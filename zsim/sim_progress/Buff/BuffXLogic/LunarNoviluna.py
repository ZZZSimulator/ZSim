from typing import Any

from zsim.sim_progress.data_struct.schedule_dispatch import (
    ScheduledEventEmitterProvider,
)

from .. import Buff, check_preparation, find_tick
from ..JudgeTools.PreparationContext import (
    ResourceRefreshCommandPort,
    build_preparation_context_from_buff,
)
from ._preparation_helpers import ensure_equipper_template_record, prepare_with_context


class LunarNovilunaRecord:
    def __init__(self):
        self.equipper = None
        self.char = None
        self.enegy_value_map = {1: 3, 2: 3.5, 3: 4, 4: 4.5, 5: 5}
        self.sub_exist_buff_dict = None


class LunarNoviluna(Buff.BuffLogic):
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
        self.xstart = self.special_start_logic
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
            item_name="「月相」-朔",
            record_factory=LunarNovilunaRecord,
            context_builder=build_preparation_context_from_buff,
        )

    def special_start_logic(self, **kwargs):
        self.check_record_module()
        self.get_prepared(equipper="「月相」-朔", sub_exist_buff_dict=1)

        energy_value = self.record.enegy_value_map[self.buff_instance.ft.refinement]
        self._emit_scheduled_refresh(
            sp_target=(self.record.char.NAME,),
            sp_value=energy_value,
        )
        self.buff_instance.simple_start(
            find_tick(sim_instance=self.buff_instance.sim_instance),
            self.record.sub_exist_buff_dict,
        )
