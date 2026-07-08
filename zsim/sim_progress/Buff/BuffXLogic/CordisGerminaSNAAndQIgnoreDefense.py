from .. import Buff, check_preparation
from ..JudgeTools import (
    TriggerBuffRef,
    build_preparation_context_from_buff,
    read_trigger_buff_state,
)
from ._buff_record_base_class import BuffRecordBaseClass as Brbc
from ._preparation_helpers import ensure_equipper_template_record, prepare_with_context


class CordisGerminaSNAAndQIgnoreDefenseRecord(Brbc):
    def __init__(self):
        super().__init__()


class CordisGerminaSNAAndQIgnoreDefense(Buff.BuffLogic):
    def __init__(self, buff_instance):
        """这是机巧心种普攻大招无视防御Buff的脚本"""
        super().__init__(buff_instance)
        self.buff_instance: Buff = buff_instance
        self.xjudge = self.special_judge_logic
        self.xexit = self.special_exit_logic
        self.equipper = None
        self.buff_0 = None
        self.record: CordisGerminaSNAAndQIgnoreDefenseRecord | None = None

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
            item_name="机巧心种",
            record_factory=CordisGerminaSNAAndQIgnoreDefenseRecord,
            context_builder=build_preparation_context_from_buff,
        )

    def special_judge_logic(self, **kwargs):
        self.check_record_module()
        self.get_prepared(
            equipper="机巧心种",
            trigger_buff_0=TriggerBuffRef.equipper("机巧心种-电属性增伤"),
        )
        assert self.record is not None
        trigger_state = read_trigger_buff_state(self.record)
        result = len(trigger_state.built_in_buff_box) == 2
        return result

    def special_exit_logic(self, **kwargs):
        return not self.special_judge_logic(**kwargs)
