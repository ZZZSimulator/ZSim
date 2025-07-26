from .. import Buff, JudgeTools, check_preparation


class YangiCinema1ApBonusRecord:
    def __init__(self):
        self.char = None
        self.trigger_buff_0 = None


class YangiCinema1ApBonus(Buff.BuffLogic):
    """柳1画的精通增幅"""

    def __init__(self, buff_instance):
        super().__init__(buff_instance)
        self.buff_instance: Buff = buff_instance
        self.xjudge = self.special_judge_logic
        self.xexit = self.special_exit_logic
        self.buff_0 = None
        self.record = None

    def get_prepared(self, **kwargs):
        return check_preparation(buff_instance=self.buff_instance, buff_0=self.buff_0, **kwargs)

    def check_record_module(self):
        if self.buff_0 is None:
            self.buff_0 = JudgeTools.find_exist_buff_dict(
                sim_instance=self.buff_instance.sim_instance
            )["柳"][self.buff_instance.ft.index]
        if self.buff_0.history.record is None:
            self.buff_0.history.record = YangiCinema1ApBonusRecord()
        self.record = self.buff_0.history.record

    def special_judge_logic(self, **kwargs):
        """
        检测触发器Buff洞悉的层数，层数>= 1 就触发！
        """
        self.check_record_module()
        self.get_prepared(char_CID=1221, trigger_buff_0=("柳", "Buff-角色-柳-1画-洞悉"))
        if self.record.trigger_buff_0.dy.active:
            if self.record.trigger_buff_0.dy.count >= 1:
                return True
        return False

    def special_exit_logic(self, **kwargs):
        """退出逻辑和触发逻辑相反！"""
        return not self.special_judge_logic(**kwargs)
