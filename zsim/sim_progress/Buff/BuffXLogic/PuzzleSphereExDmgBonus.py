from typing import TYPE_CHECKING

from .. import Buff, check_preparation
from ..JudgeTools import build_preparation_context_from_buff
from ._preparation_helpers import ensure_equipper_template_record, prepare_with_context

if TYPE_CHECKING:
    from zsim.sim_progress.Preload import SkillNode


class PuzzleSphereExDmgBonusRecord:
    def __init__(self):
        self.equipper = None
        self.char = None
        self.enemy = None


class PuzzleSphereExDmgBonus(Buff.BuffLogic):
    def __init__(self, buff_instance):
        super().__init__(buff_instance)
        self.buff_instance: Buff = buff_instance
        self.xjudge = self.special_judge_logic
        self.equipper = None
        self.buff_0 = None
        self.record = None

    def get_prepared(self, **kwargs):
        return prepare_with_context(
            self,
            check_preparation_func=check_preparation,
            context_builder=build_preparation_context_from_buff,
            **kwargs,
        )

    def check_record_module(self):
        ensure_equipper_template_record(
            self,
            item_name="幻变魔方",
            record_factory=PuzzleSphereExDmgBonusRecord,
            context_builder=build_preparation_context_from_buff,
        )

    def special_judge_logic(self, **kwargs):
        """幻变魔方的特殊判定逻辑，强化E发动时，若敌人的血量高于50%，则放行。"""
        self.check_record_module()
        self.get_prepared(equipper="幻变魔方", enemy=1)
        skill_node: "SkillNode | None" = kwargs.get("skill_node", None)
        if skill_node is None:
            return False
        if skill_node.char_name != self.record.char.NAME:
            return False
        if skill_node.skill.trigger_buff_level != 2:
            return False
        if self.record.enemy.get_current_hp_percentage() < 0.5:
            return False
        return True
