from .. import Buff, JudgeTools, check_preparation


class TheVaultRecord:
    def __init__(self):
        self.equipper = None
        self.char = None
        self.action_stack = None


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
        return check_preparation(buff_instance=self.buff_instance, buff_0=self.buff_0, **kwargs)

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
        聚宝箱的触发条件：自己的技能、技能命中帧、[强化E、大招、连携技]
        """
        self.check_record_module()
        self.get_prepared(equipper="聚宝箱", action_stack=1)
        from zsim.sim_progress.Preload import SkillNode

        skill_node: SkillNode | None = kwargs.get("skill_node", None)
        if skill_node is None:
            return False
        if skill_node.char_name != self.record.char.NAME:
            return False
        if skill_node.skill.trigger_buff_level not in [2, 5, 6]:
            return False
        tick = self.buff_instance.sim_instance.tick
        if skill_node.is_hit_now(tick):
            return True
        return False
