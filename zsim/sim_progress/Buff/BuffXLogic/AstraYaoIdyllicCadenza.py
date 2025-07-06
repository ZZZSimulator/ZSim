from .. import Buff, JudgeTools, check_preparation


class AstraYaoIdyllicCadenzaRecord:
    def __init__(self):
        self.char = None


class AstraYaoIdyllicCadenza(Buff.BuffLogic):
    def __init__(self, buff_instance):
        """耀嘉音咏叹华彩的加成效果的判定逻辑"""
        super().__init__(buff_instance)
        self.buff_instance: Buff = buff_instance
        self.buff_0 = None
        self.record = None
        self.xjudge = self.special_judge_logic
        self.xexit = self.special_exit_logic

    def get_prepared(self, **kwargs):
        return check_preparation(
            buff_instance=self.buff_instance, buff_0=self.buff_0, **kwargs
        )

    def check_record_module(self):
        if self.buff_0 is None:
            self.buff_0 = JudgeTools.find_exist_buff_dict(
                sim_instance=self.buff_instance.sim_instance
            )["耀嘉音"][self.buff_instance.ft.index]
        if self.buff_0.history.record is None:
            self.buff_0.history.record = AstraYaoIdyllicCadenzaRecord()
        self.record = self.buff_0.history.record

    def special_judge_logic(self, **kwargs):
        """检测咏叹华彩状态"""
        self.check_record_module()
        self.get_prepared(char_CID=1311)
        if self.record.char.get_resources()[1]:
            return True
        else:
            return False

    def special_exit_logic(self, **kwargs):
        return not self.special_judge_logic(**kwargs)
