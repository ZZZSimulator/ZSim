from .. import Buff, check_preparation
from ..JudgeTools import build_preparation_context_from_buff
from ._preparation_helpers import ensure_equipper_template_record, prepare_with_context


class SpectralGazeDefReduceRecord:
    def __init__(self):
        self.equipper = None
        self.char = None


class SpectralGazeDefReduce(Buff.BuffLogic):
    """扳机专武索魂影眸的减防效果判定"""

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
            item_name="索魂影眸",
            record_factory=SpectralGazeDefReduceRecord,
            context_builder=build_preparation_context_from_buff,
        )

    def special_judge_logic(self, **kwargs):
        """装备者的[追加攻击]命中敌人并造成电属性伤害时触发"""
        self.check_record_module()
        self.get_prepared(equipper="索魂影眸")
        skill_node = kwargs.get("skill_node", None)
        if skill_node is None:
            raise ValueError(f"{self.buff_instance.ft.index}的xjudge中缺少skill_node参数")
        from zsim.sim_progress.Preload import SkillNode

        if not isinstance(skill_node, SkillNode):
            raise TypeError
        if str(self.record.char.CID) not in skill_node.skill_tag or not skill_node.skill.labels:
            return False
        if skill_node.element_type == 3 and "aftershock_attack" in skill_node.skill.labels:
            return True
        return False
