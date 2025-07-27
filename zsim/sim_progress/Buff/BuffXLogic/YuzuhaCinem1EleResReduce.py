from .. import Buff, JudgeTools, check_preparation
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...Preload import SkillNode


class YuzuhaCinem1EleResReduceRecord:
    def __init__(self):
        self.char = None
        self.enemy = None


class YuzuhaCinem1EleResReduce(Buff.BuffLogic):
    def __init__(self, buff_instance):
        """柚叶的1画，一样是甜蜜惊吓判定逻辑"""
        super().__init__(buff_instance)
        self.buff_instance: Buff = buff_instance
        self.buff_0 = None
        self.record = None
        self.xjudge = self.special_judge_logic

    def get_prepared(self, **kwargs):
        return check_preparation(buff_instance=self.buff_instance, buff_0=self.buff_0, **kwargs)

    def check_record_module(self):
        if self.buff_0 is None:
            self.buff_0 = JudgeTools.find_exist_buff_dict(
                sim_instance=self.buff_instance.sim_instance
            )["柚叶"][self.buff_instance.ft.index]
        if self.buff_0.history.record is None:
            self.buff_0.history.record = YuzuhaCinem1EleResReduceRecord()
        self.record = self.buff_0.history.record

    def special_judge_logic(self, **kwargs):
        """只有两种强化E和大招的重攻击才能触发甜蜜惊吓效果"""
        self.check_record_module()
        self.get_prepared(char_CID=1411, enemy=1)
        skill_node: "SkillNode" = kwargs.get("skill_node")
        if skill_node is None:
            return False
        if skill_node.skill_tag not in ["1411_E_EX_A", "1411_E_EX_B", "1411_Q"]:
            return False
        if not skill_node.is_last_hit(tick=self.buff_instance.sim_instance.tick):
            return False
        else:
            return True
