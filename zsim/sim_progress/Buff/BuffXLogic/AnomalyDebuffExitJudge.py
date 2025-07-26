from .. import Buff, JudgeTools


anomaly_statement_dict = {
    "Buff-异常-霜寒": "frostbite",
    "Buff-异常-畏缩": "assault",
    "Buff-异常-烈霜霜寒": "frost_frostbite",
}


class AnomalyDebuffExitJudge(Buff.BuffLogic):
    """
    理论上所有属性异常导致的debuff都适用这退出特效。
    """

    def __init__(self, buff_instance):
        super().__init__(buff_instance)
        self.buff_instance: Buff = buff_instance
        self.xexit = self.special_exit_logic
        self.last_frostbite = False
        self.last_frost_frostbite = False
        self.last_assault = False
        self.last_shock = False
        self.last_burn = False
        self.last_corruption = False
        self.enemy = None

    def special_exit_logic(self):
        """
        特殊属性异常退出机制
        即：属性异常结束（检测到下降沿）就结束
        """
        if self.enemy is None:
            self.enemy = JudgeTools.find_enemy(sim_instance=self.buff_instance.sim_instance)
        anomaly_name = anomaly_statement_dict[self.buff_instance.ft.index]
        anomaly_now = getattr(self.enemy.dynamic, anomaly_name)
        anomaly_statement = [
            getattr(self.buff_instance.logic, f"last_{anomaly_name}"),
            anomaly_now,
        ]

        def mode_func(a, b):
            return a is True and b is False

        result = JudgeTools.detect_edge(anomaly_statement, mode_func)
        setattr(self.buff_instance.logic, f"last_{anomaly_name}", anomaly_now)
        return result
