from .. import Buff, JudgeTools, check_preparation

anomaly_name_list = ["frostbite", "assault", "shock", "burn", "corruption"]


class HailstormShrineIceBonusRecord:
    def __init__(self):
        self.anomaly_state = {name: False for name in anomaly_name_list}
        self.equipper = None
        self.action_stack = None
        self.enemy = None
        self.char = None


class HailstormShrineIceBonus(Buff.BuffLogic):
    """
    该buff为雅专武的冰伤判定模块。
    它需要检测所有的属性异常，找它们的上升沿。
    或者是当前动作的trigger_buff_level为强化特殊技
    """

    def __init__(self, buff_instance):
        super().__init__(buff_instance)
        self.buff_instance: Buff = buff_instance
        self.xjudge = self.special_judge_logic
        self.equipper = None
        self.buff_0 = None
        self.record = None

    def get_prepared(self, **kwargs):
        return check_preparation(
            buff_instance=self.buff_instance, buff_0=self.buff_0, **kwargs
        )

    def check_record_module(self):
        if self.equipper is None:
            self.equipper = JudgeTools.find_equipper(
                "霰落星殿", sim_instance=self.buff_instance.sim_instance
            )
        if self.buff_0 is None:
            self.buff_0 = JudgeTools.find_exist_buff_dict(
                sim_instance=self.buff_instance.sim_instance
            )[self.equipper][self.buff_instance.ft.index]
        if self.buff_0.history.record is None:
            self.buff_0.history.record = HailstormShrineIceBonusRecord()
        self.record = self.buff_0.history.record

    def special_judge_logic(self, **kwargs):
        self.check_record_module()
        self.get_prepared(equipper="霰落星殿", enemy=1, action_stack=1)
        action_now = self.record.action_stack.peek()
        current_anomalies = {
            name: getattr(self.record.enemy.dynamic, name) for name in anomaly_name_list
        }
        # 判断总异常数量是否 >= 2
        if (
            sum(current_anomalies.values()) >= 2
            or sum(self.record.anomaly_state.values()) >= 2
        ):
            raise ValueError("当前ticks总异常数量为2！")
        # 检查是否有状态变化或满足特殊技触发条件
        has_change = any(
            current_anomalies[name] != self.record.anomaly_state[name]
            for name in anomaly_name_list
        )
        if has_change or (
            action_now.mission_node.skill.trigger_buff_level == 2
            and str(self.record.char.CID) in action_now.mission_tag
        ):
            self.record.anomaly_state.update(current_anomalies)
            return True
        # 更新状态并返回
        self.record.anomaly_state.update(current_anomalies)
        return False
