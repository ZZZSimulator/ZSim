from .. import Buff, JudgeTools, check_preparation


class YanagiCinema6EXDmgBonusRecord:
    def __init__(self):
        self.char = None


class YanagiCinema6EXDmgBonus(Buff.BuffLogic):
    """
    柳的6画，森罗万象激活时，通过判定。
    """

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
            self.buff_0.history.record = YanagiCinema6EXDmgBonusRecord()
        self.record = self.buff_0.history.record

    def special_judge_logic(self, **kwargs):
        """检测当前的森罗万象状态是否开启，若开启则通过判定。"""
        self.check_record_module()
        self.get_prepared(char_CID=1221)
        if self.record.char.get_special_stats()["森罗万象状态"]:
            return True
        else:
            return False

    def special_exit_logic(self, **kwargs):
        return not self.special_judge_logic(**kwargs)
