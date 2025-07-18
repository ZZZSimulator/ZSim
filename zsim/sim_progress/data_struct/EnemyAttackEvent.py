import math
from typing import TYPE_CHECKING

from zsim.define import ENEMY_ATK_PARAMETER_DICT, ENEMY_ATTACK_REPORT

if TYPE_CHECKING:
    from zsim.sim_progress.data_struct import SingleHit
    from zsim.sim_progress.Enemy import Enemy
    from zsim.sim_progress.Enemy.EnemyAttack.EnemyAttackClass import EnemyAttackAction
    from zsim.sim_progress.Preload import SkillNode


class EnemyAttackEventManager:
    def __init__(self, enemy_instance: "Enemy"):
        """进攻事件对象，负责管理敌人进攻的相关动态信息。"""
        self.enemy: "Enemy" = enemy_instance
        self.action: "None | EnemyAttackAction" = None

        self.last_start_tick: int = 0  # 进攻事件的开始时刻，也是进攻意图的展露时刻。
        self.last_end_tick: int = 0
        self.answered_action: list["SkillNode"] = []
        self.interaction_window_open_tick: int | None = (
            None  # 交互窗口开启的tick，即游戏中红黄光亮起的tick
        )
        self.interaction_window_close_tick: int | None = (
            None  # 交互窗口关闭的tick，即游戏中动作命中的时间点
        )

        self.hitted_count = 0  # 交互期间的命中计数
        self.answered_count = 0  # 交互期间的成功响应次数
        self.interrupted_skill_type = [2, 5, 6]
        self.interruption_recovery_frames = 60  # 每次敌人被打断的硬直时间
        self._interruption_update_tick = 0

    @property
    def interruption_update_tick(self) -> int:
        """上一次敌人进入打断硬直的更新时间，可以直接访问，也可以赋值"""
        return self._interruption_update_tick

    @interruption_update_tick.setter
    def interruption_update_tick(self, value: int):
        """赋值功能"""
        self._interruption_update_tick = value
        # print(
        #     f"敌人的打断硬直更新了！新的状态将从{value}tick开始，于{value + self.interruption_recovery_frames}tick结束。"
        # )

    def event_start(self, action: "EnemyAttackAction", start_tick: int):
        """开始一个进攻事件"""
        self.action = action
        self.last_start_tick = start_tick
        self.last_end_tick = start_tick + action.duration
        response_window: tuple[int, int] = self.get_response_window()
        self.interaction_window_open_tick = response_window[0]
        self.interaction_window_close_tick = response_window[1]
        if ENEMY_ATTACK_REPORT:
            self.enemy.sim_instance.schedule_data.change_process_state()
            print(
                f"敌人（{self.enemy.name}）开始了进攻事件：{action.tag}，持续时间为{action.duration}tick"
            )

    def event_end(self, tick: int = None):
        """结束一个进攻事件"""
        if self.action is None:
            raise ValueError("没有正在进行的进攻事件，无法结束！")

        # self.response_result_settlement()
        if tick is not None:
            self.last_end_tick = tick
        self.action = None
        self.answered_action = []
        self.hitted_count = 0
        self.answered_count = 0

    def interrupted(self, tick: int, reason: str = None):
        """中断当前进攻事件"""
        if self.action is None:
            raise ValueError("没有正在进行的进攻事件，无法中断！")
        if ENEMY_ATTACK_REPORT:
            self.enemy.sim_instance.schedule_data.change_process_state()
            print(
                f"敌人（{self.enemy.name}）的进攻事件：{self.action.tag}在第{tick}tick被中断！打断源：{reason}"
            )
        self.event_end(tick=tick)
        self.interruption_update_tick = tick

    def interruption_recovery_check(self, tick: int) -> bool:
        """检测当前tick是否处于硬直状态"""
        if self.interruption_update_tick == 0:
            return False
        if tick - self.interruption_update_tick > self.interruption_recovery_frames:
            return False
        else:
            return True

    def end_check(self, tick: int):
        """检测当前进攻事件是否已经结束"""
        if not self.action:
            return
        if tick >= self.last_end_tick:
            if ENEMY_ATTACK_REPORT:
                self.enemy.sim_instance.schedule_data.change_process_state()
                print(
                    f"敌人（{self.enemy.name}）的进攻事件：{self.action.tag}在第{tick}tick自然结束！该次动作共计命中{self.hitted_count}次，被有效响应{self.answered_count}次"
                )
            self.event_end()

    @property
    def attacking(self) -> bool:
        """当前是否正在进行进攻事件"""
        return self.action is not None

    @property
    def is_answered(self) -> bool:
        """当前进攻事件是否已经被响应"""
        if not self.answered_action:
            return False
        else:
            for action in self.answered_action:
                """仅在检测到招架支援时，才返回True。只要不招架，那么单次进攻信号就可能被多次利用。"""
                if "parry_Aid" in action.skill_tag:
                    return True
            else:
                return False

    def is_in_response_window(self, tick: int) -> bool:
        """判断当前tick是否处于首次响应窗口内"""
        if not self.attacking:
            return False
        if (
            self.interaction_window_open_tick
            <= tick
            <= self.interaction_window_close_tick
        ):
            return True
        return False

    def get_rt(self) -> int:
        """获取玩家反应时间（RT），即玩家从看到敌人进攻到做出反应的时间。"""
        theta = ENEMY_ATK_PARAMETER_DICT.get("theta", None)
        if theta is None:
            raise ValueError("ENEMY_ATK_PARAMETER_DICT中没有theta参数，请检查配置！")

        Lp = ENEMY_ATK_PARAMETER_DICT.get("PlayerLevel", None)
        if Lp is None:
            raise ValueError(
                "ENEMY_ATK_PARAMETER_DICT中没有PlayerLevel参数，请检查配置！"
            )
        c = ENEMY_ATK_PARAMETER_DICT.get("c", None)
        if c is None:
            raise ValueError("ENEMY_ATK_PARAMETER_DICT中没有c参数，请检查配置！")
        Tbase = ENEMY_ATK_PARAMETER_DICT.get("Tbase", None)
        if Tbase is None:
            raise ValueError("ENEMY_ATK_PARAMETER_DICT中没有Tbase参数，请检查配置！")
        delta = ENEMY_ATK_PARAMETER_DICT.get("delta", None)
        if delta is None:
            raise ValueError("ENEMY_ATK_PARAMETER_DICT中没有delta参数，请检查配置！")
        sigma = c / (Lp**0.3)  # 计算方差
        Ta = Tbase + delta * (3 - Lp)  # 根据玩家水平计算对应中位数
        mu = math.log(Ta - theta) - sigma**2 / 2  # 计算均值

        Z = abs(
            self.enemy.sim_instance.rng_instance.normal_from_table()
        )  # 从RNG模块按正态分布获取一个0~1的随机数。
        RT = theta + math.e ** (mu + sigma * Z)
        rt_tick = round(RT / 1000 * 60)  # 将毫秒转化为帧（tick）

        return rt_tick

    def get_response_window(self) -> tuple[int, int]:
        """获取红黄光亮起的时间点"""

        first_hit_tick = self.action.get_hit_tick() + self.last_start_tick

        Ta = ENEMY_ATK_PARAMETER_DICT.get("Taction")
        left_bound = max(
            self.last_start_tick, first_hit_tick - Ta
        )  # 如果怪物前摇很短，动作时间也很短，那么怪物攻击动作开始的时间就是黄光亮起的时间。
        right_bound = first_hit_tick
        return left_bound, right_bound

    def get_uncommon_response_window(self, another_ta: int) -> tuple[int, int]:
        """获取红黄光亮起的时间点，适用于非标准的进攻动作"""
        first_hit_tick = (
            self.action.get_hit_tick(another_ta=another_ta) + self.last_start_tick
        )
        Ta = another_ta
        left_bonud = max(self.last_start_tick, first_hit_tick - Ta)
        right_bound = first_hit_tick
        return left_bonud, right_bound

    def can_be_answered(self, rt_tick: int) -> tuple[bool, int, int]:
        """该函数用于判断当前进攻事件是否具有响应的可能，主要是时间判断。"""
        if not self.action:
            raise ValueError("调用can_be_answered函数时请确保存在进攻事件")
        if self.is_answered:
            print(
                f"当前动作：{self.action.tag}已经被{[_action.skill_tag for _action in self.answered_action]}响应过了！"
            )
            return False, 0, 0
        Lp = ENEMY_ATK_PARAMETER_DICT.get("PlayerLevel")
        Td = self.interaction_window_close_tick - self.interaction_window_open_tick
        first_hit_tick = self.action.get_hit_tick()
        if Lp <= 2:
            return rt_tick <= Td, rt_tick, Td
        else:
            return (
                rt_tick <= first_hit_tick,
                rt_tick,
                first_hit_tick,
            )

    def receive_response_node(self, skill_node: "SkillNode"):
        """统一接口，用于接收响应技能（preload阶段）。"""
        if not self.attacking:
            raise ValueError("企图在没有进攻事件的时候调用进攻事件接收接口。")
        self.answered_action.append(skill_node)
        self.answered_count += 1

    def check_myself(self, tick: int) -> None:
        """检查当前tick的命中结算、结束结算、打断等情况；"""
        if self.action is None:
            return
        """筛除过期的响应技能"""
        nodes_to_remove = []
        for nodes in self.answered_action:
            if nodes.end_tick < tick:
                nodes_to_remove.append(nodes)
        else:
            for _nodes in nodes_to_remove:
                self.answered_action.remove(_nodes)
        """检查是否命中，如果有命中则执行单次命中的结果检测"""
        if self.hit_check(tick=tick):
            self.single_hit_settlement(tick=tick)

    def receive_single_hit(self, single_hit: "SingleHit", tick: int):
        """
        在Enemy接收Hit的时候，需要这个函数来把SingleHit传进AtkEventManager，
        来更新敌人的打断状态。
        """
        skill_node: "SkillNode | None" = single_hit.skill_node
        if skill_node is None:
            return
        if not self.__check_skill_interrupt_capability(skill_node=skill_node):
            return
        self.interruption_update_tick = tick
        if self.action is not None:
            self.interrupted(tick=tick, reason=f"技能：{skill_node.skill_tag}")

    def hit_check(self, tick: int) -> bool:
        """检查输入的tick是否存在命中节点"""
        if any(
            [
                _hit_tick + self.last_start_tick == tick
                for _hit_tick in self.action.hit_list
            ]
        ):
            return True
        return False

    def single_hit_settlement(self, tick: int) -> None:
        """单次命中结算函数，用于结算当前tick的命中结果。"""
        sim_instance = self.enemy.sim_instance
        char_on_field: int = sim_instance.preload.preload_data.operating_now
        char_stack = sim_instance.preload.preload_data.personal_node_stack[
            char_on_field
        ]
        self.hitted_count += 1
        if char_stack is None:
            if ENEMY_ATTACK_REPORT:
                self.enemy.sim_instance.schedule_data.change_process_state()
                print(
                    f"当前前台角色{char_on_field}并未进行有效交互（没有技能栈），将被打断！"
                )
            return
        nodes = char_stack.get_effective_node()
        if nodes is None:
            if ENEMY_ATTACK_REPORT:
                self.enemy.sim_instance.schedule_data.change_process_state()
                print(
                    f"当前前台角色{char_on_field}并未进行有效交互（尚未行动过），将被打断！"
                )
            return
        if "interrupted" in nodes.skill_tag:
            print(f"角色{char_on_field}正处于被打断后摇中，打断后摇不刷新！")
            return
        if (
            nodes.end_tick < tick
            and not self.enemy.sim_instance.preload.strategy.apl_engine.apl.action_replace_manager.parry_aid_strategy.consecutive_parry_mode
        ):
            if ENEMY_ATTACK_REPORT:
                self.enemy.sim_instance.schedule_data.change_process_state()
                print(
                    f"当前前台角色{char_on_field}并未进行有效交互（没有正在进行的动作，上一个动作{nodes.skill_tag}已经在{nodes.end_tick}结束），将被打断！"
                )
            return

        if any([_sub_tag in nodes.skill_tag for _sub_tag in ["parry", "dodge"]]):
            # 直接交互
            if ENEMY_ATTACK_REPORT:
                self.enemy.sim_instance.schedule_data.change_process_state()
                print(
                    f"角色{char_on_field}成功通过{nodes.skill_tag}与敌方的进攻进行交互。该技能从{nodes.preload_tick}开始，{nodes.end_tick}结束。"
                )
            self.answered_count += 1
            if "parry" in nodes.skill_tag:
                from zsim.sim_progress.Preload.APLModule.ActionReplaceManager import (
                    ActionReplaceManager,
                )

                action_replace_manager: ActionReplaceManager = (
                    sim_instance.preload.strategy.apl_engine.apl.action_replace_manager
                )
                if self.action.hit == 1:
                    self.enemy.sim_instance.schedule_data.change_process_state()
                    print(
                        f"【AtkEventManager】检测到来自角色{char_on_field}的招架技能{nodes.skill_tag}，进攻交互式时间提前结束，角色即将被击退！"
                    )
                    action_replace_manager.parry_aid_strategy.knock_back_signal = True
                    action_replace_manager.parry_aid_strategy.final_parry_node = nodes
                    self.event_end(tick=tick)
                else:
                    if self.action.hit == self.hitted_count:
                        action_replace_manager.parry_aid_strategy.knock_back_signal = (
                            True
                        )
                        action_replace_manager.parry_aid_strategy.final_parry_node = (
                            nodes
                        )
                        self.event_end(tick=tick)
                        print(
                            f"检测到来自角色{char_on_field}的招架技能{nodes.skill_tag}，进攻交互式时间提前结束，角色即将被击退！"
                        )
        else:
            # 非直接交互
            if nodes.skill.trigger_buff_level in [2, 4, 5, 6, 7, 8, 9]:
                if ENEMY_ATTACK_REPORT:
                    self.enemy.sim_instance.schedule_data.change_process_state()
                    print(
                        f"角色{char_on_field}选择释放{nodes.skill_tag}进行交互，交互成功。"
                    )
                self.answered_count += 1
            else:
                if ENEMY_ATTACK_REPORT:
                    self.enemy.sim_instance.schedule_data.change_process_state()
                    print(
                        f"角色被打断！{nodes.skill_tag}技能被迫取消！"
                    )
                """取消当前正在进行的技能，同时添加一次被打断技能，模拟角色动作被打断。"""
                sim_instance.preload.preload_data.delete_mission_in_preload_data(
                    node_be_changed=nodes
                )
                sim_instance.preload.preload_data.external_add_skill(
                    skill_tuple=(f"{char_on_field}_interrupted", True, tick)
                )

    def __check_skill_interrupt_capability(self, skill_node: "SkillNode") -> bool:
        """检查技能是否能够被打断，这涉及到更加详细的打断参数比对，所以这里先用其他的逻辑代替。"""
        if skill_node.skill.trigger_buff_level in self.interrupted_skill_type:
            if skill_node.active_generation:
                return True
        return False
