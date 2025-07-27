from .. import Buff, JudgeTools, check_preparation


class YunkuiTalesSheerAtkBonusRecord:
    def __init__(self):
        self.equipper = None
        self.char = None
        self.trigger_buff_0 = None


class YunkuiTalesSheerAtkBonus(Buff.BuffLogic):
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
                "云岿如我", sim_instance=self.buff_instance.sim_instance
            )
        if self.buff_0 is None:
            self.buff_0 = JudgeTools.find_exist_buff_dict(
                sim_instance=self.buff_instance.sim_instance
            )[self.equipper][self.buff_instance.ft.index]
        if self.buff_0.history.record is None:
            self.buff_0.history.record = YunkuiTalesSheerAtkBonusRecord()
        self.record = self.buff_0.history.record

    def special_judge_logic(self, **kwargs):
        self.check_record_module()
        self.get_prepared(
            equipper="云岿如我",
            trigger_buff_0=(self.equipper, "Buff-驱动盘-云岿如我-四件套-暴击率提升"),
        )
        trigger_buff_0: Buff = self.record.trigger_buff_0
        if trigger_buff_0.dy.active:
            if trigger_buff_0.dy.count == 3:
                return True
        return False
