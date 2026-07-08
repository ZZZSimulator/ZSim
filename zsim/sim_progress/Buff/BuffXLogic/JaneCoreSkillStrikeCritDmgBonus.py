from .. import Buff, check_preparation
from ..JudgeTools import (
    TriggerBuffRef,
    build_preparation_context_from_buff,
    read_trigger_buff_state,
)
from ._preparation_helpers import ensure_owner_template_record, prepare_with_context

_JANE_BITE_TRIGGER_REF = TriggerBuffRef.enemy("Buff-角色-简-核心被动-啮咬触发器")


class JaneCoreSkillStrikeCritDmgBonusRecord:
    def __init__(self):
        self.char = None
        self.trigger_buff_0 = None
        self.dynamic_buff_list = None
        self.enemy = None
        self.sub_exist_buff_dict = None


class JaneCoreSkillStrikeCritDmgBonus(Buff.BuffLogic):
    def __init__(self, buff_instance):
        """简核心被动中，强击暴击伤害的复杂逻辑"""
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
            record_factory=JaneCoreSkillStrikeCritDmgBonusRecord,
            context_builder=build_preparation_context_from_buff,
        )

    def special_judge_logic(self, **kwargs):
        """强击的暴伤Debuff情况是和啮咬绑定的。"""
        self.check_record_module()
        self.get_prepared(char_CID=1261, trigger_buff_0=_JANE_BITE_TRIGGER_REF)
        trigger_state = read_trigger_buff_state(self.record)
        return trigger_state.active

    def special_exit_logic(self, **kwargs):
        """此Buff退出逻辑和触发逻辑相反"""
        return not self.special_judge_logic()
