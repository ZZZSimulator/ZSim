from .. import Buff, JudgeTools, check_preparation


class JanePassionStateTriggerRecord:
    def __init__(self):
        self.char = None


class JanePassionStateTrigger(Buff.BuffLogic):
    def __init__(self, buff_instance):
        """简单的狂热状态触发器"""
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
            )["简"][self.buff_instance.ft.index]
        if self.buff_0.history.record is None:
            self.buff_0.history.record = JanePassionStateTriggerRecord()
        self.record = self.buff_0.history.record

    def special_judge_logic(self, **kwargs):
        """简的狂热状态触发器，其取值狂热状态同步"""
        self.check_record_module()
        self.get_prepared(char_CID=1261)
        passion_state = self.record.char.get_special_stats().get("狂热状态")
        if passion_state is None:
            raise ValueError(
                f"{self.buff_instance.ft.index} 的xjudge模块并未获取到简的狂热状态！"
            )
        if passion_state:
            return True
        else:
            return False

    def special_exit_logic(self, **kwargs):
        """简的狂热状态触发器的退出逻辑，和触发函数持相反逻辑"""
        return not self.special_judge_logic()
