from __future__ import annotations

import sys
from types import SimpleNamespace
from typing import Any, cast

import zsim.define as define_module
from zsim.sim_progress.data_struct import PolarizedAssaultEvent
from zsim.sim_progress.data_struct.schedule_dispatch import (
    ScheduledEventEmitterProvider,
    ScheduleDispatchPort,
)

sys.modules.setdefault("define", define_module)

from zsim.sim_progress.Buff.BuffXLogic.AlicePolarizedAssaultTrigger import (
    AlicePolarizedAssaultTrigger,
)


class _FailFastEventList(list):
    def append(self, item):
        raise AssertionError("AlicePolarizedAssaultTrigger should publish via dispatch port")


class _RecordingDispatchPort(ScheduleDispatchPort):
    def __init__(self) -> None:
        self.events: list[object] = []

    def publish_scheduled(self, event: object) -> None:
        self.events.append(event)


class _FakeAnomalyBar:
    def __init__(self, *, sim_instance) -> None:
        self.sim_instance = sim_instance
        self.element_type = 0
        self.settled = False
        self.rename_tag = None
        self.activated_by = None

    def anomaly_settled(self) -> None:
        self.settled = True


def _build_trigger(dispatch_port: _RecordingDispatchPort):
    schedule_data = SimpleNamespace(
        enemy=None,
        event_list=_FailFastEventList(),
        change_process_state=lambda: None,
    )
    sim_instance = SimpleNamespace(
        tick=17,
        schedule_data=schedule_data,
    )
    anomaly_bar = _FakeAnomalyBar(sim_instance=sim_instance)
    schedule_data.enemy = SimpleNamespace(anomaly_bars_dict={0: anomaly_bar})
    buff_instance = SimpleNamespace(sim_instance=sim_instance)
    trigger = AlicePolarizedAssaultTrigger(
        buff_instance,
        scheduled_event_emitter_provider=ScheduledEventEmitterProvider(lambda: dispatch_port),
    )
    trigger_any = cast(Any, trigger)
    trigger_any.check_record_module = lambda: None
    trigger_any.get_prepared = lambda **kwargs: None

    trigger_origin = SimpleNamespace(
        skill_tag="1401_Q",
        skill=SimpleNamespace(skill_text="Polarized Assault"),
    )
    char = SimpleNamespace(NAME="\u7231\u4e3d\u4e1d", cinema=2)
    trigger_any.record = SimpleNamespace(
        char=char,
        trigger_origin=trigger_origin,
    )
    return trigger, sim_instance, anomaly_bar, char, trigger_origin


def test_alice_polarized_assault_trigger_publishes_via_dispatch_port():
    dispatch_port = _RecordingDispatchPort()
    trigger, sim_instance, anomaly_bar, char, trigger_origin = _build_trigger(dispatch_port)

    trigger.special_effect_logic()

    assert len(dispatch_port.events) == 1
    published_event = dispatch_port.events[0]
    assert isinstance(published_event, PolarizedAssaultEvent)
    assert published_event.execute_tick == sim_instance.tick
    assert published_event.char is char
    assert published_event.skill_node is trigger_origin
    assert published_event.anomaly_bar is not anomaly_bar
    assert published_event.anomaly_bar.activated_by is trigger_origin
    assert published_event.anomaly_bar.settled is True
    assert anomaly_bar.settled is False
    assert sim_instance.schedule_data.event_list == []
    assert trigger.record.trigger_origin is None
