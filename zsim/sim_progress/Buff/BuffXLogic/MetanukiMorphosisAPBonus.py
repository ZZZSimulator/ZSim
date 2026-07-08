from typing import TYPE_CHECKING

from .. import Buff, check_preparation
from ..JudgeTools import build_preparation_context_from_buff
from ._preparation_helpers import ensure_equipper_template_record, prepare_with_context

if TYPE_CHECKING:
    from zsim.sim_progress.Preload import SkillNode


class MetanukiMorphosisAPBonusRecord:
    def __init__(self):
        self.equipper = None
        self.char = None


class MetanukiMorphosisAPBonus(Buff.BuffLogic):
    def __init__(self, buff_instance):
        super().__init__(buff_instance)
        self.buff_instance: Buff = buff_instance
        self.xjudge = self.special_judge_logic
        self.equipper = None
        self.buff_0 = None
        self.record: MetanukiMorphosisAPBonusRecord | None = None

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
            item_name="狸法七变化",
            record_factory=MetanukiMorphosisAPBonusRecord,
            context_builder=build_preparation_context_from_buff,
        )

    def special_judge_logic(self, **kwargs):
        """检测到装备者的追加攻击时放行，但是需要注意此效果只能生效一个"""
        self.check_record_module()
        self.get_prepared(equipper="狸法七变化")
        skill_node: "SkillNode" = kwargs.get("skill_node")
        if skill_node is None:
            return False
        if skill_node.char_name != self.record.char.NAME:
            return False
        if not skill_node.have_label(label_key="aftershock_attack"):
            return False
        if skill_node.is_hit_now(tick=self.buff_instance.sim_instance.tick):
            return True
        else:
            return False
