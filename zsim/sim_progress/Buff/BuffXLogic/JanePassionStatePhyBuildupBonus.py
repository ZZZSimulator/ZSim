from .. import Buff, JudgeTools, check_preparation


class JanePassionStatePhyBuildupBonusRecord:
    def __init__(self):
        self.char = None
        self.trigger_buff_0 = None


class JanePassionStatePhyBuildupBonus(Buff.BuffLogic):
    def __init__(self, buff_instance):
        """狂热状态下的积蓄效率的判定逻辑"""
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
            )["简"][self.buff_instance.ft.index]
        if self.buff_0.history.record is None:
            self.buff_0.history.record = JanePassionStatePhyBuildupBonusRecord()
        self.record = self.buff_0.history.record

    def special_judge_logic(self, **kwargs):
        """积蓄效率Buff的判定和触发器有关，其状态和触发器相同"""
        self.check_record_module()
        self.get_prepared(char_CID=1301, trigger_buff_0=("简", "Buff-角色-简-狂热状态触发器"))
        if self.record.trigger_buff_0.dy.active:
            return True
        else:
            return False

    def special_exit_logic(self, **kwargs):
        """积蓄效率的退出逻辑与触发器相反"""
        return not self.special_judge_logic()
