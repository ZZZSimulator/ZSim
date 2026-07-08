from .. import Buff, check_preparation
from ..JudgeTools import build_preparation_context_from_buff
from ._preparation_helpers import ensure_equipper_template_record, prepare_with_context
from .enemy_anomaly_read import read_enemy_anomaly_active


class ElectroLipGlossAtkAndDmgBonusRecord:
    def __init__(self):
        self.equipper = None
        self.char = None
        self.enemy = None


class ElectroLipGlossAtkAndDmgBonus(Buff.BuffLogic):
    """触电唇彩判定逻辑"""

    def __init__(self, buff_instance):
        super().__init__(buff_instance)
        self.buff_instance: Buff = buff_instance
        self.xjudge = self.special_judge_logic
        self.xexit = self.special_exit_logic
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
            item_name="触电唇彩",
            record_factory=ElectroLipGlossAtkAndDmgBonusRecord,
            context_builder=build_preparation_context_from_buff,
        )

    def special_judge_logic(self, **kwargs):
        """检测到目标处于异常状态就放行。"""
        self.check_record_module()
        self.get_prepared(equipper="触电唇彩", enemy=1)
        if read_enemy_anomaly_active(self.record.enemy):
            return True
        else:
            return False

    def special_exit_logic(self, **kwargs):
        return not self.special_judge_logic()
