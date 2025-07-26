from .. import Buff, JudgeTools, check_preparation


class BranchBladeSongCritRateBonusRecord:
    def __init__(self):
        self.enemy = None
        self.equipper = None
        self.main_module = None
        self.char = None
        self.last_tick_freez_statement = 0, False


class BranchBladeSongCritRateBonus(Buff.BuffLogic):
    def __init__(self, buff_instance):
        """
        该buff是新冰4的第二特效，需要检测冻结和碎冰效果。
        也就是enemy.dynamic.frozen的状态，只要发生改变，就可以触发。

        """
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
                "折枝剑歌", sim_instance=self.buff_instance.sim_instance
            )
        if self.buff_0 is None:
            self.buff_0 = JudgeTools.find_exist_buff_dict(
                sim_instance=self.buff_instance.sim_instance
            )[self.equipper][self.buff_instance.ft.index]
        if self.buff_0.history.record is None:
            self.buff_0.history.record = BranchBladeSongCritRateBonusRecord()
        self.record = self.buff_0.history.record

    def special_judge_logic(self, **kwargs):
        self.check_record_module()
        self.get_prepared(equipper="折枝剑歌", enemy=1)
        tick = JudgeTools.find_tick(sim_instance=self.buff_instance.sim_instance)
        if self.record.enemy.dynamic.frozen is None:
            this_tick_freez_statement = False
        else:
            this_tick_freez_statement = self.record.enemy.dynamic.frozen
        if this_tick_freez_statement != self.record.last_tick_freez_statement[1]:
            self.record.last_tick_freez_statement = tick, this_tick_freez_statement
            return True
        else:
            self.record.last_tick_freez_statement = tick, this_tick_freez_statement
            return False
