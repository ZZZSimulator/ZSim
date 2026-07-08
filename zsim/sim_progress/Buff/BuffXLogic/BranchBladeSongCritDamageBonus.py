from zsim.sim_progress.calculation.calculator import (
    create_calculator_runtime_read_context_from_sim_instance,
    get_calculator_buff_attribute_reader_service,
)

from .. import Buff, check_preparation
from ..JudgeTools import build_preparation_context_from_buff
from ._preparation_helpers import ensure_equipper_template_record, prepare_with_context


class BranchBladeSongRecord:
    def __init__(self):
        self.equipper = None
        self.enemy = None
        self.dynamic_buff_list = None
        self.char = None


class BranchBladeSongCritDamageBonus(Buff.BuffLogic):
    """
    该buff是新冰4件套中的第一特效：异常掌控>=115就会触发。
    由于不能实现“异常掌控>=115时候，将buff.ft.alltime修改为True的操作，
    所以只能让该buff在每个动作都检测，然后每个动作都触发，用来平替alltime。
    """

    def __init__(self, buff_instance):
        super().__init__(buff_instance)
        self.buff_instance: Buff = buff_instance
        self.xjudge = self.special_judge_logic
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
            item_name="折枝剑歌",
            record_factory=BranchBladeSongRecord,
            context_builder=build_preparation_context_from_buff,
        )

    def special_judge_logic(self, **kwargs):
        self.check_record_module()
        self.get_prepared(equipper="折枝剑歌", enemy=1)
        context = create_calculator_runtime_read_context_from_sim_instance(
            sim_instance=self.buff_instance.sim_instance,
            enemy=self.record.enemy,
            character=self.record.char,
        )
        reader_service = get_calculator_buff_attribute_reader_service()
        am = reader_service.read_anomaly_mastery(context)
        if am >= 115:
            return True
        return False
