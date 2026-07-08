from .. import Buff, check_preparation, find_tick
from ..JudgeTools import build_preparation_context_from_buff
from ._preparation_helpers import ensure_equipper_template_record, prepare_with_context


class FlightOfFancyRecord:
    def __init__(self):
        self.equipper = None
        self.char = None


class FlightOfFancy(Buff.BuffLogic):
    """飞鸟星梦的复杂逻辑，监测到装备者造成以太伤害时叠层。"""

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
            item_name="飞鸟星梦",
            record_factory=FlightOfFancyRecord,
            context_builder=build_preparation_context_from_buff,
        )

    def special_judge_logic(self, **kwargs):
        """检测到装备者的以太伤害技能，并且处于Hit节点。"""
        self.check_record_module()
        self.get_prepared(equipper="飞鸟星梦")
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
        # 滤去非以太伤害的技能
        if skill_node.element_type != 4:
            return False
        tick = find_tick(sim_instance=self.buff_instance.sim_instance)
        if skill_node.loading_mission.is_hit_now(tick):
            return True
        return False
