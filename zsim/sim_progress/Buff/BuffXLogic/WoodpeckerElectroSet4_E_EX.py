from zsim.sim_progress.calculation.calculator import (
    create_calculator_runtime_read_context_from_sim_instance,
    get_calculator_buff_attribute_reader_service,
)
from zsim.sim_progress.RandomNumberGenerator import RNG

from .. import Buff, check_preparation
from ..JudgeTools import build_preparation_context_from_buff
from ._preparation_helpers import ensure_equipper_template_record, prepare_with_context


class WoodpeckerElectroEXRecord:
    def __init__(self):
        self.equipper = None
        self.char = None
        self.dynamic_buff_list = None
        self.enemy = None
        self.action_stack = None


class WoodpeckerElectroSet4_E_EX(Buff.BuffLogic):
    def __init__(self, buff_instance):
        super().__init__(buff_instance)
        self.buff_instance: Buff = buff_instance
        # 初始化特定逻辑
        self.xjudge = self.special_judge_logic
        self.buff_0 = None
        self.record = None
        self.equipper = None

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
            item_name="啄木鸟电音",
            record_factory=WoodpeckerElectroEXRecord,
            context_builder=build_preparation_context_from_buff,
        )

    def special_judge_logic(self, **kwargs):
        self.check_record_module()
        self.get_prepared(equipper="啄木鸟电音", enemy=1, action_stack=1)
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
        if str(self.record.char.CID) not in skill_node.skill_tag:
            return False
        context = create_calculator_runtime_read_context_from_sim_instance(
            sim_instance=self.buff_instance.sim_instance,
            enemy=self.record.enemy,
            character=self.record.char,
        )
        if skill_node.skill.trigger_buff_level == 2:
            reader_service = get_calculator_buff_attribute_reader_service()
            cric_rate = reader_service.read_full_crit_rate(context)
            rng: RNG = self.buff_instance.sim_instance.rng_instance
            normalized_value = rng.random_float()
            if normalized_value <= cric_rate:
                return True
            else:
                return False
        else:
            return False
