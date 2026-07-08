from .. import Buff, check_preparation
from ..JudgeTools import (
    TriggerBuffRef,
    build_preparation_context_from_buff,
    read_trigger_buff_state,
)
from ._preparation_helpers import ensure_equipper_template_record, prepare_with_context


class SpectralGazeImpactBonusRecord:
    def __init__(self):
        self.equipper = None
        self.char = None
        self.trigger_buff_0 = None


class SpectralGazeImpactBonus(Buff.BuffLogic):
    """扳机专武索魂影眸的第3特效——魂锁满层时，获得冲击力增幅，"""

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
            item_name="索魂影眸",
            record_factory=SpectralGazeImpactBonusRecord,
            context_builder=build_preparation_context_from_buff,
        )

    def special_judge_logic(self, **kwargs):
        """检查触发器buff是否是3层"""
        self.check_record_module()
        self.get_prepared(
            equipper="索魂影眸",
            trigger_buff_0=TriggerBuffRef.equipper("索魂影眸-魂锁"),
        )
        trigger_state = read_trigger_buff_state(self.record)
        if trigger_state.active:
            if trigger_state.count == 3:
                return True
        return False

    def special_exit_logic(self, **kwargs):
        if not self.xjudge:
            return True
        return False
