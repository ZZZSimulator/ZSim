from .. import Buff, JudgeTools, check_preparation


class LinaAdditionalSkillRecord:
    def __init__(self):
        self.enemy = None


class LinaAdditionalSkillEleDMGBonus(Buff.BuffLogic):
    def __init__(self, buff_instance):
        """
        丽娜组队被动：感电增加全队电伤
        """
        super().__init__(buff_instance)
        self.buff_instance: Buff = buff_instance
        self.buff_0 = None
        self.record = None
        self.xjudge = self.special_judge_logic
        self.xexit = self.special_exit_logic

    def get_prepared(self, **kwargs):
        return check_preparation(buff_instance=self.buff_instance, buff_0=self.buff_0, **kwargs)

    def check_record_module(self):
        if self.buff_0 is None:
            self.buff_0 = JudgeTools.find_exist_buff_dict(
                sim_instance=self.buff_instance.sim_instance
            )["丽娜"][self.buff_instance.ft.index]
        if self.buff_0.history.record is None:
            self.buff_0.history.record = LinaAdditionalSkillRecord()
        self.record = self.buff_0.history.record

    def special_judge_logic(self, **kwargs):
        self.check_record_module()
        self.get_prepared(enemy=1)
        if self.record.enemy.dynamic.shock:
            return True
        else:
            return False

    def special_exit_logic(self):
        self.check_record_module()
        self.get_prepared(enemy=1)
        if not self.record.enemy.dynamic.shock:
            return True
        else:
            return False
