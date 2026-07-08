from .. import Buff, check_preparation
from ..JudgeTools import (
    TriggerBuffRef,
    build_preparation_context_from_buff,
    read_trigger_buff_state,
)
from ._preparation_helpers import ensure_owner_template_record, prepare_with_context

_YANGI_CINEMA1_TRIGGER_REF = TriggerBuffRef.owner(
    "柳",
    "Buff-角色-柳-1画-洞悉",
)


class YangiCinema1ApBonusRecord:
    def __init__(self):
        self.char = None
        self.trigger_buff_0 = None


class YangiCinema1ApBonus(Buff.BuffLogic):
    """柳1画的精通增幅"""

    def __init__(self, buff_instance):
        super().__init__(buff_instance)
        self.buff_instance: Buff = buff_instance
        self.xjudge = self.special_judge_logic
        self.xexit = self.special_exit_logic
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
        ensure_owner_template_record(
            self,
            owner_name="柳",
            record_factory=YangiCinema1ApBonusRecord,
            context_builder=build_preparation_context_from_buff,
        )

    def special_judge_logic(self, **kwargs):
        """
        检测触发器Buff洞悉的层数，层数>= 1 就触发！
        """
        self.check_record_module()
        self.get_prepared(char_CID=1221, trigger_buff_0=_YANGI_CINEMA1_TRIGGER_REF)
        trigger_state = read_trigger_buff_state(self.record)
        if trigger_state.active:
            if trigger_state.count >= 1:
                return True
        return False

    def special_exit_logic(self, **kwargs):
        """退出逻辑和触发逻辑相反！"""
        return not self.special_judge_logic(**kwargs)
