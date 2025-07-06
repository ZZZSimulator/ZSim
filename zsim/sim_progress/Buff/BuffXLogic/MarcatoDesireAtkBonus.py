from .. import Buff, JudgeTools, check_preparation, find_tick


class MarcatoDesireRecord:
    def __init__(self):
        self.equipper = None
        self.char = None
        self.enemy = None


class MarcatoDesireAtkBonus(Buff.BuffLogic):
    """强音热望的复杂逻辑：连携技或强化E命中属性异常状态下敌人时触发"""

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
                "强音热望", sim_instance=self.buff_instance.sim_instance
            )
        if self.buff_0 is None:
            self.buff_0 = JudgeTools.find_exist_buff_dict(
                sim_instance=self.buff_instance.sim_instance
            )[self.equipper][self.buff_instance.ft.index]
        if self.buff_0.history.record is None:
            self.buff_0.history.record = MarcatoDesireRecord()
        self.record = self.buff_0.history.record

    def special_judge_logic(self, **kwargs):
        self.check_record_module()
        self.get_prepared(equipper="强音热望", enemy=1)
        skill_node = kwargs.get("skill_node", None)
        if skill_node is None:
            return False
        from zsim.sim_progress.Preload import SkillNode

        if not isinstance(skill_node, SkillNode):
            raise ValueError(
                f"{self.buff_instance.ft.index}的Xjudge函数获取的skill_node不是SkillNode类型！"
            )
        if skill_node.char_name != self.record.char.NAME:
            return False
        if not skill_node.is_hit_now(
            find_tick(sim_instance=self.buff_instance.sim_instance)
        ):
            return False
        if skill_node.skill.trigger_buff_level in [2, 5]:
            if self.record.enemy.dynamic.is_under_anomaly():
                return True
        return False
