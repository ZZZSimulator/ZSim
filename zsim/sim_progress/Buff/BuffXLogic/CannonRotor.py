from typing import Any

from zsim.sim_progress.calculation.calculator import (
    create_calculator_runtime_read_context_from_sim_instance,
    get_calculator_buff_attribute_reader_service,
)
from zsim.sim_progress.data_struct.schedule_dispatch import (
    ScheduledEventEmitter,
    ScheduledEventEmitterProvider,
)

from .. import Buff, check_preparation, find_tick
from ..JudgeTools import build_preparation_context_from_buff
from ._preparation_helpers import ensure_equipper_template_record, prepare_with_context


class CannonRotorRecord:
    def __init__(self):
        self.equipper = None
        self.char = None
        self.enemy = None
        self.dynamic_buff_list = None
        self.skill_tag = "CannonRotorAdditionalDamage"
        self.preload_data = None
        self.sub_exist_buff_dict = None


class CannonRotor(Buff.BuffLogic):
    def __init__(
        self,
        buff_instance,
        scheduled_event_emitter_provider: ScheduledEventEmitterProvider | None = None,
    ):
        super().__init__(buff_instance)
        self.buff_instance: Buff = buff_instance
        self._scheduled_event_emitter_provider = (
            scheduled_event_emitter_provider
            or ScheduledEventEmitterProvider.from_sim_instance_getter(
                lambda: self.buff_instance.sim_instance
            )
        )
        self.xjudge = self.special_judge_logic
        self.xhit = self.special_hit_logic
        self.equipper = None
        self.buff_0: Any = None
        self.record: Any = None

    def get_prepared(self, **kwargs):
        return prepare_with_context(
            self,
            check_preparation_func=check_preparation,
            context_builder=build_preparation_context_from_buff,
            **kwargs,
        )

    def _scheduled_event_emitter(self) -> ScheduledEventEmitter:
        return self._scheduled_event_emitter_provider.create_emitter()

    def check_record_module(self):
        ensure_equipper_template_record(
            self,
            item_name="加农转子",
            record_factory=CannonRotorRecord,
            context_builder=build_preparation_context_from_buff,
        )

    def special_judge_logic(self, **kwargs):
        self.check_record_module()
        self.get_prepared(equipper="加农转子", enemy=1, sub_exist_buff_dict=1)
        skill_node = kwargs.get("skill_node", None)
        if skill_node is None:
            return False
        from zsim.sim_progress.Preload import SkillNode

        if not isinstance(skill_node, SkillNode):
            raise ValueError(
                f"{self.buff_instance.ft.index}的Xjudge函数获取的skill_node不是SkillNode类型！"
            )
        if skill_node.char_name != self.record.char.NAME:
            return False
        if not skill_node.is_hit_now(find_tick(sim_instance=self.buff_instance.sim_instance)):
            return False

        from zsim.sim_progress.RandomNumberGenerator import RNG

        context = create_calculator_runtime_read_context_from_sim_instance(
            sim_instance=self.buff_instance.sim_instance,
            enemy=self.record.enemy,
            character=self.record.char,
        )
        rng: RNG = self.buff_instance.sim_instance.rng_instance
        normalized_value = rng.random_float()
        reader_service = get_calculator_buff_attribute_reader_service()
        cric_rate = reader_service.read_full_crit_rate(context)
        if normalized_value <= cric_rate:
            return True
        return False

    def special_hit_logic(self, **kwargs):
        self.check_record_module()
        self.get_prepared(equipper="加农转子", enemy=1, preload_data=1)
        from zsim.sim_progress.Preload.SkillsQueue import spawn_node

        whole_skill_tag = str(self.record.char.CID) + "_" + self.record.skill_tag

        node = spawn_node(
            whole_skill_tag,
            find_tick(sim_instance=self.buff_instance.sim_instance),
            self.record.preload_data.skills,
        )
        from zsim.sim_progress.Load import LoadingMission

        mission = LoadingMission(node)
        mission.mission_start(find_tick(sim_instance=self.buff_instance.sim_instance))
        node.loading_mission = mission

        self._scheduled_event_emitter().emit_scheduled(node)
        self.buff_instance.simple_start(
            find_tick(sim_instance=self.buff_instance.sim_instance),
            self.record.sub_exist_buff_dict,
        )
