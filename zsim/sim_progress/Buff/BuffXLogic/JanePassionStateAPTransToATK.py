from math import floor

from zsim.sim_progress.ScheduledEvent.Calculator import (
    Calculator as Cal,
)
from zsim.sim_progress.ScheduledEvent.Calculator import (
    MultiplierData as Mul,
)

from .. import Buff, JudgeTools, check_preparation, find_tick


class JanePassionStateAPTransToATKRecord:
    def __init__(self):
        self.char = None
        self.trigger_buff_0 = None
        self.dynamic_buff_list = None
        self.enemy = None
        self.sub_exist_buff_dict = None


class JanePassionStateAPTransToATK(Buff.BuffLogic):
    def __init__(self, buff_instance):
        """狂热状态下的精通转攻击力"""
        super().__init__(buff_instance)
        self.buff_instance: Buff = buff_instance
        self.buff_0 = None
        self.record = None
        self.xjudge = self.special_judge_logic
        self.xhit = self.special_hit_logic
        self.xexit = self.special_exit_logic

    def get_prepared(self, **kwargs):
        return check_preparation(buff_instance=self.buff_instance, buff_0=self.buff_0, **kwargs)

    def check_record_module(self):
        if self.buff_0 is None:
            self.buff_0 = JudgeTools.find_exist_buff_dict(
                sim_instance=self.buff_instance.sim_instance
            )["简"][self.buff_instance.ft.index]
        if self.buff_0.history.record is None:
            self.buff_0.history.record = JanePassionStateAPTransToATKRecord()
        self.record = self.buff_0.history.record

    def special_judge_logic(self, **kwargs):
        """精通转攻击力部分的触发行为与触发器对齐；"""
        self.check_record_module()
        self.get_prepared(char_CID=1301, trigger_buff_0=("简", "Buff-角色-简-狂热状态触发器"))
        if self.record.trigger_buff_0.dy.active:
            return True
        else:
            return False

    def special_hit_logic(self, **kwargs):
        """当触发器激活时，执行self.xhit，计算实时精通，激活自身状态并且更新层数。"""
        self.check_record_module()
        self.get_prepared(
            char_CID=1301,
            trigger_buff_0=("简", "Buff-角色-简-狂热状态触发器"),
            dynamic_buff_list=1,
            enemy=1,
            sub_exist_buff_dict=1,
        )
        mul_data = Mul(self.record.enemy, self.record.dynamic_buff_list, self.record.char)
        ap = Cal.AnomalyMul.cal_ap(mul_data)
        count = floor(
            max(ap - 120, 0)
        )  # 超过120点的部分，每1点叠1层，这里应该是向下取证，比如120.1，那就不叠层。
        tick = find_tick(sim_instance=self.buff_instance.sim_instance)
        self.buff_instance.simple_start(tick, self.record.sub_exist_buff_dict, no_count=1)
        self.buff_instance.dy.count = count
        self.buff_instance.update_to_buff_0(self.buff_0)

    def special_exit_logic(self, **kwargs):
        """精通转攻击力Buff的退出逻辑与触发器相反"""
        return not self.special_judge_logic()
