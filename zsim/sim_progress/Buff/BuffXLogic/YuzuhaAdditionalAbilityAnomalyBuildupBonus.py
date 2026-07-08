from zsim.sim_progress.calculation.calculator import (
    create_calculator_runtime_read_context_from_sim_instance,
    get_calculator_buff_attribute_reader_service,
)

from .. import Buff, check_preparation
from ..JudgeTools import build_preparation_context_from_buff
from ._preparation_helpers import ensure_owner_template_record, prepare_with_context


class YuzuhaAdditionalAbilityAnomalyBuildupBonusRecord:
    def __init__(self):
        self.char = None
        self.sub_exist_buff_dict = None
        self.dynamic_buff_list = None
        self.enemy = None
        self.cinema_1_ratio = None


class YuzuhaAdditionalAbilityAnomalyBuildupBonus(Buff.BuffLogic):
    def __init__(self, buff_instance):
        super().__init__(buff_instance)
        self.buff_instance: Buff = buff_instance
        self.xhit = self.special_hit_logic
        self.buff_0 = None
        self.record: YuzuhaAdditionalAbilityAnomalyBuildupBonusRecord | None = None

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
            owner_name="柚叶",
            record_factory=YuzuhaAdditionalAbilityAnomalyBuildupBonusRecord,
            context_builder=build_preparation_context_from_buff,
        )

    def special_hit_logic(self, **kwargs):
        """buff激活时，根据柚叶的异常掌控计算层数"""
        self.check_record_module()
        self.get_prepared(char_CID=1411, sub_exist_buff_dict=1, enemy=1)
        if self.record.cinema_1_ratio is None:
            self.record.cinema_1_ratio = 1 if self.record.char.cinema < 1 else 1.3

        context = create_calculator_runtime_read_context_from_sim_instance(
            sim_instance=self.buff_instance.sim_instance,
            enemy=self.record.enemy,
            character=self.record.char,
        )
        reader_service = get_calculator_buff_attribute_reader_service()
        am = reader_service.read_anomaly_mastery(context)
        if am < 100:
            return
        count = min(am - 100, 100) * self.record.cinema_1_ratio
        tick = self.buff_instance.sim_instance.tick
        self.buff_instance.simple_start(
            timenow=tick, sub_exist_buff_dict=self.record.sub_exist_buff_dict, no_count=1
        )
        self.buff_instance.dy.count = count
        self.buff_instance.update_to_buff_0(buff_0=self.buff_0)
