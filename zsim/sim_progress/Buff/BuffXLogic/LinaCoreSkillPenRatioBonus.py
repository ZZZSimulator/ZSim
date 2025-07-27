from zsim.sim_progress.ScheduledEvent.Calculator import (
    Calculator as Cal,
)
from zsim.sim_progress.ScheduledEvent.Calculator import (
    MultiplierData as Mul,
)

from .. import Buff, JudgeTools, check_preparation


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
        return check_preparation(buff_instance=self.buff_instance, buff_0=self.buff_0, **kwargs)

    def check_record_module(self):
        if self.buff_0 is None:
            self.buff_0 = JudgeTools.find_exist_buff_dict(
                sim_instance=self.buff_instance.sim_instance
            )["丽娜"][self.buff_instance.ft.index]
        if self.buff_0.history.record is None:
            self.buff_0.history.record = LinaCoreSkillRecord()
        self.record = self.buff_0.history.record

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

    def special_start_logic(self):
        self.check_record_module()
        self.get_prepared(
            action_stack=1,
            char_CID=1211,
            dynamic_buff_list=1,
            enemy=1,
            sub_exist_buff_dict=1,
        )
        tick_now = JudgeTools.find_tick(sim_instance=self.buff_instance.sim_instance)
        self.buff_instance.simple_start(tick_now, self.record.sub_exist_buff_dict)
        self.buff_0.dy.count -= self.buff_0.ft.step
        mul_data = Mul(self.record.enemy, self.record.dynamic_buff_list, self.record.char)

        pen_ratio = Cal.RegularMul.cal_pen_ratio(mul_data)

        count = min(pen_ratio * 0.2 * 100 + 12, self.buff_instance.ft.maxcount)
        self.buff_instance.dy.count = count
        self.buff_instance.update_to_buff_0(self.buff_0)

    def special_exit_logic(self):
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
