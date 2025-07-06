from zsim.sim_progress.ScheduledEvent.Calculator import (
    Calculator as Cal,
)
from zsim.sim_progress.ScheduledEvent.Calculator import (
    MultiplierData as Mul,
)

from .. import Buff, JudgeTools, check_preparation, find_tick


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
        return check_preparation(
            buff_instance=self.buff_instance, buff_0=self.buff_0, **kwargs
        )

    def check_record_module(self):
        if self.buff_0 is None:
            self.buff_0 = JudgeTools.find_exist_buff_dict(
                sim_instance=self.buff_instance.sim_instance
            )["简"][self.buff_instance.ft.index]
        if self.buff_0.history.record is None:
            self.buff_0.history.record = JaneCoreSkillStrikeCritRateBonusRecord()
        self.record = self.buff_0.history.record

    def special_judge_logic(self, **kwargs):
        """强击暴击率的Debuff情况是和啮咬绑定的。"""
        self.check_record_module()
        self.get_prepared(
            char_CID=1301, trigger_buff_0=("enemy", "Buff-角色-简-核心被动-啮咬触发器")
        )
        if self.record.trigger_buff_0.dy.active:
            return True
        else:
            return False

    def special_hit_logic(self, **kwargs):
        """当触发器激活时，执行self.xhit，计算实时精通，转化成暴击率层数。"""
        self.check_record_module()
        self.get_prepared(
            char_CID=1301,
            trigger_buff_0=("enemy", "Buff-角色-简-核心被动-啮咬触发器"),
            dynamic_buff_list=1,
            enemy=1,
            sub_exist_buff_dict=1,
        )
        mul_data = Mul(
            self.record.enemy, self.record.dynamic_buff_list, self.record.char
        )
        ap = Cal.AnomalyMul.cal_ap(mul_data)
        count = min(40 + ap * 0.16, 100)
        tick = find_tick(sim_instance=self.buff_instance.sim_instance)
        self.buff_instance.simple_start(
            tick, self.record.sub_exist_buff_dict, no_count=1
        )
        self.buff_instance.dy.count = count
        self.buff_instance.update_to_buff_0(self.buff_0)

    def special_exit_logic(self, **kwargs):
        """此Buff退出逻辑和触发逻辑相反"""
        return not self.special_judge_logic()
