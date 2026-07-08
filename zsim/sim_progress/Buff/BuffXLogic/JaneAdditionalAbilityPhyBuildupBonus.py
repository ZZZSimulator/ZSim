from .. import Buff, check_preparation
from ..JudgeTools import build_preparation_context_from_buff
from ._preparation_helpers import ensure_owner_template_record, prepare_with_context
from .enemy_anomaly_read import read_enemy_anomaly_active


class JaneAdditionalAbilityPhyBuildupBonusRecord:
    def __init__(self):
        self.char = None
        self.trigger_buff_0 = None
        self.dynamic_buff_list = None
        self.enemy = None
        self.sub_exist_buff_dict = None


class JaneAdditionalAbilityPhyBuildupBonus(Buff.BuffLogic):
    def __init__(self, buff_instance):
        """简组队被动中第二特效的复杂逻辑"""
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
            record_factory=JaneAdditionalAbilityPhyBuildupBonusRecord,
            context_builder=build_preparation_context_from_buff,
        )

    def special_judge_logic(self, **kwargs):
        """简组队被动的第二特效是：只要有敌人处于异常状态即可触发，所以只要有任意一种异常处于激活状态，就可以放行。"""
        self.check_record_module()
        self.get_prepared(char_CID=1261, enemy=1)
        return read_enemy_anomaly_active(self.record.enemy)

    def special_exit_logic(self, **kwargs):
        """此Buff退出逻辑和触发逻辑相反"""
        return not self.special_judge_logic()
