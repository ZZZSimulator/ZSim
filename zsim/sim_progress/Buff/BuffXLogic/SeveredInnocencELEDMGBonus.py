from .. import Buff, JudgeTools, check_preparation


class SeveredInnocencELEDMGBonusRecord:
    def __init__(self):
        self.char = None
        self.equipper = None
        self.trigger_buff_0 = None


class SeveredInnocencELEDMGBonus(Buff.BuffLogic):
    """
    牺牲洁纯的电伤判定
    """

    def __init__(self, buff_instance):
        super().__init__(buff_instance)
        self.buff_instance: Buff = buff_instance
        self.buff_0 = None
        self.equipper = None
        self.record = None
        self.xjudge = self.special_judge_logic
        self.xexit = self.special_exit_logic

    def get_prepared(self, **kwargs):
        return check_preparation(
            buff_instance=self.buff_instance, buff_0=self.buff_0, **kwargs
        )

    def check_record_module(self):
        if self.equipper is None:
            self.equipper = JudgeTools.find_equipper(
                "牺牲洁纯", sim_instance=self.buff_instance.sim_instance
            )
        if self.buff_0 is None:
            self.buff_0 = JudgeTools.find_exist_buff_dict(
                sim_instance=self.buff_instance.sim_instance
            )[self.equipper][self.buff_instance.ft.index]
        if self.buff_0.history.record is None:
            self.buff_0.history.record = SeveredInnocencELEDMGBonusRecord()
        self.record = self.buff_0.history.record

    def special_judge_logic(self, **kwargs):
        """查装备者身上的触发暴伤的Buff是否为3层"""
        self.check_record_module()
        self.get_prepared(
            char_CID=1381,
            equipper="牺牲洁纯",
            trigger_buff_0=("equipper", "牺牲洁纯-触发暴伤"),
        )
        if self.record.trigger_buff_0.dy.count == 3:
            if not self.record.trigger_buff_0.dy.active:
                raise ValueError(
                    f"{self.record.trigger_buff_0.ft.index}有层数但是未激活！"
                )
            return True
        return False

    def special_exit_logic(self, **kwargs):
        """xjudge的反逻辑"""
        if self.xjudge:
            return False
        else:
            return True
