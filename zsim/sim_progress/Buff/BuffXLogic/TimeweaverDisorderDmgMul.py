from .. import Buff, JudgeTools, check_preparation


class TimeweaverDisorderDmgMulRecord:
    def __init__(self):
        self.equipper = None
        self.char = None
        self.preload_data = None
        self.dynamic_buff_list = None
        self.enemy = None


class TimeweaverDisorderDmgMul(Buff.BuffLogic):
    """时流贤者的精通AP检查相关Buff逻辑。"""

    def __init__(self, buff_instance):
        super().__init__(buff_instance)
        self.buff_instance: Buff = buff_instance
        self.xjudge = self.special_judge_logic
        self.xexit = self.special_exit_logic
        self.equipper = None
        self.buff_0 = None
        self.record = None

    def get_prepared(self, **kwargs):
        return check_preparation(
            buff_instance=self.buff_instance, buff_0=self.buff_0, **kwargs
        )

    def check_record_module(self):
        if self.equipper is None:
            self.equipper = JudgeTools.find_equipper(
                "时流贤者", sim_instance=self.buff_instance.sim_instance
            )
        if self.buff_0 is None:
            self.buff_0 = JudgeTools.find_exist_buff_dict(
                sim_instance=self.buff_instance.sim_instance
            )[self.equipper][self.buff_instance.ft.index]
        if self.buff_0.history.record is None:
            self.buff_0.history.record = TimeweaverDisorderDmgMulRecord()
        self.record = self.buff_0.history.record

    def special_judge_logic(self, **kwargs):
        """时流贤者的精通AP检查相关Buff的核心逻辑。"""
        self.check_record_module()
        self.get_prepared(
            equipper="时流贤者", preload_data=1, dynamic_buff_list=1, enemy=1
        )
        from zsim.sim_progress.ScheduledEvent.Calculator import (
            Calculator as Cal,
        )
        from zsim.sim_progress.ScheduledEvent.Calculator import (
            MultiplierData as Mul,
        )

        mul_data = Mul(
            self.record.enemy, self.record.dynamic_buff_list, self.record.char
        )
        ap = Cal.AnomalyMul.cal_ap(mul_data)
        return ap >= 375

    def special_exit_logic(self, **kwargs):
        return not self.special_judge_logic(**kwargs)
