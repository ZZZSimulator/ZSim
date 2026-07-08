from typing import TYPE_CHECKING

from zsim.define import YIXUAN_REPORT

from .. import Buff, check_preparation
from ..JudgeTools import build_preparation_context_from_buff
from ._preparation_helpers import ensure_owner_template_record, prepare_with_context
from .enemy_state_read import read_enemy_stun_active

if TYPE_CHECKING:
    from zsim.sim_progress.Preload import SkillNode


class YixuanAdditionalAbilityDmgBonusRecord:
    def __init__(self):
        self.char = None
        self.trigger_buff_0 = None


class YixuanAdditionalAbilityDmgBonus(Buff.BuffLogic):
    """仪玄组队被动的增伤效果：触发条件是：凝云术和墨烬影消命中失衡状态下的敌人时触发。"""

    def __init__(self, buff_instance):
        super().__init__(buff_instance)
        self.buff_instance: Buff = buff_instance
        self.xjudge = self.special_judge_logic
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
        ensure_owner_template_record(
            self,
            owner_name="仪玄",
            record_factory=YixuanAdditionalAbilityDmgBonusRecord,
            context_builder=build_preparation_context_from_buff,
        )

    def special_judge_logic(self, **kwargs):
        self.check_record_module()
        self.get_prepared(char_CID=1371)
        skill_node: "SkillNode | None" = kwargs.get("skill_node", None)
        if skill_node is None:
            return False
        enemy = self.buff_instance.sim_instance.schedule_data.enemy
        if not read_enemy_stun_active(enemy):
            return False
        if "1371_E_EX_B_" not in skill_node.skill_tag:
            return False
        if skill_node.preload_tick == self.buff_instance.sim_instance.tick:
            if YIXUAN_REPORT:
                self.buff_instance.sim_instance.schedule_data.change_process_state()
                print(
                    f"仪玄的{skill_node.skill.skill_text}命中了失衡状态下的敌人，触发了组队被动的增伤效果！"
                )
        return True
