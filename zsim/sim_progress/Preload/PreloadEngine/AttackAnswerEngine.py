from typing import TYPE_CHECKING

from zsim.sim_progress.data_struct import EnemyAttackEventManager

from .BasePreloadEngine import BasePreloadEngine

if TYPE_CHECKING:
    from zsim.sim_progress.Character import Character
    from zsim.sim_progress.Enemy import Enemy
    from zsim.sim_progress.Enemy.EnemyAttack.EnemyAttackClass import EnemyAttackAction
    from zsim.simulator.simulator_class import Simulator

    from ..PreloadDataClass import PreloadData


class AttackResponseEngine(BasePreloadEngine):
    """进攻响应引擎，主要负责敌人进攻动作抛出，以及角色动作响应相关的内容；"""

    def __init__(self, data, sim_instance: "Simulator" = None):
        super().__init__(data)
        self.data: "PreloadData" = data
        self.game_state = None
        self.found_char_dict: dict[int, "Character"] = {}
        self.enemy: "Enemy | None" = None
        self.sim_instance: "Simulator | None" = sim_instance

    def run_myself(self, tick: int, *args, **kwargs) -> None:
        if self.data.atk_manager is None:
            self.data.atk_manager = EnemyAttackEventManager(
                enemy_instance=self.sim_instance.schedule_data.enemy
            )

        self.data.atk_manager.end_check(tick=tick)

        enemy_attack_action: "EnemyAttackAction | None" = self.try_spawn_enemy_attack()
        if enemy_attack_action is not None:
            # 将进攻信号发送给PreloadData。
            self.data.atk_manager.event_start(
                action=enemy_attack_action, start_tick=self.sim_instance.tick
            )

        """每次运行，都要让atk_manager自检一次，以更新状态。"""
        self.data.atk_manager.check_myself(tick=tick)

    def try_spawn_enemy_attack(self) -> "EnemyAttackAction | None":
        """调用Enemy对象下的进攻模组，并且生成一次攻击，同时打包成事件存入本地"""
        if self.sim_instance is None:
            self.sim_instance = self.data.sim_instance
        if self.enemy is None:
            self.enemy = self.sim_instance.schedule_data.enemy
        if not self.enemy.attack_method.active:
            return None
        if self.enemy.dynamic.stun:
            return None
        if self.data.atk_manager.interruption_recovery_check(
            tick=self.sim_instance.tick
        ):
            return None
        if self.enemy.attack_method.random_attack:
            enemy_attack_action = (
                self.enemy.attack_method.probablity_driven_action_selection(
                    current_tick=self.sim_instance.tick
                )
            )
        else:
            enemy_attack_action = (
                self.enemy.attack_method.time_anchored_action_selection(
                    current_tick=self.sim_instance.tick
                )
            )
        return enemy_attack_action
