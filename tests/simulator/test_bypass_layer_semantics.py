from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Sequence, cast

from zsim.models.event_enums import ListenerBroadcastSignal as LBS
from zsim.sim_progress.Buff.JudgeTools import build_preparation_context_from_sim_instance
from zsim.sim_progress.data_struct.BattleEventListener import ListenerManger
from zsim.sim_progress.data_struct.planned_queue import PlannedEventQueue
from zsim.sim_progress.data_struct.schedule_dispatch import (
    ScheduleDispatchPort,
    create_schedule_dispatch_port,
)
from zsim.sim_progress.data_struct.SchedulePreload import SchedulePreload
from zsim.sim_progress.ScheduledEvent.buff_runtime import BuffRuntimeReadPort, BuffRuntimeState
from zsim.sim_progress.ScheduledEvent.event_handlers.context import EventContext
from zsim.sim_progress.ScheduledEvent.event_handlers.handlers.preload import PreloadEventHandler


class _RuntimeViewStub(BuffRuntimeReadPort):
    def get_active_buffs(self, beneficiary: str) -> Sequence[Any]:
        return ()

    def get_active_buff_view(self):
        return {}

    def get_exist_buff_snapshot(self, beneficiary: str):
        return {}

    def get_exist_buff_snapshot_view(self):
        return {}


class _RecordingListener:
    def __init__(self) -> None:
        self.calls: list[tuple[object, LBS, dict[str, object]]] = []

    def listening_event(self, event: object, signal: LBS, **kwargs: object) -> None:
        self.calls.append((event, signal, kwargs))


class _FuturePreloadEvent:
    execute_tick = 11

    def execute_myself(self) -> None:
        raise AssertionError("future retained event should be requeued")


def _attach_planned_queue(schedule_data: SimpleNamespace) -> list[object]:
    events = getattr(schedule_data, "event_list", [])
    schedule_data.event_list = events
    schedule_data.planned_event_queue = PlannedEventQueue(
        get_events=lambda: schedule_data.event_list,
        set_events=lambda new_events: setattr(schedule_data, "event_list", new_events),
    )
    return events


def test_schedule_dispatch_publish_is_queue_only_not_broadcast_or_runtime_write() -> None:
    schedule_data = SimpleNamespace(event_list=[])
    _attach_planned_queue(schedule_data)
    dispatch_port = create_schedule_dispatch_port(schedule_data=cast(Any, schedule_data))

    assert isinstance(dispatch_port, ScheduleDispatchPort)

    dispatch_port.publish_scheduled("planned-event")

    assert schedule_data.event_list == ["planned-event"]


def test_listener_broadcast_is_synchronous_not_schedule_publish() -> None:
    schedule_data = SimpleNamespace(event_list=[])
    _attach_planned_queue(schedule_data)
    listener = _RecordingListener()
    manager = ListenerManger(cast(Any, SimpleNamespace(schedule_data=schedule_data)))
    cast(Any, manager)._listeners_group["enemy"]["probe"] = listener

    manager.broadcast_event(event="broadcast-event", signal=LBS.DISORDER_SPAWN, source="test")

    assert listener.calls == [
        ("broadcast-event", LBS.DISORDER_SPAWN, {"source": "test"}),
    ]
    assert schedule_data.event_list == []


def test_handler_requeue_uses_planned_queue_owner() -> None:
    schedule_data = SimpleNamespace(event_list=[])
    _attach_planned_queue(schedule_data)
    context = EventContext(
        data=cast(Any, schedule_data),
        tick=10,
        enemy=cast(Any, SimpleNamespace()),
        buff_runtime_view=_RuntimeViewStub(),
        runtime_command_port=cast(Any, SimpleNamespace()),
        action_stack=cast(Any, SimpleNamespace()),
        sim_instance=cast(Any, SimpleNamespace()),
    )
    event = _FuturePreloadEvent()

    PreloadEventHandler().handle(cast(Any, event), context)

    assert schedule_data.event_list == [event]


def test_preparation_context_preload_commands_publish_only_scheduled_events() -> None:
    character = SimpleNamespace(NAME="alpha", CID=1001)
    preload_data = SimpleNamespace(marker="preload-data")
    schedule_data = SimpleNamespace(event_list=[], enemy=SimpleNamespace())
    _attach_planned_queue(schedule_data)
    sim_instance = SimpleNamespace(
        tick=23,
        load_data=SimpleNamespace(
            exist_buff_dict={"alpha": {}},
            action_stack=SimpleNamespace(),
        ),
        init_data=SimpleNamespace(Judge_list_set=[]),
        char_data=SimpleNamespace(char_obj_list=[character]),
        global_stats=SimpleNamespace(DYNAMIC_BUFF_DICT={"alpha": []}),
        schedule_data=schedule_data,
        preload=SimpleNamespace(preload_data=preload_data),
    )
    sim_instance.buff_runtime_state = BuffRuntimeState(
        template_registry=sim_instance.load_data.exist_buff_dict,
        pending_queue={"alpha": []},
        active_store=sim_instance.global_stats.DYNAMIC_BUFF_DICT,
        enemy_mirror=[],
    )
    preparation_context = build_preparation_context_from_sim_instance(cast(Any, sim_instance))

    preparation_context.preload_commands.schedule_preload_events(
        preload_tick_list=[23, 24],
        skill_tag_list=["1461_Cinema_6", "1461_Cinema_6"],
        apl_priority_list=[0, 1],
        active_generation_list=[False, True],
    )

    assert [type(event) for event in schedule_data.event_list] == [
        SchedulePreload,
        SchedulePreload,
    ]
    assert [cast(SchedulePreload, event).execute_tick for event in schedule_data.event_list] == [
        23,
        24,
    ]
