from .. import Buff, JudgeTools, check_preparation


class Slodier11AdditionalSkillRecord:
    def __init__(self):
        self.enemy = None


class Soldier11AdditionalSkillExtraFireDMGBonus(Buff.BuffLogic):
    def __init__(self, buff_instance):
        """
        11号组队被动：失衡期间额外火伤。
        """
        super().__init__(buff_instance)
        self.buff_instance: Buff = buff_instance
        self.xjudge = self.special_judge_logic
        self.buff_0 = None
        self.record = None

    def get_prepared(self, **kwargs):
        return check_preparation(buff_instance=self.buff_instance, buff_0=self.buff_0, **kwargs)

    def check_record_module(self):
        if self.buff_0 is None:
            self.buff_0 = JudgeTools.find_exist_buff_dict(
                sim_instance=self.buff_instance.sim_instance
            )["11号"][self.buff_instance.ft.index]
        if self.buff_0.history.record is None:
            self.buff_0.history.record = Slodier11AdditionalSkillRecord()
        self.record = self.buff_0.history.record

    def special_judge_logic(self, **kwargs):
        self.check_record_module()
        self.get_prepared(enemy=1)
        if self.record.enemy.dynamic.stun:
            return True
        else:
            return False
