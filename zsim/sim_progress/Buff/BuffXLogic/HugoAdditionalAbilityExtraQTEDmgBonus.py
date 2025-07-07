from .. import Buff, JudgeTools, check_preparation


class HugoAdditionalAbilityExtraQTEDmgBonusRecord:
    def __init__(self):
        self.char = None
        self.enemy = None


class HugoAdditionalAbilityExtraQTEDmgBonus(Buff.BuffLogic):
    def __init__(self, buff_instance):
        """雨果组队被动，连携技对普通敌人增伤"""
        super().__init__(buff_instance)
        self.buff_instance: Buff = buff_instance
        self.buff_0: Buff | None = None
        self.record = None
        self.xjudge = self.special_judge_logic

    def get_prepared(self, **kwargs):
        return check_preparation(
            buff_instance=self.buff_instance, buff_0=self.buff_0, **kwargs
        )

    def check_record_module(self):
        if self.buff_0 is None:
            self.buff_0 = JudgeTools.find_exist_buff_dict(
                sim_instance=self.buff_instance.sim_instance
            )["雨果"][self.buff_instance.ft.index]
        if self.buff_0.history.record is None:
            self.buff_0.history.record = HugoAdditionalAbilityExtraQTEDmgBonusRecord()
        self.record = self.buff_0.history.record

    def special_judge_logic(self, **kwargs):
        """连携技对普通敌人增伤"""
        self.check_record_module()
        self.get_prepared(char_CID=1291, enemy=1)
        skill_node = kwargs.get("skill_node", None)
        if skill_node is None:
            return False
        from zsim.sim_progress.Preload import SkillNode

        if not isinstance(skill_node, SkillNode):
            raise TypeError(
                f"{self.buff_instance.ft.index}的xjudge函数获取到的skill_node不是SkillNode类型"
            )

        """过滤不是自己的技能"""
        if "1291" not in skill_node.skill_tag:
            return False

        """过滤不是连携技的技能"""
        if skill_node.skill.trigger_buff_level != 5:
            return False

        """普通敌人的筛选是通过可连携次数来判断的"""
        if self.record.enemy.QTE_triggerable_times <= 1:
            return True
        return False
