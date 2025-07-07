from .. import Buff, JudgeTools, check_preparation


class SpectralGazeImpactBonusRecord:
    def __init__(self):
        self.equipper = None
        self.char = None
        self.trigger_buff_0 = None


class SpectralGazeImpactBonus(Buff.BuffLogic):
    """扳机专武索魂影眸的第3特效——魂锁满层时，获得冲击力增幅，"""

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
                "索魂影眸", sim_instance=self.buff_instance.sim_instance
            )
        if self.buff_0 is None:
            """
            这里的初始化，找到的buff_0实际上是佩戴者的buff_0
            """
            self.buff_0 = JudgeTools.find_exist_buff_dict(
                sim_instance=self.buff_instance.sim_instance
            )[self.equipper][self.buff_instance.ft.index]
        if self.buff_0.history.record is None:
            self.buff_0.history.record = SpectralGazeImpactBonusRecord()
        self.record = self.buff_0.history.record

    def special_judge_logic(self, **kwargs):
        """检查触发器buff是否是3层"""
        self.check_record_module()
        self.get_prepared(
            equipper="索魂影眸", trigger_buff_0=("equipper", "索魂影眸-魂锁")
        )
        if self.record.trigger_buff_0.dy.active:
            if self.record.trigger_buff_0.dy.count == 3:
                return True
        return False

    def special_exit_logic(self, **kwargs):
        if not self.xjudge:
            return True
        return False
