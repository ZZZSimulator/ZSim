from .. import Buff, check_preparation
from ..JudgeTools import (
    TriggerBuffRef,
    build_preparation_context_from_buff,
    read_trigger_buff_state,
)
from ._preparation_helpers import ensure_owner_template_record, prepare_with_context

_JANE_PASSION_TRIGGER_REF = TriggerBuffRef.owner("简", "Buff-角色-简-狂热状态触发器")


class JanePassionStatePhyBuildupBonusRecord:
    def __init__(self):
        self.char = None
        self.trigger_buff_0 = None


class JanePassionStatePhyBuildupBonus(Buff.BuffLogic):
    def __init__(self, buff_instance):
        """狂热状态下的积蓄效率的判定逻辑"""
        super().__init__(buff_instance)
        self.buff_instance: Buff = buff_instance
        self.buff_0 = None
        self.record = None
        self.xjudge = self.special_judge_logic
        self.xexit = self.special_exit_logic

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
            owner_name="简",
            record_factory=JanePassionStatePhyBuildupBonusRecord,
            context_builder=build_preparation_context_from_buff,
        )

    def special_judge_logic(self, **kwargs):
        """积蓄效率Buff的判定和触发器有关，其状态和触发器相同"""
        self.check_record_module()
        self.get_prepared(char_CID=1261, trigger_buff_0=_JANE_PASSION_TRIGGER_REF)

        trigger_state = read_trigger_buff_state(self.record)
        return trigger_state.active

    def special_exit_logic(self, **kwargs):
        """积蓄效率的退出逻辑与触发器相反"""
        return not self.special_judge_logic()
