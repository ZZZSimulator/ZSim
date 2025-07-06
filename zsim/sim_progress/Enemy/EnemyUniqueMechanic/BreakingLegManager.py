from typing import TYPE_CHECKING

from zsim.sim_progress.data_struct import SingleHit
from zsim.sim_progress.Report import report_dmg_result

from .BaseUniqueMechanic import BaseUniqueMechanic

if TYPE_CHECKING:
    from zsim.sim_progress.Enemy import Enemy

"""
FOCUS_RATIO_MAP 的存在，是为了模拟角色在破腿的过程中，
伤害溢散到别的腿上，导致单腿的破腿效率低于预期的情况。
但是，这种伤害的溢散，本质上和角色自身的技能模组有关。
这里的数据往往来自于对实战视频的观察，并非准确数值，并且可能经常需要调整。
"""


class BreakingLegManager:
    def __init__(self, enemy_instance):
        self.leg_group = {
            0: SingleLeg(enemy_instance, self),
            1: SingleLeg(enemy_instance, self),
            2: SingleLeg(enemy_instance, self),
            3: SingleLeg(enemy_instance, self),
            4: SingleLeg(enemy_instance, self),
            5: SingleLeg(enemy_instance, self),
        }
        self.major_target = 0
        self.FOCUS_RATIO_MAP = {1361: 0.6, 1381: 0.6}
        self.enemy = enemy_instance

    def update_myself(self, single_hit: SingleHit, tick: int):
        """这是整个manager的对外总接口，负责接收SingleHit，并且分配伤害到对应的腿上"""
        leg_index_tuple = self.select_target()
        char_cid = int(single_hit.skill_tag.strip().split("_")[0])
        major_ratio = self.FOCUS_RATIO_MAP.get(char_cid, 0.7)
        minor_ratio = (1 - major_ratio) / 2
        ratio_tuple = (minor_ratio, major_ratio, minor_ratio)
        for i in range(len(leg_index_tuple)):
            self.leg_group[leg_index_tuple[i]].update_myself(
                single_hit, tick, ratio_tuple[i]
            )

    def select_target(self) -> tuple[int, int, int]:
        """选腿！"""
        major_target = self.major_target
        minor_target_left = self.major_target - 1
        if minor_target_left < 0:
            minor_target_left = 5
        minor_target_right = self.major_target + 1
        if minor_target_right > 5:
            minor_target_right = 0
        return minor_target_left, major_target, minor_target_right

    def change_major_leg(self):
        """换一条腿！"""
        self.major_target += 1
        if self.major_target > 5:
            self.major_target = 0
        # print(f'换腿！当前主目标为{self.major_target}！')

    def report_all_legs(self):
        print("------------------")
        for index, legs in self.leg_group.items():
            print(f"腿{index}的已损失HP为{legs.lost_leg_hp}")
        print("------------------")

    def reset_myself(self):
        self.major_target = 0
        for index, leg in self.leg_group.items():
            leg.reset_single_leg()


