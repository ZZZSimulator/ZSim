from typing import TYPE_CHECKING

from zsim.define import YIXUAN_REPORT
from zsim.sim_progress.Character import Character
from zsim.simulator.simulator_class import Simulator

from ..utils.filters import (
    _skill_node_filter,
    _sp_update_data_filter,
)
from .AdrenalineManagerClass import AdrenalineManager

if TYPE_CHECKING:
    from zsim.sim_progress.Preload import SkillNode


class Yixuan(Character):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.sheer_attack_conversion_rate = {
            0: 0.3,
            1: 0.1,
            2: 0,
            3: 0,
        }  # 贯穿力转化字典{属性值（攻击力0，生命值1，防御力2，精通3）: 倍率}
        self.adrenaline_limit = 120  # 闪能最大值
        self.max_technique_points = 120  # 最大术法值
        self.adrenaline = self.adrenaline_limit  # 入场时，获得满闪能
        self.technique_points: float = 0.0 if self.cinema < 1 else 120.0  # 术法值
        self.adrenaline_manager = AdrenalineManager(char_instance=self)
        self.listener_build = False
        self.__adrenaline_recover_overtime_update_tick = 0  # 上次更新闪能自然恢复的时间
        self.__technique_points_trans_ratio = 0.667  # 闪能转化成术法值的比例
        self.auricink_point: int = 0  # 玄墨值
        self.condensed_ink: int = 0  # 聚墨（2画效果）
        self.regulated_breathing: bool = False  # 调息（6画效果）
        self.regulated_breathing_last_update_tick: int = 0
        self.cinema_6_cd = 1800  # 6画获得调息的CD
        # TODO: 队友极限支援监听
        # TODO: 极限闪避监听

    def special_resources(self, *args, **kwargs) -> None:
        # 输入类型检查
        if not self.listener_build:
            if not isinstance(self.sim_instance, Simulator):
                raise TypeError("仪玄对象中的sim_instance不是Simulator类")
            self.sim_instance.listener_manager.listener_factory(
                listener_owner=self,
                initiate_signal="Yixuan_1",
                sim_instance=self.sim_instance,
            )
            self.listener_build = True
        skill_nodes: list["SkillNode"] = _skill_node_filter(*args, **kwargs)
        tick = self.sim_instance.tick
        for __nodes in skill_nodes:
            """向闪能回复事件管理器广播当前skill_node"""
            self.adrenaline_manager.broadcast(skill_node=__nodes)

            if __nodes.char_name != self.NAME:
                continue
            if __nodes.skill_tag == "1371_Q_A":
                if self.auricink_point != 0:
                    print(
                        f"Warning：仪玄在玄墨值大于0的情况下再次释放了【{__nodes.skill.skill_text}】，这造成了玄墨值的溢出，请检查APL代码！"
                    )
                if self.regulated_breathing:
                    if self.cinema < 6:
                        raise ValueError("仪玄在非6画状态下开启了调息状态，请检查代码！")
                    self.regulated_breathing = False
                    self.regulated_breathing_last_update_tick = tick
                    if YIXUAN_REPORT:
                        print(f"6画：仪玄释放【{__nodes.skill.skill_text}】，消耗一层调息！")
                        self.sim_instance.schedule_data.change_process_state()
                else:
                    if self.technique_points < 120:
                        raise ValueError("仪玄的术法值不足！请检查APL！")
                    self.technique_points = 0
                    self.auricink_point = min(1, self.auricink_point + 1)
            elif __nodes.skill_tag == "1371_Q":
                if self.cinema >= 2:
                    self.condensed_ink = min(1, self.condensed_ink + 1)
                    if YIXUAN_REPORT:
                        print(
                            f"2画：检测到仪玄释放喧响大招【{__nodes.skill.skill_text}】，获得1点聚墨值！"
                        )
                        self.sim_instance.schedule_data.change_process_state()
                if self.cinema == 6:
                    if (
                        tick - self.regulated_breathing_last_update_tick >= self.cinema_6_cd
                    ) or self.regulated_breathing_last_update_tick == 0:
                        self.regulated_breathing = True
                        if YIXUAN_REPORT:
                            print(
                                f"6画：检测到技能【{__nodes.skill.skill_text}】，仪玄获得一层调息"
                            )
                            self.sim_instance.schedule_data.change_process_state()
                    else:
                        print(
                            f"6画：检测到技能【{__nodes.skill.skill_text}】，但是仪玄调息的内置CD尚未转好，所以无法获得调息"
                        )
            elif __nodes.skill_tag == "1371_SNA_B_1":
                if self.auricink_point <= 0:
                    raise ValueError("仪玄的玄墨值不足！请检查APL！")
                self.auricink_point -= 1
            elif __nodes.skill_tag == "1371_Cinema_2":
                if self.cinema < 2:
                    raise ValueError(
                        f"仪玄当前影画为{self.cinema}，未解锁2画，APL却抛出了2画专属的SkillNode，请检查APL"
                    )
                if self.condensed_ink < 1:
                    raise ValueError("仪玄当前的聚墨点数不足！请检查APL")
                self.condensed_ink -= 1
                if YIXUAN_REPORT:
                    print(f"2画：仪玄追加释放【{__nodes.skill.skill_text}】，消耗1点聚墨值")
                    self.sim_instance.schedule_data.change_process_state()

            # 更新术法值和闪能值
            self.__update_adrenaline(skill_node=__nodes)

    def update_sp(self, sp_value: float):
        """仪玄没有能量值，所以这里update_sp直接return置空"""
        return

    def update_adrenaline(self, sp_value: int | float):
        """可全局强制更新能量的方法——仪玄特化版"""
        if sp_value < 0:
            # 当检测到闪能消耗时候，进行术法值的转化
            technique_points_delta = abs(sp_value) * self.__technique_points_trans_ratio
            self.technique_points = min(
                self.technique_points + technique_points_delta,
                self.max_technique_points,
            )
            if YIXUAN_REPORT:
                print(
                    f"仪玄消耗了{abs(sp_value):.2f}点闪能值，转化为{technique_points_delta:.2f}点术法值！当前术法值为：{self.technique_points:.2f}"
                )
                self.sim_instance.schedule_data.change_process_state()
        self.adrenaline += sp_value
        self.adrenaline = max(0.0, min(self.adrenaline, self.adrenaline_limit))
        # if abs(sp_value) >= 0.1:
        #     print(f"仪玄的闪能改变了{sp_value:.2f}点，当前为：{self.adrenaline:.2f}")

    def __update_adrenaline(self, skill_node: "SkillNode"):
        """char对象内部更新闪能的方法"""
        if skill_node.char_name != self.NAME:
            raise ValueError(f"{self.NAME}的更新闪能的方法接收到了非仪玄的SkillNode")
        adrenaline_delta = (
            skill_node.skill.adrenaline_recovery - skill_node.skill.adrenaline_consume
        )
        if adrenaline_delta <= 0 and abs(adrenaline_delta) > self.adrenaline:
            raise ValueError(
                f"检测到技能{skill_node.skill_tag}【{skill_node.skill.skill_text}】企图消耗{skill_node.skill.adrenaline_consume}点闪能，但是仪玄当前的闪能不足：{self.adrenaline}，请检查APL"
            )
        self.update_adrenaline(adrenaline_delta)

    def update_sp_overtime(self, args, kwargs):
        """
        该函数会在Preload以及Schedule阶段被调用两次，当在Preload阶段调用时，sp_regen_data为空，
        只有在Schedule阶段被调用时，函数才会被执行。
        所以sp_regen_data虽然和闪能回复无关，但确是保证函数只被运行一次的关键。
        """
        sp_regen_data = _sp_update_data_filter(*args, **kwargs)
        if sp_regen_data:
            if (
                self.sim_instance.tick == self.__adrenaline_recover_overtime_update_tick
                and self.__adrenaline_recover_overtime_update_tick != 0
            ):
                raise ValueError(
                    "检测到仪玄闪能的自然恢复逻辑在同一个tick被调用了两次！请检查函数！"
                )
            sp_change_per_tick = 2 / 60
            self.update_adrenaline(sp_change_per_tick)
            self.__adrenaline_recover_overtime_update_tick = self.sim_instance.tick

    def refresh_myself(self):
        """回能更新的几个管理器需要每个tick更新一次，所以用这个接口进行更新。"""
        self.adrenaline_manager.refresh()

    def get_resources(self) -> tuple[str, float]:
        return "闪能", self.adrenaline

    def get_special_stats(self, *args, **kwargs) -> dict[str, int | float | bool]:
        """获取简仪玄特殊状态"""
        return {
            "术法值": self.technique_points,
            "玄墨值": self.auricink_point,
            "聚墨点数": self.condensed_ink,
            "调息层数": self.regulated_breathing,
        }
