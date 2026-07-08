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


class SliceofTimeExtraResourcesRecord:
    def __init__(self):
        self.equipper = None
        self.char = None
        self.action_stack = None
        self.sub_exist_buff_dict = None
        self.decibel_value_dict = {
            1: {4: 20, 2: 25, 7: 30, 8: 30, 9: 30, 5: 35},
            2: {4: 23, 2: 28.5, 7: 34.5, 8: 34.5, 9: 34.5, 5: 40},
            3: {4: 26, 2: 32, 7: 39, 8: 39, 9: 39, 5: 45},
            4: {4: 29, 2: 35.5, 7: 43.5, 8: 43.5, 9: 43.5, 5: 50},
            5: {4: 32, 2: 40, 7: 48, 8: 48, 9: 48, 5: 55},
        }
        self.energy_value_dict = {1: 0.7, 2: 0.8, 3: 0.9, 4: 1.0, 5: 1.1}
        self.last_update_tick_box = {"E_EX": 0, "Sup": 0, "QTE": 0, "CA": 0}
        self.update_key_dict = {
            2: "E_EX",
            4: "CA",
            5: "QTE",
            7: "Sup",
            8: "Sup",
            9: "Sup",
        }


class SliceofTimeExtraResources(Buff.BuffLogic):
    """
    这是时光切片的复杂效果逻辑。
    虽然该buff的buff effect为空，但是在special_start逻辑中，内置了恢复能量和喧响值的方法。
    通过构建Schedule Refresh Data的实例，并向event list中添加，
    就可以实现角色的喧响值和能量值的修改。
    """

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
        decibel_target: tuple[str, ...],
        decibel_value: float | int,
    ) -> None:
        refresh_commands = ResourceRefreshCommandPort(self._scheduled_event_emitter_provider)
        refresh_commands.publish_refresh(
            sp_target=sp_target,
            sp_value=sp_value,
            decibel_target=decibel_target,
            decibel_value=decibel_value,
        )

    def check_record_module(self):
        ensure_equipper_template_record(
            self,
            item_name="时光切片",
            record_factory=SliceofTimeExtraResourcesRecord,
            context_builder=build_preparation_context_from_buff,
        )

    def special_judge_logic(self, **kwargs):
        """
        第一层判定是trigger_buff_level的判定
        通过第一层判定后，再过内置CD检测。
        """
        self.check_record_module()
        self.get_prepared(equipper="时光切片", action_stack=1)
        action_now = self.record.action_stack.peek()
        trigger_buff_level = action_now.mission_node.skill.trigger_buff_level
        tick_now = JudgeTools.find_tick(sim_instance=self.buff_instance.sim_instance)
        if trigger_buff_level in [4, 2, 7, 8, 9, 5]:
            ready = self.check_update_cd(trigger_buff_level, tick_now)
            if ready:
                return True
            else:
                return False
        else:
            return False

    def special_start_logic(self, **kwargs):
        """
        这部分的代码主要是负责构建一个ScheduleRefreshData实例的，
        而simple_start只是为了启动一次，让Log记录到这个buff。
        Buff自身没有效果。
        """
        self.check_record_module()
        self.get_prepared(equipper="时光切片", action_stack=1, sub_exist_buff_dict=1)
        tick_now = JudgeTools.find_tick(sim_instance=self.buff_instance.sim_instance)
        self.buff_instance.simple_start(tick_now, self.record.sub_exist_buff_dict)
        action_now = self.record.action_stack.peek()
        trigger_buff_level = action_now.mission_node.skill.trigger_buff_level
        decibel_value = self.record.decibel_value_dict[self.buff_instance.ft.refinement][
            trigger_buff_level
        ]
        energy_value = self.record.energy_value_dict[self.buff_instance.ft.refinement]
        actor_name = action_now.mission_character
        self._emit_scheduled_refresh(
            sp_target=(self.record.char.NAME,),
            sp_value=energy_value,
            decibel_target=(actor_name,),
            decibel_value=decibel_value,
        )

    def check_update_cd(self, tbl: int, tick_now: int):
        """
        检测内置CD！由于闪避反击、强化E、支援技、QTE的触发CD是分开计算的，
        所以，这里也要根据trigger buff level进行分流，分别检测各自的CD。
        """
        if tbl not in self.record.update_key_dict:
            raise ValueError(f"传入的Trigger Buff Level为{tbl}，不在检测范围内！")
        key = self.record.update_key_dict[tbl]
        last_update_tick = self.record.last_update_tick_box[key]
        if last_update_tick == 0:
            self.record.last_update_tick_box[key] = tick_now
            return True
        if tick_now - last_update_tick > self.buff_instance.ft.cd:
            self.record.last_update_tick_box[key] = tick_now
            return True
        else:
            return False