class SingleLeg(BaseUniqueMechanic):
    """
    这是一个关于未知侵蚀复合体的破腿机制的模拟结构——
    这只怪拥有六条腿，每条腿都有自己的独立血量，
    它们的对外接口是：update_myself()函数，需要传入single_hit，
    而它们的事件触发核心是：event_active()函数
    """

    def __init__(self, enemy_instance, manager_instance):
        super().__init__(enemy_instance)
        self.leg_hp_ratio = 0.08  # 腿的倍率
        self.max_leg_hp = self.enemy.max_HP * self.leg_hp_ratio
        self.lost_leg_hp = 0  # 已经损失的腿的HP
        self.cd = 180  # 给了破腿的CD，暂定3秒
        self.last_broken = 0  # 上一次破腿的时间
        self.event = BreakingEvent(enemy_instance)
        self.manager = manager_instance

    def update_myself(self, single_hit: SingleHit, tick: int, ratio: float):
        """对外接口，接受主动技能的SingleHit，并且积累伤害。但是这里有几种情况是不积累伤害的，"""
        if self.enemy.dynamic.stun:
            """
            敌人如果正处于失衡状态下，那么游戏会强制锁定你的目标为敌人本体，而非腿，
            所以在失衡期，是不太容易破腿的，
            在模拟器中，我们对这种情况进行了直接返回的处理——即模拟战斗中，失衡期不会破腿。
            不尽如此，腿还会因为失衡期而恢复。
            """
            if self.lost_leg_hp != 0:
                self.restore_leg()
            return

        if self.last_broken != 0:
            if tick - self.last_broken <= self.cd:
                """腿还没冷却好！"""
                return

        """更新腿的生命值"""
        self.update_leg_hp(single_hit, tick, ratio)

    def event_active(self, single_hit: SingleHit, tick: int):
        self.event.active(single_hit, tick)

    def broken_leg_judge(self, tick: int) -> bool:
        """检测腿有没有爆"""
        if self.lost_leg_hp >= self.max_leg_hp:
            self.last_broken = tick
            self.restore_leg()
            print("腿破了！！！")
            return True
        else:
            return False

    def restore_leg(self):
        self.lost_leg_hp = 0
        self.manager.change_major_leg()

    def update_leg_hp(self, single_hit: SingleHit, tick: int, ratio):
        """更新腿的生命值"""
        self.lost_leg_hp += single_hit.dmg_expect * ratio
        if self.broken_leg_judge(tick):
            self.event_active(single_hit, tick)
            self.enemy.sim_instance.decibel_manager.update(
                single_hit=single_hit, key="part_break"
            )

    def reset_single_leg(self):
        """重置单条腿"""
        self.lost_leg_hp = 0
        self.last_broken = 0


class BreakingEvent:
    def __init__(self, enemy_instance):
        self.enemy: "Enemy" = enemy_instance
        self.decibel_rewards = 1000  # 奖励喧响值
        self.stun_ratio = 0.15  # 失衡比例
        self.damage_ratio = 0.055  # 破腿的直伤倍率
        self.game_state = None
        self.found_char_dict: dict[int:object] = {}

    def active(self, single_hit: SingleHit, tick: int):
        """破腿进行时！"""
        if self.game_state is None:
            from zsim.sim_progress.Preload import get_game_state

            self.game_state = get_game_state()

        # 1、更新喧响值
        self.update_decibel(single_hit)

        # 2、更新失衡
        stun_value = self.enemy.max_stun * self.stun_ratio
        self.enemy.update_stun(stun_value)
        self.enemy.stun_judge(tick, single_hit=single_hit)

        # 3、更新伤害
        dmg_value = self.enemy.max_HP * self.damage_ratio
        self.enemy._Enemy__HP_update(dmg_value)

        report_dmg_result(
            tick=tick,
            element_type=0,
            skill_tag="破腿",
            dmg_expect=round(dmg_value, 2),
            dmg_crit=round(dmg_value, 2),
            stun=round(stun_value, 2),
            buildup=0,
            **self.enemy.dynamic.get_status(),
        )

    def update_decibel(self, single_hit: SingleHit):
        """向破腿的角色里更新喧响值"""
        char_cid = int(single_hit.skill_tag.strip().split("_")[0])
        if char_cid not in self.found_char_dict:
            from zsim.sim_progress.Buff import find_char_from_CID

            self.found_char_dict[char_cid] = find_char_from_CID(
                char_cid, self.enemy.sim_instance
            )
        char_obj = self.found_char_dict[char_cid]
        char_name = char_obj.NAME
        from zsim.sim_progress.data_struct import ScheduleRefreshData

        refresh_data = ScheduleRefreshData(
            sp_target=(char_name,),
            decibel_target=(char_name,),
            decibel_value=self.decibel_rewards,
        )
        self.game_state["schedule_data"].event_list.append(refresh_data)
