from .. import Buff, JudgeTools


class PreciousFossilizedCoreStunBonusOver75Hp(Buff.BuffLogic):
    """
    这段代码是贵重骨核的复杂判断逻辑，
    敌人生命值大于等于75%时返回True
    """

    def __init__(self, buff_instance):
        super().__init__(buff_instance)
        self.buff_instance: Buff = buff_instance
        # 初始化特定逻辑
        self.xjudge = self.special_judge_logic

    def special_judge_logic(self, **kwargs):
        enemy = JudgeTools.find_enemy(sim_instance=self.buff_instance.sim_instance)
        hp_pct = enemy.get_total_hp_percentage()
        if hp_pct >= 0.75:
            return True
        else:
            return False
