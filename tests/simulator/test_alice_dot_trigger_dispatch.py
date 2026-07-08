from __future__ import annotations

from types import SimpleNamespace
from typing import cast

import pytest

from zsim.models.event_enums import ListenerBroadcastSignal as LBS
from zsim.sim_progress.data_struct.BattleEventListener import (
    AliceDotTriggerListener as alice_dot_module,
)
from zsim.sim_progress.data_struct.BattleEventListener.AliceDotTriggerListener import (
    AliceDotTriggerListener,
)
from zsim.sim_progress.data_struct.schedule_dispatch import (
    ScheduledEventEmitterProvider,
    ScheduleDispatchPort,
)
from zsim.sim_progress.Dot.BaseDot import Dot


class _FailFastEventList(list):
    def append(self, item):
        raise AssertionError("AliceDotTriggerListener should publish via dispatch port")


class _RecordingDispatchPort:
    def __init__(self, call_order: list[str] | None = None) -> None:
        self.events: list[object] = []
        self._call_order = call_order

    def publish_scheduled(self, event: object) -> None:
        if self._call_order is not None:
            self._call_order.append("publish")
        self.events.append(event)


class _FakeAnomalyBar:
    def __init__(self) -> None:
        self.settled = False

    def anomaly_settled(self) -> None:
        self.settled = True


class _FakeDot(Dot):
    def __init__(
        self,
        *,
        index: str,
        anomaly_data: object,
        call_order: list[str] | None = None,
    ) -> None:
        super().__init__(bar=None, sim_instance=None)
        self.ft.index = index
        self.ft.max_duration = 60
        self.anomaly_data = anomaly_data
        self.started_at: int | None = None
        self.ended_at: int | None = None
        self._call_order = call_order

    def start(self, timenow: int):
        if self._call_order is not None:
            self._call_order.append("start_new_dot")
        self.started_at = timenow
        super().start(timenow)

    def end(self, timenow: int):
        if self._call_order is not None:
            self._call_order.append("end_old_dot")
        self.ended_at = timenow
        super().end(timenow)


class _RecordingDotList(list):
    def __init__(self, call_order: list[str]) -> None:
        super().__init__()
        self._call_order = call_order

    def append(self, item):
        self._call_order.append("register_dot")
        super().append(item)

    def remove(self, item):
        self._call_order.append("remove_old_dot")
        super().remove(item)


class _ForbiddenRuntimeCommandPort:
    def update_anomaly(self, **kwargs):
        raise AssertionError("Alice dot listener should not issue runtime commands")


def _build_listener(
    *,
    event_list,
    call_order: list[str] | None = None,
    scheduled_event_emitter_provider: ScheduledEventEmitterProvider | None = None,
):
    dynamic_dot_list = _RecordingDotList(call_order) if call_order is not None else []

    def fail_broadcast(**kwargs):
        raise AssertionError("Alice dot listener should not broadcast listener events")

    enemy = SimpleNamespace(
        dynamic=SimpleNamespace(
            assault=True,
            dynamic_dot_list=dynamic_dot_list,
        ),
        anomaly_bars_dict={0: _FakeAnomalyBar()},
    )
    sim_instance = SimpleNamespace(
        tick=10,
        schedule_data=SimpleNamespace(
            enemy=enemy,
            event_list=event_list,
            change_process_state=lambda: None,
        ),
        char_data=SimpleNamespace(find_char_obj=lambda CID: SimpleNamespace(CID=CID, NAME="Alice")),
        listener_manager=SimpleNamespace(broadcast_event=fail_broadcast),
        runtime_command_port=_ForbiddenRuntimeCommandPort(),
    )
    return (
        AliceDotTriggerListener(
            listener_id="Alice_5",
            sim_instance=sim_instance,
            scheduled_event_emitter_provider=scheduled_event_emitter_provider,
        ),
        sim_instance,
        enemy,
    )


def test_alice_dot_trigger_listener_publishes_dot_anomaly_via_dispatch_port(
    monkeypatch: pytest.MonkeyPatch,
):
    call_order: list[str] = []
    dispatch_port = _RecordingDispatchPort(call_order)
    listener, sim_instance, enemy = _build_listener(
        event_list=_FailFastEventList(),
        call_order=call_order,
        scheduled_event_emitter_provider=ScheduledEventEmitterProvider(
            lambda: cast(ScheduleDispatchPort, dispatch_port)
        ),
    )
    previous_dot = _FakeDot(
        index="AliceCoreSkillAssaultDot",
        anomaly_data=SimpleNamespace(tag="old"),
        call_order=call_order,
    )
    enemy.dynamic.dynamic_dot_list.append(previous_dot)
    call_order.clear()
    published_bar = SimpleNamespace(tag="new")
    replacement_dot = _FakeDot(
        index="AliceCoreSkillAssaultDot",
        anomaly_data=published_bar,
        call_order=call_order,
    )
    received_bar: dict[str, _FakeAnomalyBar] = {}
    wrapped_bar = SimpleNamespace(tag="wrapped")

    def fake_spawn_normal_dot(*, dot_index, sim_instance, bar: _FakeAnomalyBar):
        assert dot_index == "AliceCoreSkillAssaultDot"
        assert sim_instance is listener.sim_instance
        received_bar["value"] = bar
        return replacement_dot

    monkeypatch.setattr(
        "zsim.sim_progress.Update.UpdateAnomaly.spawn_normal_dot",
        fake_spawn_normal_dot,
    )

    def fake_new_anomaly(anomaly_data, *, sim_instance):
        assert anomaly_data is published_bar
        assert sim_instance is listener.sim_instance
        return wrapped_bar

    monkeypatch.setattr(alice_dot_module, "NewAnomaly", fake_new_anomaly)

    listener.listening_event(event=None, signal=LBS.ASSAULT_STATE_ON)

    assert listener.char is not None
    assert previous_dot.ended_at == sim_instance.tick
    assert replacement_dot.started_at == sim_instance.tick
    assert enemy.dynamic.dynamic_dot_list == [replacement_dot]
    assert replacement_dot.anomaly_data is wrapped_bar
    assert dispatch_port.events == [wrapped_bar]
    assert call_order == [
        "start_new_dot",
        "end_old_dot",
        "remove_old_dot",
        "register_dot",
        "publish",
    ]
    assert sim_instance.schedule_data.event_list == []
    assert received_bar["value"] is not enemy.anomaly_bars_dict[0]
    assert received_bar["value"].settled is True
