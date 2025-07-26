from .. import Buff, JudgeTools, check_preparation


class VVivianCinema1DebuffRecord:
    def __init__(self):
        self.char = None
        self.enemy = None


class VivianCinema1Debuff(Buff.BuffLogic):
    def __init__(self, buff_instance):
        """薇薇安1画的负面效果判定逻辑"""
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
            )["薇薇安"][self.buff_instance.ft.index]
        if self.buff_0.history.record is None:
            self.buff_0.history.record = VVivianCinema1DebuffRecord()
        self.record = self.buff_0.history.record

    def special_judge_logic(self, **kwargs):
        """检测到敌人身上有薇薇安的预言Dot就放行"""
        self.check_record_module()
        self.get_prepared(char_CID=1331, enemy=1)
        if self.record.enemy.find_dot("ViviansProphecy"):
            return True
        else:
            return False
