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


class ElegantVanitySpRecoverRecord:
    def __init__(self):
        self.equipper = None
        self.char = None
        self.sub_exist_buff_dict = None
        self.energy_value_dict = {1: 5, 2: 5.5, 3: 6, 4: 6.5, 5: 7}


class ElegantVanitySpRecover(Buff.BuffLogic):
    """玲珑妆匣的回能Buff逻辑。"""

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
            item_name="玲珑妆匣",
            record_factory=ElegantVanitySpRecoverRecord,
            context_builder=build_preparation_context_from_buff,
        )

    def special_start_logic(self, **kwargs):
        """
        这部分的代码主要是负责构建一个ScheduleRefreshData实例的，
        而simple_start只是为了启动一次，让Log记录到这个buff。
        Buff自身没有效果。
        """
        self.check_record_module()
        self.get_prepared(equipper="玲珑妆匣", sub_exist_buff_dict=1)
        tick_now = JudgeTools.find_tick(sim_instance=self.buff_instance.sim_instance)
        self.buff_instance.simple_start(tick_now, self.record.sub_exist_buff_dict)
        energy_value = self.record.energy_value_dict[int(self.buff_instance.ft.refinement)]
        self._emit_scheduled_refresh(
            sp_target=(self.record.char.NAME,),
            sp_value=energy_value,
        )
        # print(f'玲珑妆匣回能触发！')
