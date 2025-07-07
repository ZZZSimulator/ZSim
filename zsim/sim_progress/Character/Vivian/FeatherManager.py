from zsim.define import VIVIAN_REPORT
from zsim.sim_progress.Preload import SkillNode

from ..character import Character


class FeatherManager:
    """薇薇安的羽毛管理器，飞羽、护羽存储、转化、消耗。"""

    def __init__(self, char_instance: Character):
        self.char = char_instance
        self.flight_feather = 2  # 飞羽，进场初始化为4层
        self.guard_feather = 0 if self.char.cinema < 4 else 5  # 护羽，初始化为0层
        self.feather_max_count = 5  # 最大飞羽/护羽层数，默认为6层
        self.co_attack_index = "1331_CoAttack_A"
        self.c1_counter = 0  # 1 画计数器

    def update_myself(self, skill_node: SkillNode = None, c6_signal: bool = None):
        """
        用来更新羽毛的方法，被薇薇安的羽毛触发器调用，
        该函数内部没有任何类型判断，所有的判断全部交给羽毛触发器的xjudge
        """
        if skill_node is None and c6_signal is None:
            raise ValueError(
                "薇薇安羽毛管理器的update_myself函数必须传入skill_node或c6_singal参数中的一个！"
            )
        if c6_signal or skill_node.skill_tag == "1331_SNA_2":
            self.trans_feather()
        else:
            self.gain_feather(skill_node)

    def trans_feather(self):
        """将现有的飞羽全部转化成护羽：注意，飞羽转化为护羽的时间点为SNA_2的最后一跳，所以这里不能走特殊资源，只能从触发器走。"""
        trans_count = self.flight_feather
        self.guard_feather = min(
            self.guard_feather + trans_count, self.feather_max_count
        )
        self.flight_feather = 0
        if VIVIAN_REPORT:
            self.char.sim_instance.schedule_data.change_process_state()
            print(
                f"羽毛管理器：羽毛转化！当前的护羽、飞羽数量为：{self.guard_feather, self.flight_feather}"
            )

    def gain_feather(self, skill_node: SkillNode):
        """
        获得飞羽，飞羽的获得结算大多为技能的最后一跳，所以也需要从触发器走。
        该函数内部没有任何类型判断，所有的判断全部交给羽毛触发器的xjudge
        """
        if not skill_node.skill.labels:
            return
        if "flight_feather" not in skill_node.skill.labels.keys():
            return
        flight_feather_count = skill_node.labels["flight_feather"]
        c6_feather = skill_node.labels.get("c6_feather", 0)
        if self.char.cinema == 6:
            flight_feather_count += c6_feather
        self.flight_feather = min(
            self.flight_feather + flight_feather_count, self.feather_max_count
        )
        if VIVIAN_REPORT:
            self.char.sim_instance.schedule_data.change_process_state()
            print(
                f"羽毛管理器：获得{flight_feather_count}点羽毛！当前护、飞羽数量为：{self.guard_feather, self.flight_feather}"
            )

    def spawn_coattack(self) -> str | None:
        """尝试生成一次生花"""
        if self.guard_feather > 0:
            self.guard_feather -= 1
            if self.char.cinema >= 1:
                self.c1_counter += 1
                if self.c1_counter >= 4:
                    self.flight_feather = min(
                        self.flight_feather + 1, self.feather_max_count
                    )
                    self.c1_counter -= 4
            if VIVIAN_REPORT:
                self.char.sim_instance.schedule_data.change_process_state()
                print(
                    f"羽毛管理器：落羽生花完成结算！当前的护羽、飞羽数量为：{self.guard_feather, self.flight_feather}"
                )
            return self.co_attack_index
        else:
            return None
