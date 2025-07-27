from zsim.sim_progress.ScheduledEvent import Calculator
from zsim.sim_progress.ScheduledEvent.Calculator import MultiplierData

from .. import Buff, JudgeTools, check_preparation


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
        return check_preparation(buff_instance=self.buff_instance, buff_0=self.buff_0, **kwargs)

    def check_record_module(self):
        if self.equipper is None:
            self.equipper = JudgeTools.find_equipper(
                "折枝剑歌", sim_instance=self.buff_instance.sim_instance
            )
        if self.buff_0 is None:
            self.buff_0 = JudgeTools.find_exist_buff_dict(
                sim_instance=self.buff_instance.sim_instance
            )[self.equipper][self.buff_instance.ft.index]
        if self.buff_0.history.record is None:
            self.buff_0.history.record = BranchBladeSongRecord()
        self.record = self.buff_0.history.record

    def special_judge_logic(self, **kwargs):
        self.check_record_module()
        self.get_prepared(equipper="折枝剑歌", enemy=1, dynamic_buff_list=1)
        mul_data = MultiplierData(
            self.record.enemy, self.record.dynamic_buff_list, self.record.char
        )
        am = Calculator.AnomalyMul.cal_am(mul_data)
        if am >= 115:
            return True
        return False
