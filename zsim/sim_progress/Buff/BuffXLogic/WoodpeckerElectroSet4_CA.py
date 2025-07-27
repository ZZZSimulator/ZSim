from __future__ import annotations

from typing import TYPE_CHECKING

from .. import Buff, JudgeTools, check_preparation

if TYPE_CHECKING:
    from zsim.sim_progress.RandomNumberGenerator import RNG


class WoodpeckerElectroCARecord:
    def __init__(self):
        self.equipper = None
        self.char = None
        self.dynamic_buff_list = None
        self.enemy = None
        self.action_stack = None


class WoodpeckerElectroSet4_CA(Buff.BuffLogic):
    def __init__(self, buff_instance):
        super().__init__(buff_instance)
        self.buff_instance: Buff = buff_instance
        # 初始化特定逻辑
        self.xjudge = self.special_judge_logic
        self.buff_0 = None
        self.record = None
        self.equipper = None

    def get_prepared(self, **kwargs):
        return check_preparation(buff_instance=self.buff_instance, buff_0=self.buff_0, **kwargs)

    def check_record_module(self):
        if self.equipper is None:
            self.equipper = JudgeTools.find_equipper(
                "啄木鸟电音", sim_instance=self.buff_instance.sim_instance
            )
        if self.buff_0 is None:
            self.buff_0 = JudgeTools.find_exist_buff_dict(
                sim_instance=self.buff_instance.sim_instance
            )[self.equipper][self.buff_instance.ft.index]
        if self.buff_0.history.record is None:
            self.buff_0.history.record = WoodpeckerElectroCARecord()
        self.record = self.buff_0.history.record

    def special_judge_logic(self, **kwargs):
        self.check_record_module()
        self.get_prepared(equipper="啄木鸟电音", enemy=1, dynamic_buff_list=1, action_stack=1)
        skill_node = kwargs.get("skill_node", None)
        if skill_node is None:
            return False
        from zsim.sim_progress.Load import LoadingMission
        from zsim.sim_progress.Preload import SkillNode

        if isinstance(skill_node, SkillNode):
            pass
        elif isinstance(skill_node, LoadingMission):
            skill_node = skill_node.mission_node
        else:
            return False
        if str(self.record.char.CID) not in skill_node.skill_tag:
            return False
        from zsim.sim_progress.ScheduledEvent import Calculator, MultiplierData

        mul_data = MultiplierData(
            self.record.enemy, self.record.dynamic_buff_list, self.record.char
        )
        if skill_node.skill.trigger_buff_level == 4:
            rng: RNG = self.buff_instance.sim_instance.rng_instance
            normalized_value = rng.random_float()
            cric_rate = Calculator.RegularMul.cal_crit_rate(mul_data)
            if normalized_value <= cric_rate:
                return True
            else:
                return False
        else:
            return False
