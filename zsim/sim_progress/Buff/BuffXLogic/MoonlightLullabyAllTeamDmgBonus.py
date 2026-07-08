from .. import Buff, check_preparation
from ..JudgeTools import build_preparation_context_from_buff
from ._preparation_helpers import ensure_equipper_template_record, prepare_with_context


class MoonlightLullabyAllTeamDmgBonusRecord:
    def __init__(self):
        self.equipper = None
        self.char = None


class MoonlightLullabyAllTeamDmgBonus(Buff.BuffLogic):
    def __init__(self, buff_instance):
        """这是月光骑士颂全队增伤Buff的脚本"""
        super().__init__(buff_instance)
        self.buff_instance: Buff = buff_instance
        self.xjudge = self.special_judge_logic
        self.equipper = None
        self.buff_0 = None
        self.record: MoonlightLullabyAllTeamDmgBonusRecord | None = None

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
            item_name="月光骑士颂",
            record_factory=MoonlightLullabyAllTeamDmgBonusRecord,
            context_builder=build_preparation_context_from_buff,
        )

    def special_judge_logic(self, **kwargs):
        self.check_record_module()
        self.get_prepared(equipper="月光骑士颂")
