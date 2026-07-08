from zsim.sim_progress.calculation.calculator import (
    create_calculator_runtime_read_context_from_sim_instance,
    get_calculator_buff_attribute_reader_service,
)

from .. import Buff, check_preparation
from ..JudgeTools import build_preparation_context_from_buff
from ._preparation_helpers import ensure_equipper_template_record, prepare_with_context


class TimeweaverDisorderDmgMulRecord:
    def __init__(self):
        self.equipper = None
        self.char = None
        self.preload_data = None
        self.dynamic_buff_list = None
        self.enemy = None


class TimeweaverDisorderDmgMul(Buff.BuffLogic):
    """时流贤者的精通AP检查相关Buff逻辑。"""

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
            item_name="时流贤者",
            record_factory=TimeweaverDisorderDmgMulRecord,
            context_builder=build_preparation_context_from_buff,
        )

    def special_judge_logic(self, **kwargs):
        """时流贤者的精通AP检查相关Buff的核心逻辑。"""
        self.check_record_module()
        self.get_prepared(equipper="时流贤者", preload_data=1, enemy=1)

        context = create_calculator_runtime_read_context_from_sim_instance(
            sim_instance=self.buff_instance.sim_instance,
            enemy=self.record.enemy,
            character=self.record.char,
        )
        reader_service = get_calculator_buff_attribute_reader_service()
        ap = reader_service.read_anomaly_proficiency(context)
        return ap >= 375

    def special_exit_logic(self, **kwargs):
        return not self.special_judge_logic(**kwargs)
