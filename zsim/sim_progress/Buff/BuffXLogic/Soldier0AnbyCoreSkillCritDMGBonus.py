from zsim.sim_progress.ScheduledEvent.Calculator import (
    Calculator as Cal,
)
from zsim.sim_progress.ScheduledEvent.Calculator import (
    MultiplierData as Mul,
)

from .. import Buff, JudgeTools, check_preparation


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
        return check_preparation(buff_instance=self.buff_instance, buff_0=self.buff_0, **kwargs)

    def check_record_module(self):
        if self.buff_0 is None:
            self.buff_0 = JudgeTools.find_exist_buff_dict(
                sim_instance=self.buff_instance.sim_instance
            )["零号·安比"][self.buff_instance.ft.index]
        if self.buff_0.history.record is None:
            self.buff_0.history.record = Soldier0AnbyCoreSkillCritDMGBonusRecord()
        self.record = self.buff_0.history.record

    def special_judge_logic(self, **kwargs):
        """
        只要是检测到有银星，就返回True
        """
        self.check_record_module()
        self.get_prepared(
            char_CID=1381,
            trigger_buff_0=("零号·安比", "Buff-角色-零号·安比-银星触发器"),
        )
        if self.record.trigger_buff_0.dy.active:
            return True
        else:
            return False

    def special_hit_logic(self, **kwargs):
        """在Buff触发时，读取安比的暴伤，计算当前的层数"""
        self.check_record_module()
        self.get_prepared(char_CID=1381, dynamic_buff_list=1, enemy=1, sub_exist_buff_dict=1)
        tick_now = JudgeTools.find_tick(sim_instance=self.buff_instance.sim_instance)
        self.buff_instance.simple_start(tick_now, self.record.sub_exist_buff_dict, no_count=1)
        mul_data = Mul(self.record.enemy, self.record.dynamic_buff_list, self.record.char)
        crit_dmg = Cal.RegularMul.cal_personal_crit_dmg(mul_data)
        count = crit_dmg * 0.3 * 100
        self.buff_instance.dy.count = count
        self.buff_instance.update_to_buff_0(self.buff_0)
