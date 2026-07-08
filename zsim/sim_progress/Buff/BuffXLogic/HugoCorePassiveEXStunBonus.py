from .. import Buff, check_preparation
from ..JudgeTools import build_preparation_context_from_buff
from ._preparation_helpers import ensure_owner_template_record, prepare_with_context
from .enemy_state_read import EnemyStateReadPort


class HugoCorePassiveEXStunBonusRecord:
    def __init__(self):
        self.char = None
        self.enemy = None


class HugoCorePassiveEXStunBonus(Buff.BuffLogic):
    def __init__(self, buff_instance):
        """雨果核心被动，E对非失衡状态的敌人造成的失衡值提升"""
        super().__init__(buff_instance)
        self.buff_instance: Buff = buff_instance
        self.buff_0: Buff | None = None
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
            owner_name="雨果",
            record_factory=HugoCorePassiveEXStunBonusRecord,
            context_builder=build_preparation_context_from_buff,
        )

    def special_judge_logic(self, **kwargs):
        """强化E命中非失衡状态的敌人时触发"""
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

        """过滤不是强化E的技能"""
        if skill_node.skill.trigger_buff_level != 2:
            return False

        if EnemyStateReadPort(self.record.enemy).stun_active():
            return False
        return True
