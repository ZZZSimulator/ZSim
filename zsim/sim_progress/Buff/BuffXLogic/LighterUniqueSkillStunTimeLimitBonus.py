from .. import Buff, JudgeTools, check_preparation


class LighterUniqueSkillStunTimeRecord:
    def __init__(self):
        self.last_stun_statement = False
        self.enemy = None


class LighterUniqueSkillStunTimeLimitBonus(Buff.BuffLogic):
    """
    该buff的退出逻辑特殊，失衡结束就会直接退出。
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
            )["莱特"][self.buff_instance.ft.index]
        if self.buff_0.history.record is None:
            self.buff_0.history.record = LighterUniqueSkillStunTimeRecord()
        self.record = self.buff_0.history.record

    def special_exit_logic(self):
        """
        获取当前失衡值，和上一次失衡值对比。
        """
        self.check_record_module()
        self.get_prepared(enemy=1)

        if self.record.last_stun_statement and not self.record.enemy.dynamic.stun:
            self.record.last_stun_statement = self.record.enemy.dynamic.stun
            return True
        else:
            self.record.last_stun_statement = self.record.enemy.dynamic.stun
            return False
