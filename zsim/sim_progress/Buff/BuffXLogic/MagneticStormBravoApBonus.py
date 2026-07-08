from .. import Buff, check_preparation
from ..JudgeTools import build_preparation_context_from_buff
from ._preparation_helpers import ensure_equipper_template_record, prepare_with_context


class MagneticStormBravoApBonusRecord:
    def __init__(self):
        self.equipper = None
        self.char = None
        self.sub_exist_buff_dict = None


class MagneticStormBravoApBonus(Buff.BuffLogic):
    """电磁暴2式判定逻辑"""

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
            item_name="「电磁暴」-贰式",
            record_factory=MagneticStormBravoApBonusRecord,
            context_builder=build_preparation_context_from_buff,
        )

    def special_judge_logic(self, **kwargs):
        """只要造成了积蓄值，就放行"""
        self.check_record_module()
        self.get_prepared(equipper="「电磁暴」-贰式")
        skill_node = kwargs.get("skill_node", None)
        if skill_node is None:
            return False
        from zsim.sim_progress.Load import LoadingMission
        from zsim.sim_progress.Preload import SkillNode

        if isinstance(skill_node, SkillNode):
            pass
        elif isinstance(skill_node, LoadingMission):
            skill_node = skill_node.mission_node
        else:
            return False
        # 滤去不是自己的技能
        if self.record.equipper != skill_node.char_name:
            return False

        if (
            skill_node.skill.anomaly_accumulation != 0
            and skill_node.skill.element_damage_percent > 0
        ):
            return True
        return False
