from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Sequence, cast

import pytest

import zsim.sim_progress.ScheduledEvent as scheduled_event_module
from zsim.sim_progress.data_struct.planned_queue import (
    PlannedEventQueue,
    ensure_planned_event_queue,
)
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


class _EventProbe:
    def __init__(self, execute_tick: int, schedule_priority: int = 0) -> None:
        self.execute_tick = execute_tick
        self.schedule_priority = schedule_priority

    def execute_myself(self) -> None:
        raise AssertionError("future event should be retained")


def _attach_planned_queue(schedule_data: SimpleNamespace, events: list[Any]) -> None:
    schedule_data.planned_event_queue = PlannedEventQueue(
        get_events=lambda: events,
        set_events=lambda new_events: events.__setitem__(slice(None), new_events),
    )


def _runtime_state_for_test() -> BuffRuntimeState:
    return BuffRuntimeState(
        template_registry={"alpha": {}, "enemy": {}},
        pending_queue={"alpha": [], "enemy": []},
        active_store={"alpha": [], "enemy": []},
        enemy_mirror=[],
    )


def test_ensure_planned_event_queue_requires_owner() -> None:
    with pytest.raises(AttributeError, match="planned_event_queue"):
        ensure_planned_event_queue(SimpleNamespace())


def test_scheduled_event_selects_due_events_from_planned_queue_owner() -> None:
    due_low = _EventProbe(execute_tick=10, schedule_priority=0)
    future = _EventProbe(execute_tick=11, schedule_priority=10)
    due_high = _EventProbe(execute_tick=10, schedule_priority=5)
    events = [due_low, future, due_high]
    schedule_data = SimpleNamespace(enemy=object(), char_obj_list=[])
    _attach_planned_queue(schedule_data, events)
    scheduled_event = scheduled_event_module.ScheduledEvent.from_runtime_state(
        schedule_data=cast(Any, schedule_data),
        tick=10,
        action_stack=object(),
        buff_runtime_state=_runtime_state_for_test(),
        sim_instance=cast(Any, object()),
    )
    scheduled_event.execute_tick_key_map[_EventProbe] = "execute_tick"

    assert scheduled_event.select_processable_event() == [due_low, due_high]


def test_scheduled_event_reuses_run_scoped_handler_factory() -> None:
    events: list[Any] = []
    schedule_data = SimpleNamespace(enemy=object(), char_obj_list=[])
    _attach_planned_queue(schedule_data, events)
    sim_instance = SimpleNamespace()

    first = scheduled_event_module.ScheduledEvent.from_runtime_state(
        schedule_data=cast(Any, schedule_data),
        tick=10,
        action_stack=object(),
        buff_runtime_state=_runtime_state_for_test(),
        sim_instance=cast(Any, sim_instance),
    )
    second = scheduled_event_module.ScheduledEvent.from_runtime_state(
        schedule_data=cast(Any, schedule_data),
        tick=11,
        action_stack=object(),
        buff_runtime_state=_runtime_state_for_test(),
        sim_instance=cast(Any, sim_instance),
    )

    assert first._event_handler_factory is second._event_handler_factory
    assert sim_instance._scheduled_event_handler_factory is first._event_handler_factory


def test_handler_requeue_writes_to_planned_queue_owner() -> None:
    events: list[Any] = []
    schedule_data = SimpleNamespace()
    _attach_planned_queue(schedule_data, events)
    context = EventContext(
        data=cast(Any, schedule_data),
        tick=10,
        enemy=cast(Any, SimpleNamespace()),
        buff_runtime_view=_RuntimeViewStub(),
        runtime_command_port=cast(Any, SimpleNamespace()),
        action_stack=cast(Any, SimpleNamespace()),
        sim_instance=cast(Any, SimpleNamespace()),
    )
    future = _EventProbe(execute_tick=11)

    PreloadEventHandler().handle(cast(Any, future), context)

    assert events == [future]
