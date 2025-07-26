from .. import Buff, JudgeTools, check_preparation


class ElectroLipGlossAtkAndDmgBonusRecord:
    def __init__(self):
        self.equipper = None
        self.char = None
        self.enemy = None


class ElectroLipGlossAtkAndDmgBonus(Buff.BuffLogic):
    """触电唇彩判定逻辑"""

    def __init__(self, buff_instance):
        super().__init__(buff_instance)
        self.buff_instance: Buff = buff_instance
        self.xjudge = self.special_judge_logic
        self.xexit = self.special_exit_logic
        self.equipper = None
        self.buff_0 = None
        self.record = None

    def get_prepared(self, **kwargs):
        return check_preparation(buff_instance=self.buff_instance, buff_0=self.buff_0, **kwargs)

    def check_record_module(self):
        if self.equipper is None:
            self.equipper = JudgeTools.find_equipper(
                "触电唇彩", sim_instance=self.buff_instance.sim_instance
            )
        if self.buff_0 is None:
            self.buff_0 = JudgeTools.find_exist_buff_dict(
                sim_instance=self.buff_instance.sim_instance
            )[self.equipper][self.buff_instance.ft.index]
        if self.buff_0.history.record is None:
            self.buff_0.history.record = ElectroLipGlossAtkAndDmgBonusRecord()
        self.record = self.buff_0.history.record

    def special_judge_logic(self, **kwargs):
        """检测到目标处于异常状态就放行。"""
        self.check_record_module()
        self.get_prepared(equipper="触电唇彩", enemy=1)
        if self.record.enemy.dynamic.is_under_anomaly():
            return True
        else:
            return False

    def special_exit_logic(self, **kwargs):
        return not self.special_judge_logic()
