from .. import Buff, JudgeTools, check_preparation
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from zsim.simulator.simulator_class import Simulator
    from zsim.sim_progress.Preload import SkillNode
    from zsim.sim_progress.Preload.PreloadDataClass import PreloadData
    from zsim.sim_progress.Character import Character


class QingmingBirdcageCompanionSheerAtkBonusRecord:
    def __init__(self):
        self.equipper = None
        self.char = None
        self.sub_exist_buff_dict = None
        self.preload_data = None
        self.update_signal = None


class QingmingBirdcageCompanionSheerAtkBonus(Buff.BuffLogic):
    """青溟笼舍的清明同行的复杂判定，这把武器拥有 以太增伤 以及 贯穿伤害两部分效果，这两部分效果共享同一个判定逻辑"""

    def __init__(self, buff_instance):
        super().__init__(buff_instance)
        self.buff_instance: Buff = buff_instance
        self.xjudge = self.special_judge_logic
        self.xstart = self.special_start_logic
        self.equipper = None
        self.buff_0 = None
        self.record = None

    def get_prepared(self, **kwargs):
        return check_preparation(
            buff_instance=self.buff_instance, buff_0=self.buff_0, **kwargs
        )

    def check_record_module(self):
        if self.equipper is None:
            self.equipper = JudgeTools.find_equipper(
                "青溟笼舍", sim_instance=self.buff_instance.sim_instance
            )
        if self.buff_0 is None:
            self.buff_0 = JudgeTools.find_exist_buff_dict(
                sim_instance=self.buff_instance.sim_instance
            )[self.equipper][self.buff_instance.ft.index]
        if self.buff_0.history.record is None:
            self.buff_0.history.record = QingmingBirdcageCompanionSheerAtkBonusRecord()
        self.record = self.buff_0.history.record

    def special_judge_logic(self, **kwargs):
        """这里有两种放行条件。第一种是装备者的强化E，第二种是刚刚进场时放行。"""
        self.check_record_module()
        self.get_prepared(equipper="青溟笼舍", preload_data=1)
        preload_data: "PreloadData" = self.record.preload_data
        char: "Character" = self.record.char
        skill_node: "SkillNode | None" = kwargs.get("skill_node", None)
        sim: "Simulator" = self.buff_instance.sim_instance
        if skill_node is None:
            return False
        # 检测到第一个动作时放行
        if skill_node.char_name != char.NAME:
            return False
        if skill_node.preload_tick != sim.tick:
            return False
        if len(preload_data.personal_node_stack[char.CID]) == 1:
            if self.record.update_signal is not None:
                raise ValueError(
                    f"{self.buff_instance.ft.index}的Xjudge函数检验到有尚未处理的更新信号，请检查XStart函数"
                )
            self.record.update_signal = 0
            return True
        if skill_node.skill.trigger_buff_level == 2:
            if self.record.update_signal is not None:
                raise ValueError(
                    f"{self.buff_instance.ft.index}的Xjudge函数检验到有尚未处理的更新信号，请检查XStart函数"
                )
            self.record.update_signal = 1
            return True
        return False

    def special_start_logic(self, **kwargs):
        self.check_record_module()
        self.get_prepared(equipper="青溟笼舍", sub_exist_buff_dict=1)
        sim: "Simulator" = self.buff_instance.sim_instance
        if self.record.update_signal is None:
            raise ValueError(
                f"{self.buff_instance.ft.index}的XStart函数并未检测到有效的更新信号，请检查Xjudge函数！"
            )
        if self.record.update_signal == 0:
            self.buff_instance.simple_start(
                timenow=sim.tick,
                sub_exist_buff_dict=self.record.sub_exist_buff_dict,
                no_count=1,
            )
            self.buff_instance.dy.count = 2
            self.buff_instance.update_to_buff_0(self.buff_0)
            self.record.update_signal = None
        elif self.record.update_signal == 1:
            self.buff_instance.simple_start(
                timenow=sim.tick, sub_exist_buff_dict=self.record.sub_exist_buff_dict
            )
            self.record.update_signal = None
        else:
            raise ValueError(f"无法解析的更新信号：{self.record.update_signal}")
