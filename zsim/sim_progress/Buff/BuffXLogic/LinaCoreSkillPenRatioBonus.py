from zsim.sim_progress.calculation.calculator import (
    create_calculator_runtime_read_context_from_sim_instance,
    get_calculator_buff_attribute_reader_service,
)

from .. import Buff, JudgeTools, check_preparation
from ..JudgeTools import build_preparation_context_from_buff
from ._preparation_helpers import ensure_owner_template_record, prepare_with_context


class LinaCoreSkillRecord:
    def __init__(self):
        self.action_stack = None
        self.char = None
        self.enemy = None
        self.dynamic_buff_list = None
        self.sub_exist_buff_dict = None


class LinaCoreSkillPenRatioBonus(Buff.BuffLogic):
    def __init__(self, buff_instance):
        """
        丽娜核心被动，穿透率增幅。
        """
        super().__init__(buff_instance)
        self.buff_instance: Buff = buff_instance
        self.buff_0 = None
        self.record = None
        self.xjudge = self.special_judge_logic
        self.xstart = self.special_start_logic
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
            owner_name="丽娜",
            record_factory=LinaCoreSkillRecord,
            context_builder=build_preparation_context_from_buff,
        )

    def special_judge_logic(self, **kwargs):
        """
        只要不是重击，就都触发。
        """
        self.check_record_module()
        self.get_prepared(action_stack=1)
        if self.record.action_stack.peek().mission_tag == "1211_SNA_1":
            return False
        else:
            return True

    def special_start_logic(self, **kwargs):
        self.check_record_module()
        self.get_prepared(
            action_stack=1,
            char_CID=1211,
            enemy=1,
            sub_exist_buff_dict=1,
        )
        tick_now = JudgeTools.find_tick(sim_instance=self.buff_instance.sim_instance)
        self.buff_instance.simple_start(tick_now, self.record.sub_exist_buff_dict)
        self.buff_0.dy.count -= self.buff_0.ft.step

        context = create_calculator_runtime_read_context_from_sim_instance(
            sim_instance=self.buff_instance.sim_instance,
            enemy=self.record.enemy,
            character=self.record.char,
        )
        reader_service = get_calculator_buff_attribute_reader_service()
        pen_ratio = reader_service.read_pen_ratio(context)

        count = min(pen_ratio * 0.2 * 100 + 12, self.buff_instance.ft.maxcount)
        self.buff_instance.dy.count = count
        self.buff_instance.update_to_buff_0(self.buff_0)

    def special_exit_logic(self, **kwargs):
        """
        只要检测到重击，就立刻终止。
        """
        self.check_record_module()
        self.get_prepared(action_stack=1)
        if self.record.action_stack.peek().mission_tag != "1211_SNA_1":
            tick = JudgeTools.find_tick(sim_instance=self.buff_instance.sim_instance)
            if self.buff_instance.dy.endticks <= tick:
                return True
            return False
        else:
            return True
