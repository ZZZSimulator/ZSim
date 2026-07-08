from .. import Buff, check_preparation
from ..JudgeTools import build_preparation_context_from_buff
from ._preparation_helpers import ensure_owner_template_record, prepare_with_context


class TriggerCoreSkillStunDMGBonusRecord:
    def __init__(self):
        self.char = None


class TriggerCoreSkillStunDMGBonus(Buff.BuffLogic):
    def __init__(self, buff_instance):
        """
        扳机的核心被动，扳机发动的追加攻击能增加失衡易伤
        """
        super().__init__(buff_instance)
        self.buff_instance: Buff = buff_instance
        self.buff_0 = None
        self.record = None
        self.xjudge = self.special_judge_logic

    def get_prepared(self, **kwargs):
        return prepare_with_context(
            self,
            check_preparation_func=check_preparation,
            context_builder=build_preparation_context_from_buff,
            **kwargs,
        )

    def check_record_module(self):
        ensure_owner_template_record(
            self,
            owner_name="扳机",
            record_factory=TriggerCoreSkillStunDMGBonusRecord,
            context_builder=build_preparation_context_from_buff,
        )

    def special_judge_logic(self, **kwargs):
        """只要是检测到扳机释放的协同攻击，就返回True"""
        self.check_record_module()
        self.get_prepared(char_CID=1361)
        from zsim.sim_progress.Preload import SkillNode

        skill_node: SkillNode | None
        skill_node = kwargs.get("skill_node", None)
        if skill_node is None:
            raise ValueError(f"{self.buff_instance.ft.index}的xjudge并未成功获取到skill_node！")
        if "1361" not in skill_node.skill_tag or not skill_node.skill.labels:
            return False
        if "aftershock_attack" in skill_node.skill.labels.keys():
            return True
        return False
