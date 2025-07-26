import ast
from collections import defaultdict
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd

from zsim.define import (
    ENEMY_ATK_PARAMETER_DICT,
    ENEMY_ATTACK_ACTION,
    ENEMY_ATTACK_METHOD_CONFIG,
    ENEMY_ATTACK_REPORT,
    ENEMY_RANDOM_ATTACK,
    ENEMY_REGULAR_ATTACK,
)
from zsim.sim_progress.RandomNumberGenerator import RNG

if TYPE_CHECKING:
    from zsim.sim_progress.Enemy import Enemy

"""
    EnemyAttack模块相关的数据结构以及程序逻辑设计如下（2025.1.30）：
    1、新建一个数据库（暂时用CSV来执行），里面记录了Enemy的各种进攻动作，由独立的ID作为索引。（包含了默认动作）
    2、新建一个Json，用来记录不同敌人的进攻策略，其中包含了各种数据库中的动作ID，以及它们对应的几率。（包含了默认的策略）
        Json的键值是一个独立的ID，可以是数字，也可以是字符串。
    3、在Enemy类下，更新一个新的字段（包括EnemyClass以及对应的Enemy.csv），用来存放不同敌人的策略ID，
    4、初始化时，根据Enemy.attack.策略ID→对应的攻击策略→对应的攻击动作ID（多个）→构造EnemyAttack实例（多个）→存放到Enemy.attack.attack_method下
        4.1、每个攻击动作都会构造一个单独的EnemyAttackAction实例，这些实例会被存到EnemyAttackMethod实例下，并且有各自的几率。
    5、调用时，利用EnemyAttack.attack_event_spawn函数，生成本次发生的攻击事件，并且抛出，被Preload获取。
"""

method_file = pd.read_csv(ENEMY_ATTACK_METHOD_CONFIG, index_col="ID")
action_file = pd.read_csv(ENEMY_ATTACK_ACTION, index_col="ID")


class EnemyAttackMethod:
    """含有若干个进攻动作的进攻策略"""

    def __init__(self, ID: int = 0, enemy_instance: "Enemy" = None):
        self.action_set: dict[float | int, EnemyAttackAction] = defaultdict()
        self.enemy = enemy_instance
        self.active = True
        if ENEMY_RANDOM_ATTACK:
            self.random_attack: bool = True
            self.attack_skill_tag = None
        elif ENEMY_REGULAR_ATTACK:
            self.random_attack = False
            self.attack_skill_tag = EnemyAttackAction(ID=int(method_file.loc[ID]["action_set"])).tag
        else:
            self.random_attack = False
            self.attack_skill_tag = None
            self.active = False
        self.last_start_tick = 0
        self.last_end_tick = 0
        self.ready = False
        rate_list = method_file.loc[ID]["action_rate"].split("|")
        if sum(float(i) for i in rate_list) > 1:
            raise ValueError("动作总权重超过1，请检查配置")
        single_action_id_list = method_file.loc[ID]["action_set"].split("|")
        if len(rate_list) != len(single_action_id_list):
            raise ValueError("动作总数与概率总数不符，请检查配置")
        self.rest_tick = method_file.loc[ID]["rest_tick"]
        self.description = method_file.loc[ID]["discription"]  # FIXME
        self.name = method_file.loc[ID]["method_name"]
        for i in range(len(single_action_id_list)):
            action_id = single_action_id_list[i]
            action_rate = float(rate_list[i])
            enemy_attack_action = EnemyAttackAction(int(action_id))
            self.action_set[action_rate] = enemy_attack_action
            print(
                f"【进攻交互系统初始化】：为敌人添加进攻动作：{enemy_attack_action}"
            ) if ENEMY_ATTACK_REPORT else None
        print("【进攻交互系统初始化】：敌人进攻动作初始化完毕！") if ENEMY_ATTACK_REPORT else None
        print(
            f"【进攻交互系统初始化】：敌人（{self.enemy.name}）共拥有{len(self.action_set)}个进攻动作，每次进攻决策的冷却时间为：{self.rest_tick}tick！"
        ) if ENEMY_ATTACK_REPORT else None
        if not self.active and ENEMY_ATTACK_REPORT:
            print(
                "【进攻交互系统初始化】：由于在配置文件中并未开启任意一种进攻策略，所以在本次模拟中敌人不会进攻！"
            )

    def ready_check(self, current_tick: int) -> bool:
        """判断敌人进攻的内置CD——进攻动作结束后，进攻决策才会进入冷却时间。"""
        if not self.ready:
            if current_tick - self.last_end_tick >= self.rest_tick:
                self.ready = True
        return self.ready

    def probablity_driven_action_selection(self, current_tick: int) -> "EnemyAttackAction | None":
        """根据概率选择一个进攻动作"""
        cumulative_probability = (
            0  # 累积概率，这个数字没有实际意义，只是为了方便计算，每次函数运行时都初始化为0
        )
        rng: RNG = self.enemy.sim_instance.rng_instance
        normalized_value = rng.random_float()
        if not self.ready_check(current_tick):
            return None
        for _rate, _action in self.action_set.items():
            cumulative_probability += _rate
            if cumulative_probability >= normalized_value:
                self.last_start_tick = current_tick
                self.last_end_tick = current_tick + _action.duration
                self.ready = False
                return _action
        else:
            """如果循环结束，还没有选中任何一个动作，说明无事发生，返回None"""
            return None

    def time_anchored_action_selection(self, current_tick: int) -> "EnemyAttackAction | None":
        """以固定的时间间隔选择固定的进攻动作"""
        if self.ready_check(current_tick=current_tick):
            self.last_start_tick = current_tick
            self.last_end_tick = current_tick + self.action_set[1].duration
            self.ready = False
            print(
                f"{self.enemy.name}（ID：{self.enemy.index_ID}）抛出进攻动作{self.action_set[1].tag}"
            ) if ENEMY_ATTACK_REPORT else None
            return self.action_set[1]
        else:
            return None

    def reset_myself(self):
        """重构EnemyAttack方法！"""
        self.last_start_tick = 0
        self.last_end_tick = 0
        self.ready = False


