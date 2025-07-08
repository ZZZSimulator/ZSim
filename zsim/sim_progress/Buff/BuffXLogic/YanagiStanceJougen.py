from .. import Buff, JudgeTools, check_preparation


class YanagiStanceJougenRecord:
    def __init__(self):
        self.char = None


class YanagiStanceJougen(Buff.BuffLogic):
    """
    柳的上弦增幅，检测到上弦状态就通过判定
    """

    def __init__(self, buff_instance):
        super().__init__(buff_instance)
        self.buff_instance: Buff = buff_instance
        self.xjudge = self.special_judge_logic
        self.buff_0 = None
        self.record = None

    def get_prepared(self, **kwargs):
        return check_preparation(
            buff_instance=self.buff_instance, buff_0=self.buff_0, **kwargs
        )

    def check_record_module(self):
        if self.buff_0 is None:
            self.buff_0 = JudgeTools.find_exist_buff_dict(
                sim_instance=self.buff_instance.sim_instance
            )["柳"][self.buff_instance.ft.index]
        if self.buff_0.history.record is None:
            self.buff_0.history.record = YanagiStanceJougenRecord()
        self.record = self.buff_0.history.record

    def special_judge_logic(self, **kwargs):
        """
        检测柳的当前状态，如果当前状态为上弦就通过判定。
        """
        self.check_record_module()
        self.get_prepared(char_CID=1221)
        if self.record.char.stance_manager.stance_now:
            return True
        else:
            return False
