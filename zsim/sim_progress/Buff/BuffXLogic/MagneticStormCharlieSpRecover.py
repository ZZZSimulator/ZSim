from typing import Any

from zsim.sim_progress.data_struct.schedule_dispatch import (
    ScheduledEventEmitterProvider,
)

from .. import Buff, JudgeTools, check_preparation
from ..JudgeTools.PreparationContext import (
    ResourceRefreshCommandPort,
    build_preparation_context_from_buff,
)
from ._preparation_helpers import ensure_equipper_template_record, prepare_with_context


class MagneticStormCharlieSpRecoverRecord:
    def __init__(self):
        self.equipper = None
        self.char = None
        self.sub_exist_buff_dict = None
        self.energy_value_dict = {1: 3.5, 2: 4, 3: 4.5, 4: 5, 5: 5.5}


class MagneticStormCharlieSpRecover(Buff.BuffLogic):
    """电磁暴3式判定逻辑"""

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

    def _emit_scheduled_refresh(
        self,
        *,
        sp_target: tuple[str, ...],
        sp_value: float | int,
    ) -> None:
        refresh_commands = ResourceRefreshCommandPort(self._scheduled_event_emitter_provider)
        refresh_commands.publish_refresh(sp_target=sp_target, sp_value=sp_value)

    def check_record_module(self):
        ensure_equipper_template_record(
            self,
            item_name="「电磁暴」-叁式",
            record_factory=MagneticStormCharlieSpRecoverRecord,
            context_builder=build_preparation_context_from_buff,
        )

    def special_judge_logic(self, **kwargs):
        """只要造成了积蓄值，就放行"""
        self.check_record_module()
        self.get_prepared(equipper="「电磁暴」-叁式")
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

    def special_hit_logic(self, **kwargs):
        self.check_record_module()
        self.get_prepared(equipper="「电磁暴」-叁式", sub_exist_buff_dict=1)
        tick_now = JudgeTools.find_tick(sim_instance=self.buff_instance.sim_instance)
        self.buff_instance.simple_start(tick_now, self.record.sub_exist_buff_dict)
        energy_value = self.record.energy_value_dict[int(self.buff_instance.ft.refinement)]
        self._emit_scheduled_refresh(
            sp_target=(self.record.char.NAME,),
            sp_value=energy_value,
        )
        print("电磁暴3式回能触发！")
