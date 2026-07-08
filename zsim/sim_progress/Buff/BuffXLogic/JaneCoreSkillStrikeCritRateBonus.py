from zsim.sim_progress.calculation.calculator import (
    get_calculator_buff_attribute_reader_service,
)

from .. import Buff, check_preparation, find_tick
from ..JudgeTools import (
    TriggerBuffRef,
    build_preparation_context_from_buff,
    create_calculator_runtime_read_context_from_sim_instance,
    read_trigger_buff_state_active,
)
from ._preparation_helpers import ensure_owner_template_record, prepare_with_context

_JANE_BITE_TRIGGER_REF = TriggerBuffRef.enemy("Buff-角色-简-核心被动-啮咬触发器")


class JaneCoreSkillStrikeCritRateBonusRecord:
    def __init__(self):
        self.char = None
        self.trigger_buff_0 = None
        self.dynamic_buff_list = None
        self.enemy = None
        self.sub_exist_buff_dict = None


class JaneCoreSkillStrikeCritRateBonus(Buff.BuffLogic):
    def __init__(self, buff_instance):
        """简核心被动中，强击暴击率的复杂逻辑"""
        super().__init__(buff_instance)
        self.buff_instance: Buff = buff_instance
        self.buff_0 = None
        self.record = None
        self.xjudge = self.special_judge_logic
        self.xhit = self.special_hit_logic
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
            record_factory=JaneCoreSkillStrikeCritRateBonusRecord,
            context_builder=build_preparation_context_from_buff,
        )

    def special_judge_logic(self, **kwargs):
        """强击暴击率的Debuff情况是和啮咬绑定的。"""
        self.check_record_module()
        self.get_prepared(char_CID=1261, trigger_buff_0=_JANE_BITE_TRIGGER_REF)
        return read_trigger_buff_state_active(self.record)

    def special_hit_logic(self, **kwargs):
        """当触发器激活时，执行self.xhit，计算实时精通，转化成暴击率层数。"""
        self.check_record_module()
        self.get_prepared(
            char_CID=1261,
            trigger_buff_0=_JANE_BITE_TRIGGER_REF,
            enemy=1,
            sub_exist_buff_dict=1,
        )
        context = create_calculator_runtime_read_context_from_sim_instance(
            sim_instance=self.buff_instance.sim_instance,
            enemy=self.record.enemy,
            character=self.record.char,
        )
        reader_service = get_calculator_buff_attribute_reader_service()
        ap = reader_service.read_anomaly_proficiency(context)
        count = min(40 + ap * 0.16, 100)
        tick = find_tick(sim_instance=self.buff_instance.sim_instance)
        self.buff_instance.simple_start(tick, self.record.sub_exist_buff_dict, no_count=1)
        self.buff_instance.dy.count = count
        self.buff_instance.update_to_buff_0(self.buff_0)

    def special_exit_logic(self, **kwargs):
        """此Buff退出逻辑和触发逻辑相反"""
        return not self.special_judge_logic()
