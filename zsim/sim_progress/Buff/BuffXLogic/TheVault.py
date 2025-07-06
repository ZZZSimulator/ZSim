from .. import Buff, JudgeTools, check_preparation


class TheVaultRecord:
    def __init__(self):
        self.equipper = None
        self.char = None
        self.action_stack = None


def is_hit(action_now):
    """
    检测当前tick是否有hit事件。
    """
    mission_dict = action_now.mission_dict
    tick_now = JudgeTools.find_tick(sim_instance=self.buff_instance.sim_instance)
    for sub_mission_start_tick in mission_dict.keys():
        if tick_now - 1 < sub_mission_start_tick <= tick_now:
            if mission_dict[sub_mission_start_tick] == "hit":
                return True
    else:
        return False


class TheVault(Buff.BuffLogic):
    """
    聚宝箱的复杂逻辑模块，回能和增伤的判定逻辑都是一样的，
    所以它们共用这一个逻辑模块。
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
                "聚宝箱", sim_instance=self.buff_instance.sim_instance
            )
        if self.buff_0 is None:
            """
            这里的初始化，找到的buff_0实际上是佩戴者的buff_0
            """
            self.buff_0 = JudgeTools.find_exist_buff_dict(
                sim_instance=self.buff_instance.sim_instance
            )[self.equipper][self.buff_instance.ft.index]
        if self.buff_0.history.record is None:
            self.buff_0.history.record = TheVaultRecord()
        self.record = self.buff_0.history.record

    def special_judge_logic(self, **kwargs):
        """
        由于聚宝箱的buff是命中判定，且后台生效，但是只能自己触发。
        所以首先需要判定的是当前tick是否有hit事件。
        """
        self.check_record_module()
        self.get_prepared(equipper="聚宝箱", action_stack=1)
        action_now = self.record.action_stack.peek()
        if not is_hit(action_now):
            return False
        if action_now.mission_character != self.record.equipper:
            return False
        if (
            action_now.mission_node.skill.trigger_buff_level not in [2, 5, 6]
            and action_now.mission_node.skill.element_type != 4
        ):
            return False
        return True
