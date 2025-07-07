from .. import Buff, JudgeTools, check_preparation


class SharpenedStingerAnomalyBuildupBonusRecord:
    def __init__(self):
        self.equipper = None
        self.char = None
        self.update_signal = None
        self.preload_data = None
        self.sub_exist_buff_dict = None
        self.trigger_buff_0 = None


class SharpenedStingerAnomalyBuildupBonus(Buff.BuffLogic):
    """淬锋钳刺第二个特效的判断逻辑"""

    def __init__(self, buff_instance):
        super().__init__(buff_instance)
        self.buff_instance: Buff = buff_instance
        self.xjudge = self.special_judge_logic
        self.xexit = self.special_exit_logic
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
                "淬锋钳刺", sim_instance=self.buff_instance.sim_instance
            )
        if self.buff_0 is None:
            self.buff_0 = JudgeTools.find_exist_buff_dict(
                sim_instance=self.buff_instance.sim_instance
            )[self.equipper][self.buff_instance.ft.index]
        if self.buff_0.history.record is None:
            self.buff_0.history.record = SharpenedStingerAnomalyBuildupBonusRecord()
        self.record = self.buff_0.history.record

    def special_judge_logic(self, **kwargs):
        """淬锋钳刺的第二特效触发逻辑：触发器Buff为3层时触发。"""
        self.check_record_module()
        self.get_prepared(
            equipper="淬锋钳刺",
            preload_data=1,
            trigger_buff_0=("equipper", "淬锋钳刺-猎意"),
        )
        if self.record.trigger_buff_0.dy.count == 3:
            return True
        else:
            return False

    def special_exit_logic(self, **kwargs):
        return not self.special_judge_logic(**kwargs)
