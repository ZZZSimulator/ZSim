from .. import Buff, JudgeTools, check_preparation


class FlamemakerShakerApBonusRecord:
    def __init__(self):
        self.equipper = None
        self.char = None
        self.trigger_buff_0 = None


class FlamemakerShakerApBonus(Buff.BuffLogic):
    """灼心摇壶的精通增幅判定"""

    def __init__(self, buff_instance):
        super().__init__(buff_instance)
        self.buff_instance: Buff = buff_instance
        self.xjudge = self.special_judge_logic
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
                "灼心摇壶", sim_instance=self.buff_instance.sim_instance
            )
        if self.buff_0 is None:
            self.buff_0 = JudgeTools.find_exist_buff_dict(
                sim_instance=self.buff_instance.sim_instance
            )[self.equipper][self.buff_instance.ft.index]
        if self.buff_0.history.record is None:
            self.buff_0.history.record = FlamemakerShakerApBonusRecord()
        self.record = self.buff_0.history.record

    def special_judge_logic(self, **kwargs):
        """检测到目标buff层数>=5时候放行"""
        self.check_record_module()
        self.get_prepared(
            equipper="灼心摇壶", trigger_buff_0=("equipper", "灼心摇壶-增伤")
        )
        if not self.record.trigger_buff_0.dy.active:
            return False
        if self.record.trigger_buff_0.dy.count < 5:
            return False
        return True
