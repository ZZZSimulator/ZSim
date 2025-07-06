from .. import Buff, JudgeTools, check_preparation


class JaneAdditionalAbilityPhyBuildupBonusRecord:
    def __init__(self):
        self.char = None
        self.trigger_buff_0 = None
        self.dynamic_buff_list = None
        self.enemy = None
        self.sub_exist_buff_dict = None


class JaneAdditionalAbilityPhyBuildupBonus(Buff.BuffLogic):
    def __init__(self, buff_instance):
        """简组队被动中第二特效的复杂逻辑"""
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
            self.buff_0.history.record = JaneAdditionalAbilityPhyBuildupBonusRecord()
        self.record = self.buff_0.history.record

    def special_judge_logic(self, **kwargs):
        """简组队被动的第二特效是：只要有敌人处于异常状态即可触发，所以只要有任意一种异常处于激活状态，就可以放行。"""
        self.check_record_module()
        self.get_prepared(char_CID=1301, enemy=1)
        return self.record.enemy.dynamic.is_under_anomaly()

    def special_exit_logic(self, **kwargs):
        """此Buff退出逻辑和触发逻辑相反"""
        return not self.special_judge_logic()
