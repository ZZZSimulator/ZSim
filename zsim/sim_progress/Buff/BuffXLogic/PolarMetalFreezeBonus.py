from .. import Buff, JudgeTools, check_preparation


class PolarMetalRecord:
    def __init__(self):
        self.last_tick_freez_statement = 0, False
        self.equipper = None
        self.enemy = None
        self.char = None


class PolarMetalFreezeBonus(Buff.BuffLogic):
    """
    这是极地重金属的复杂逻辑判定。
    主要检测的是碎冰的变化状态，如果碎冰状态变了，就返回True
    """

    def __init__(self, buff_instance):
        super().__init__(buff_instance)
        self.buff_instance: Buff = buff_instance
        # 初始化特定逻辑
        self.xjudge = self.special_judge_logic
        self.equipper = None
        self.buff_0 = None
        self.record = None

    def get_prepared(self, **kwargs):
        return check_preparation(buff_instance=self.buff_instance, buff_0=self.buff_0, **kwargs)

    def check_record_module(self):
        if self.equipper is None:
            self.equipper = JudgeTools.find_equipper(
                "极地重金属", sim_instance=self.buff_instance.sim_instance
            )
        if self.buff_0 is None:
            self.buff_0 = JudgeTools.find_exist_buff_dict(
                sim_instance=self.buff_instance.sim_instance
            )[self.equipper][self.buff_instance.ft.index]
        if self.buff_0.history.record is None:
            self.buff_0.history.record = PolarMetalRecord()
        self.record = self.buff_0.history.record

    def special_judge_logic(self, **kwargs):
        self.check_record_module()
        self.get_prepared(enemy=1)
        enemy = self.record.enemy
        tick = JudgeTools.find_tick(sim_instance=self.buff_instance.sim_instance)
        if enemy.dynamic.frozen is None:
            output = False
        else:
            output = enemy.dynamic.frozen
        this_tick_freez_statement = output
        if this_tick_freez_statement != self.record.last_tick_freez_statement[1]:
            self.record.last_tick_freez_statement = tick, this_tick_freez_statement
            return True
        else:
            self.record.last_tick_freez_statement = tick, this_tick_freez_statement
            return False
