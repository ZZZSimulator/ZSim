from .. import Buff, JudgeTools, check_preparation


class Soldier0AnbyCinema4EleResReduceRecord:
    def __init__(self):
        self.char = None
        self.trigger_buff_0 = None


class Soldier0AnbyCinema4EleResReduce(Buff.BuffLogic):
    def __init__(self, buff_instance):
        """
        零号·安比的组队被动，操作角色为安比，并且目标有银星时候，全队增伤。
        """
        super().__init__(buff_instance)
        self.buff_instance: Buff = buff_instance
        self.buff_0 = None
        self.record = None
        self.xjudge = self.special_judge_logic

    def get_prepared(self, **kwargs):
        return check_preparation(buff_instance=self.buff_instance, buff_0=self.buff_0, **kwargs)

    def check_record_module(self):
        if self.buff_0 is None:
            self.buff_0 = JudgeTools.find_exist_buff_dict(
                sim_instance=self.buff_instance.sim_instance
            )["零号·安比"][self.buff_instance.ft.index]
        if self.buff_0.history.record is None:
            self.buff_0.history.record = Soldier0AnbyCinema4EleResReduceRecord()
        self.record = self.buff_0.history.record

    def special_judge_logic(self, **kwargs):
        """
        只要是检测到有银星，就返回True
        """
        self.check_record_module()
        self.get_prepared(
            char_CID=1381,
            trigger_buff_0=("零号·安比", "Buff-角色-零号·安比-银星触发器"),
        )
        if self.record.trigger_buff_0.dy.active:
            return True
        return False
