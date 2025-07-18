from .. import Buff, JudgeTools, check_preparation


class MiyabiCoreSkillFB:
    def __init__(self):
        self.last_frostbite = False
        self.enemy = None


class MiyabiCoreSkill_FrostBurn(Buff.BuffLogic):
    """
    该buff是雅的核心被动中的【霜灼】，【霜灼】的进入机制是，随着烈霜属性异常触发，同步触发。
    执行这一步的是：update_anomaly函数，该函数会在烈霜属性积蓄条满的时候，
    根据bar.accompany_debuff中记录的str，去添加同名debuff。
    """

    def __init__(self, buff_instance):
        super().__init__(buff_instance)
        self.buff_instance: Buff = buff_instance
        self.xexit = self.special_exit_logic
        self.buff_0 = None
        self.record = None

    def get_prepared(self, **kwargs):
        return check_preparation(
            buff_instance=self.buff_instance, buff_0=self.buff_0, **kwargs
        )

    def check_record_module(self):
        if self.buff_0 is None:
            self.buff_0 = JudgeTools.find_exist_buff_dict(
                sim_instance=self.buff_instance.sim_instance
            )["雅"][self.buff_instance.ft.index]
        if self.buff_0.history.record is None:
            self.buff_0.history.record = MiyabiCoreSkillFB()
        self.record = self.buff_0.history.record

    def special_exit_logic(self):
        """
        霜灼buff的退出机制是检测到霜寒的下降沿就退出
        """
        self.check_record_module()
        self.get_prepared(enemy=1)
        frostbite_now = self.record.enemy.dynamic.frost_frostbite
        frostbite_statement = [self.record.last_frostbite, frostbite_now]

        def mode_func(a, b):
            return a is True and b is False

        result = JudgeTools.detect_edge(frostbite_statement, mode_func)
        self.record.last_frostbite = frostbite_now
        return result
