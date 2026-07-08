from .. import Buff, check_preparation
from ..JudgeTools import build_preparation_context_from_buff
from ._preparation_helpers import ensure_owner_template_record, prepare_with_context


class YuzuhaCinema6SugarBurstMaxTriggerRecord:
    def __init__(self):
        self.char = None
        self.enemy = None


class YuzuhaCinema6SugarBurstMaxTrigger(Buff.BuffLogic):
    """炮弹命中甜蜜惊吓状态的敌人时，会触发一次彩糖花火·极"""

    def __init__(self, buff_instance):
        super().__init__(buff_instance)
        self.buff_instance: Buff = buff_instance
        self.xjudge = self.special_judge_logic
        self.xhit = self.special_hit_logic
        self.buff_0 = None
        self.record: YuzuhaCinema6SugarBurstMaxTriggerRecord | None = None

    def get_prepared(self, **kwargs):
        return prepare_with_context(
            self,
            check_preparation_func=check_preparation,
            context_builder=build_preparation_context_from_buff,
            **kwargs,
        )

    def check_record_module(self):
        ensure_owner_template_record(
            self,
            owner_name="柚叶",
            record_factory=YuzuhaCinema6SugarBurstMaxTriggerRecord,
            context_builder=build_preparation_context_from_buff,
        )

    def special_judge_logic(self, **kwargs):
        self.check_record_module()
        self.get_prepared(char_CID=1411, enemy=1)
        skill_node = kwargs.get("skill_node")
        if skill_node is None:
            return False
        if skill_node.skill_tag != "1411_Cinema_6":
            return False
        if self.record.enemy.special_state_manager:
            pass
        return False