class EnemyAttackAction:
    """敌人的单个进攻动作，它不记录任何动态数据，只是一个静态的动作数据结构，"""

    def __init__(self, ID: int):
        if ID == 0:
            raise ValueError("EnemyAttackAction实例化所用的ID为0，请检查配置信息！")
        self.id = ID
        self.action_dict = action_file.loc[ID].to_dict()
        self.tag = self.action_dict.get("tag", "")
        self.description = self.action_dict.get("description", "")
        self.hit = int(self.action_dict.get("hit", 0))
        if self.hit <= 0:
            raise ValueError("hit参数必须大于0，请检查配置信息！")
        self.duration = float(self.action_dict.get("duration", 0))
        if self.duration <= 0:
            raise ValueError("duration参数必须大于0，请检查配置信息！")
        self.cd = int(self.action_dict.get("cd", 0))
        hit_list_str = self.action_dict.get("hit_list", None)
        if hit_list_str is None or hit_list_str is np.nan:
            # 在未提供hit_list的情况下，默认hit均匀分布，所以直接根据hit和duration来产生hit_list，
            self.hit_list = list(
                (self.duration / (self.hit + 1)) * (i + 1) for i in range(int(self.hit))
            )
        else:
            self.hit_list = ast.literal_eval(hit_list_str)

        if len(self.hit_list) != self.hit:
            raise ValueError(f"{self.tag}的命中数量与命中时间列表长度不符，请检查配置信息！")

        self.parryable = bool(self.action_dict.get("blockable", True))  # 是否可以招架
        self.interruption_level_list = self.action_dict.get("interruption_level_list", None)
        if self.interruption_level_list is None or self.interruption_level_list is np.nan:
            self.interruption_level_list = [1] * self.hit
        else:
            self.interruption_level_list = self.interruption_level_list.split("|")
        self.effect_radius_list = self.action_dict.get("effect_radius_list", None)
        # TODO：暂时不考虑由技能范围不同而对命中率造成的影响，统一按照100%命中来处理，
        self.stoppable = self.action_dict.get("stoppable", True)
        self.hit_type = self.action_dict.get("hit_type", "Light")
        if self.hit_type == "Chain" and self.hit <= 1:
            raise ValueError(
                f"{self.tag}为连续进攻动作，但是其命中数量为{self.hit}，请检查配置信息！"
            )
        if self.hit_type in ["Light", "Heavy"] and self.hit > 1:
            raise ValueError(
                f"{self.tag}为{self.hit_type}攻击，但是其命中数量为{self.hit}，请检查配置信息！"
            )

    def get_hit_tick(self, another_ta: int = None, hit_count: int = 1) -> int:
        """获取命中时间，"""
        if not self.hit_list:
            raise ValueError("hit_list为空，无法获取命中点！")
        hit_tick = self.hit_list[hit_count - 1]
        Ta = ENEMY_ATK_PARAMETER_DICT.get("Taction") if another_ta is None else another_ta
        if hit_tick < Ta:
            raise ValueError(
                f"{self.tag}的第一个命中点({hit_tick})小于响应动作持续时间({Ta})，请检查数据库！"
            )
        return self.hit_list[0]

    def get_first_hit(self) -> int:
        """获取第一个命中点"""
        if not self.hit_list:
            raise ValueError("hit_list为空，无法获取第一个命中点！")
        first_hit_tick = self.hit_list[0]
        Ta = ENEMY_ATK_PARAMETER_DICT.get("Taction")
        if first_hit_tick < Ta:
            raise ValueError(
                f"{self.tag}的第一个命中点({first_hit_tick})小于相应动作持续时间({Ta})，请检查数据库！"
            )
        return self.hit_list[0]

    def __str__(self):
        return f"进攻动作ID：{self.id}, 技能Tag：{self.tag}，动作耗时：{self.duration}，单次动作的冷却时间：{self.cd}"


if __name__ == "__main__":
    method = EnemyAttackMethod()
    print(f"{method.name},{method.description}")
    count = 0
    for rate, action in method.action_set.items():
        print(
            f"事件{count + 1}，几率{rate}，动作集{action.hit_list}，是否可被格挡：{action.blockable_list}，\n打断等级{action.interruption_level_list}，效果半径{action.effect_radius_list}，是否可被打断{action.stoppable}"
        )
        count += 1
