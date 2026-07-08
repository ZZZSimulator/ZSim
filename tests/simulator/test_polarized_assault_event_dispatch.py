from __future__ import annotations

from copy import deepcopy
from types import SimpleNamespace
from typing import cast

import pytest

from zsim.models.event_enums import ListenerBroadcastSignal as LBS
from zsim.sim_progress.data_struct import PolarizedAssaultEventClass as polarized_module
from zsim.sim_progress.data_struct.PolarizedAssaultEventClass import PolarizedAssaultEvent
from zsim.sim_progress.data_struct.schedule_dispatch import (
    ScheduledEventEmitterProvider,
    ScheduleDispatchPort,
)
from zsim.sim_progress.Update import UpdateAnomaly as update_anomaly_module


class _FailFastEventList(list):
    def append(self, item):
        raise AssertionError(
            "PolarizedAssaultEvent should publish follow-up events via dispatch port"
        )


class _RecordingDispatchPort:
    def __init__(self, call_order: list[tuple[str, object]]) -> None:
        self.events: list[object] = []
        self._call_order = call_order

    def publish_scheduled(self, event: object) -> None:
        marker = getattr(event, "marker", type(event).__name__)
        self._call_order.append(("publish", marker))
        self.events.append(event)


class _FakeAnomalyBar:
    def __init__(
        self,
        *,
        marker: str,
        sim_instance,
        element_type: int,
        settled: bool = False,
    ) -> None:
        self.marker = marker
        self.sim_instance = sim_instance
        self.element_type = element_type
        self.settled = settled
        self.rename_tag = None
        self.active = True

    def anomaly_settled(self) -> None:
        self.settled = True

    def __deepcopy__(self, memo):
        copied = type(self)(
            marker=self.marker,
            sim_instance=self.sim_instance,
            element_type=self.element_type,
            settled=self.settled,
        )
        copied.rename_tag = self.rename_tag
        copied.active = self.active
        return copied


def test_polarized_assault_event_publishes_follow_ups_via_dispatch_port_in_order(
    monkeypatch: pytest.MonkeyPatch,
):
    call_order: list[tuple[str, object]] = []
    dispatch_port = _RecordingDispatchPort(call_order)
    polarized_output = SimpleNamespace(marker="polarized-output")
    disorder = SimpleNamespace(marker="disorder", element_type=3)

    def broadcast_event(*, event, signal, **kwargs):
        call_order.append(("broadcast", signal))

    sim_instance = SimpleNamespace(
        tick=23,
        schedule_data=SimpleNamespace(
            event_list=_FailFastEventList(),
            change_process_state=lambda: None,
        ),
        listener_manager=SimpleNamespace(broadcast_event=broadcast_event),
        enemy=None,
    )
    active_anomaly = _FakeAnomalyBar(
        marker="active-anomaly",
        sim_instance=sim_instance,
        element_type=3,
    )
    sim_instance.enemy = SimpleNamespace(
        dynamic=SimpleNamespace(get_active_anomaly=lambda: [active_anomaly]),
    )
    event_anomaly = _FakeAnomalyBar(
        marker="polarized-assault",
        sim_instance=sim_instance,
        element_type=0,
    )
    char = SimpleNamespace(NAME="爱丽丝", cinema=2)
    skill_node = SimpleNamespace(
        skill_tag="1401_Q",
        skill=SimpleNamespace(skill_text="Polarized Assault"),
    )
    event = PolarizedAssaultEvent(
        execute_tick=sim_instance.tick,
        anomlay_bar=deepcopy(event_anomaly),
        char_instance=char,
        skill_node=skill_node,
        scheduled_event_emitter_provider=ScheduledEventEmitterProvider(
            lambda: cast(ScheduleDispatchPort, dispatch_port)
        ),
    )

    def fake_anomaly_effect_active(**kwargs):
        assert kwargs["new_anomaly"] is event.anomaly_bar
        assert kwargs["element_type"] == 0
        call_order.append(("anomaly_effect_active", kwargs["new_anomaly"].marker))

    def fake_new_anomaly(anomaly_bar, *, active_by, sim_instance):
        assert anomaly_bar is event.anomaly_bar
        assert active_by is event.skill_node
        assert sim_instance is event.sim_instance
        return polarized_output

    def fake_spawn_output(anomaly_bar, mode_number, sim_instance, **kwargs):
        assert mode_number == 1
        assert kwargs["skill_node"] is event.skill_node
        call_order.append(("spawn_output", getattr(anomaly_bar, "marker", "unknown")))
        sim_instance.listener_manager.broadcast_event(event=disorder, signal=LBS.DISORDER_SPAWN)
        return disorder

    monkeypatch.setattr(update_anomaly_module, "anomaly_effect_active", fake_anomaly_effect_active)
    monkeypatch.setattr(update_anomaly_module, "spawn_output", fake_spawn_output)
    monkeypatch.setattr(polarized_module, "NewAnomaly", fake_new_anomaly)

    event.execute()

    assert dispatch_port.events == [polarized_output, disorder]
    assert sim_instance.schedule_data.event_list == []
    assert active_anomaly.settled is False
    assert call_order == [
        ("broadcast", LBS.POLARIZED_ASSAULT_SPAWN),
        ("publish", "polarized-output"),
        ("anomaly_effect_active", "polarized-assault"),
        ("spawn_output", "active-anomaly"),
        ("broadcast", LBS.DISORDER_SPAWN),
        ("publish", "disorder"),
    ]
