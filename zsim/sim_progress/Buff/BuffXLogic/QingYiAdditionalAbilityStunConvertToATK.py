from zsim.sim_progress.calculation.calculator import (
    create_calculator_runtime_read_context_from_sim_instance,
    get_calculator_buff_attribute_reader_service,
)

from .. import Buff, JudgeTools, check_preparation
from ..JudgeTools import build_preparation_context_from_buff
from ._preparation_helpers import ensure_owner_template_record, prepare_with_context


class QingYiAdditionalSkillRecord:
    def __init__(self):
        self.char = None
        self.enemy = None
        self.sub_exist_buff_dict = None
        self.dynamic_buff_list = None


class QingYiAdditionalAbilityStunConvertToATK(Buff.BuffLogic):
    def __init__(self, buff_instance):
        """
        青衣的组队被动之冲击力转模部分。
        """
        super().__init__(buff_instance)
        self.buff_instance: Buff = buff_instance
        self.buff_0 = None
        self.record = None
        self.xjudge = self.special_judge_logic
        self.xhit = self.special_hit_logic

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
            owner_name="青衣",
            record_factory=QingYiAdditionalSkillRecord,
            context_builder=build_preparation_context_from_buff,
        )

    def special_judge_logic(self, **kwargs):
        return True

    def special_hit_logic(self, **kwargs):
        """
        找冲击力，并且构建mul现场算。算完出层数即可。
        """
        self.check_record_module()
        self.get_prepared(char_CID=1251, enemy=1, sub_exist_buff_dict=1)
        tick_now = JudgeTools.find_tick(sim_instance=self.buff_instance.sim_instance)
        self.buff_instance.simple_start(tick_now, self.record.sub_exist_buff_dict)
        self.buff_0.dy.count -= self.buff_0.ft.step
        context = create_calculator_runtime_read_context_from_sim_instance(
            sim_instance=self.buff_instance.sim_instance,
            enemy=self.record.enemy,
            character=self.record.char,
        )
        reader_service = get_calculator_buff_attribute_reader_service()
        stun_value = reader_service.read_impact(context)
        count = min((stun_value - 120) * 6, self.buff_instance.ft.maxcount)
        self.buff_instance.dy.count = count
        self.buff_instance.update_to_buff_0(self.buff_0)
