from .. import Buff, JudgeTools, check_preparation


class FreedomBluesRecord:
    def __init__(self):
        self.equipper = None
        self.char = None
        self.action_stack = None


class FreedomBlues(Buff.BuffLogic):
    """
    这是自由蓝调的复杂判定逻辑。
    自由蓝调被分为6个buff，但是共用这一个逻辑模块。
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
                "自由蓝调", sim_instance=self.buff_instance.sim_instance
            )
        if self.buff_0 is None:
            self.buff_0 = JudgeTools.find_exist_buff_dict(
                sim_instance=self.buff_instance.sim_instance
            )[self.equipper][self.buff_instance.ft.index]
        if self.buff_0.history.record is None:
            self.buff_0.history.record = FreedomBluesRecord()
        self.record = self.buff_0.history.record

    def special_judge_logic(self, **kwargs):
        """
        只有装备者位于前台，并且当前的动作是强化E才会进入下一轮判断
        只有当强化E 属性与buff自身的refinement想同，才会输出True。
        这里，refinement被借用来记录buff对应的属性种类。
        """
        self.check_record_module()
        self.get_prepared(equipper="自由蓝调", action_stack=1)
        action_now = self.record.action_stack.peek()
        element_type_trigger = self.buff_instance.ft.refinement
        if (
            str(self.record.char.CID) in action_now.mission_tag
            and action_now.mission_node.skill.trigger_buff_level == 2
        ):
            if action_now.mission_node.skill.element_type == element_type_trigger:
                return True
        return False
