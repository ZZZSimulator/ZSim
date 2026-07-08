from .. import Buff, check_preparation
from ..JudgeTools import (
    TriggerBuffRef,
    build_preparation_context_from_buff,
    read_trigger_buff_state,
)
from ._preparation_helpers import ensure_owner_template_record, prepare_with_context

_SOLDIER0_ANBY_SILVER_STAR_TRIGGER_REF = TriggerBuffRef.owner(
    "零号·安比",
    "Buff-角色-零号·安比-银星触发器",
)


class Soldier0AnbyAdditionalSkillDMGBonusRecord:
    def __init__(self):
        self.char = None
        self.trigger_buff_0 = None
        self.preload_data = None


class Soldier0AnbyAdditionalSkillDMGBonus(Buff.BuffLogic):
    def __init__(self, buff_instance):
        """
        零号·安比的组队被动，操作角色为安比，并且目标有银星时候，全队增伤。
        """
        super().__init__(buff_instance)
        self.buff_instance: Buff = buff_instance
        self.buff_0 = None
        self.record = None
        self.xjudge = self.special_judge_logic

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
            owner_name="零号·安比",
            record_factory=Soldier0AnbyAdditionalSkillDMGBonusRecord,
            context_builder=build_preparation_context_from_buff,
        )

    def special_judge_logic(self, **kwargs):
        """
        只要是检测到有银星，且正在操作安比，就返回True
        """
        self.check_record_module()
        self.get_prepared(
            char_CID=1381,
            trigger_buff_0=_SOLDIER0_ANBY_SILVER_STAR_TRIGGER_REF,
            preload_data=1,
        )
        trigger_state = read_trigger_buff_state(self.record)
        if trigger_state.active:
            if self.record.preload_data.operating_now == 1381:
                return True
        return False
