from .. import Buff, JudgeTools, check_preparation
from ....define import YUZUHA_REPORT


class YuzuhaAdditionalAbilityAnomalyBuildupBonusRecord:
    def __init__(self):
        self.char = None
        self.sub_exist_buff_dict = None
        self.dynamic_buff_list = None
        self.enemy = None
        self.cinema_1_ratio = None


class YuzuhaAdditionalAbilityAnomalyBuildupBonus(Buff.BuffLogic):
    def __init__(self, buff_instance):
        super().__init__(buff_instance)
        self.buff_instance: Buff = buff_instance
        self.xhit = self.special_hit_logic
        self.buff_0 = None
        self.record: YuzuhaAdditionalAbilityAnomalyBuildupBonusRecord | None = None

    def get_prepared(self, **kwargs):
        return check_preparation(buff_instance=self.buff_instance, buff_0=self.buff_0, **kwargs)

    def check_record_module(self):
        if self.buff_0 is None:
            self.buff_0 = JudgeTools.find_exist_buff_dict(
                sim_instance=self.buff_instance.sim_instance
            )["柚叶"][self.buff_instance.ft.index]
        if self.buff_0.history.record is None:
            self.buff_0.history.record = YuzuhaAdditionalAbilityAnomalyBuildupBonusRecord()
        self.record = self.buff_0.history.record

    def special_hit_logic(self, **kwargs):
        """buff激活时，根据柚叶的异常掌控计算层数"""
        self.check_record_module()
        self.get_prepared(char_CID=1411, sub_exist_buff_dict=1, enemy=1, dynamic_buff_list=1)
        if self.record.cinema_1_ratio is None:
            self.record.cinema_1_ratio = 1 if self.record.char.cinema < 1 else 1.3
        from zsim.sim_progress.ScheduledEvent.Calculator import MultiplierData
        from zsim.sim_progress.ScheduledEvent import Calculator

        mul_data = MultiplierData(
            self.record.enemy, self.record.dynamic_buff_list, self.record.char
        )
        am = Calculator.AnomalyMul.cal_am(mul_data)
        if am < 100:
            return
        count = min(am - 100, 100) * self.record.cinema_1_ratio
        tick = self.buff_instance.sim_instance.tick
        self.buff_instance.simple_start(
            timenow=tick, sub_exist_buff_dict=self.record.sub_exist_buff_dict, no_count=1
        )
        self.buff_instance.dy.count = count
        self.buff_instance.update_to_buff_0(buff_0=self.buff_0)
