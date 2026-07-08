from .. import Buff, check_preparation
from ..JudgeTools import (
    TriggerBuffRef,
    build_preparation_context_from_buff,
    read_trigger_buff_state,
)
from ._preparation_helpers import ensure_equipper_template_record, prepare_with_context


class FlamemakerShakerApBonusRecord:
    def __init__(self):
        self.equipper = None
        self.char = None
        self.trigger_buff_0 = None


class FlamemakerShakerApBonus(Buff.BuffLogic):
    """灼心摇壶的精通增幅判定"""

    def __init__(self, buff_instance):
        super().__init__(buff_instance)
        self.buff_instance: Buff = buff_instance
        self.xjudge = self.special_judge_logic
        self.equipper = None
        self.buff_0 = None
        self.record = None

    def get_prepared(self, **kwargs):
        return prepare_with_context(
            self,
            check_preparation_func=check_preparation,
            context_builder=build_preparation_context_from_buff,
            **kwargs,
        )

    def check_record_module(self):
        ensure_equipper_template_record(
            self,
            item_name="灼心摇壶",
            record_factory=FlamemakerShakerApBonusRecord,
            context_builder=build_preparation_context_from_buff,
        )

    def special_judge_logic(self, **kwargs):
        """检测到目标buff层数>=5时候放行"""
        self.check_record_module()
        self.get_prepared(
            equipper="灼心摇壶",
            trigger_buff_0=TriggerBuffRef.equipper("灼心摇壶-增伤"),
        )
        trigger_state = read_trigger_buff_state(self.record)
        if not trigger_state.active:
            return False
        if trigger_state.count < 5:
            return False
        return True
