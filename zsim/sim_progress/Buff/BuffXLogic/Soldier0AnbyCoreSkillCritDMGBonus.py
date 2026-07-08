from zsim.sim_progress.calculation.calculator import (
    get_calculator_buff_attribute_reader_service,
)

from .. import Buff, JudgeTools, check_preparation
from ..JudgeTools import (
    TriggerBuffRef,
    build_preparation_context_from_buff,
    create_calculator_runtime_read_context_from_sim_instance,
    read_trigger_buff_state_active,
)
from ._preparation_helpers import ensure_owner_template_record, prepare_with_context

_SOLDIER0_ANBY_SILVER_STAR_TRIGGER_REF = TriggerBuffRef.owner(
    "零号·安比",
    "Buff-角色-零号·安比-银星触发器",
)


class Soldier0AnbyCoreSkillCritDMGBonusRecord:
    def __init__(self):
        self.char = None
        self.dynamic_buff_list = None
        self.enemy = None
        self.sub_exist_buff_dict = None
        self.trigger_buff_0 = None


class Soldier0AnbyCoreSkillCritDMGBonus(Buff.BuffLogic):
    def __init__(self, buff_instance):
        """
        零号·安比的核心被动，银星有层数就触发增伤。
        """
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
            owner_name="零号·安比",
            record_factory=Soldier0AnbyCoreSkillCritDMGBonusRecord,
            context_builder=build_preparation_context_from_buff,
        )

    def special_judge_logic(self, **kwargs):
        """
        只要是检测到有银星，就返回True
        """
        self.check_record_module()
        self.get_prepared(
            char_CID=1381,
            trigger_buff_0=_SOLDIER0_ANBY_SILVER_STAR_TRIGGER_REF,
        )
        if read_trigger_buff_state_active(self.record):
            return True
        else:
            return False

    def special_hit_logic(self, **kwargs):
        """在Buff触发时，读取安比的暴伤，计算当前的层数"""
        self.check_record_module()
        self.get_prepared(char_CID=1381, enemy=1, sub_exist_buff_dict=1)
        tick_now = JudgeTools.find_tick(sim_instance=self.buff_instance.sim_instance)
        self.buff_instance.simple_start(tick_now, self.record.sub_exist_buff_dict, no_count=1)
        context = create_calculator_runtime_read_context_from_sim_instance(
            sim_instance=self.buff_instance.sim_instance,
            enemy=self.record.enemy,
            character=self.record.char,
        )
        reader_service = get_calculator_buff_attribute_reader_service()
        crit_dmg = reader_service.read_personal_crit_damage(context)
        count = crit_dmg * 0.3 * 100
        self.buff_instance.dy.count = count
        self.buff_instance.update_to_buff_0(self.buff_0)
