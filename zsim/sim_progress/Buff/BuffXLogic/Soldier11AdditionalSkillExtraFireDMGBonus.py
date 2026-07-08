from .. import Buff, check_preparation
from ..JudgeTools import build_preparation_context_from_buff
from ._preparation_helpers import ensure_owner_template_record, prepare_with_context
from .enemy_state_read import read_enemy_stun_active


class Slodier11AdditionalSkillRecord:
    def __init__(self):
        self.enemy = None


class Soldier11AdditionalSkillExtraFireDMGBonus(Buff.BuffLogic):
    def __init__(self, buff_instance):
        """
        11号组队被动：失衡期间额外火伤。
        """
        super().__init__(buff_instance)
        self.buff_instance: Buff = buff_instance
        self.xjudge = self.special_judge_logic
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
            owner_name="11号",
            record_factory=Slodier11AdditionalSkillRecord,
            context_builder=build_preparation_context_from_buff,
        )

    def special_judge_logic(self, **kwargs):
        self.check_record_module()
        self.get_prepared(enemy=1)
        if read_enemy_stun_active(self.record.enemy):
            return True
        else:
            return False
