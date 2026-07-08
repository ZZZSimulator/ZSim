from __future__ import annotations

import sys
from types import SimpleNamespace
from typing import Any, Callable, cast

import pytest

import zsim.define as define_module
import zsim.sim_progress.ScheduledEvent as scheduled_event_module
import zsim.sim_progress.ScheduledEvent.buff_runtime as buff_runtime_module
import zsim.sim_progress.ScheduledEvent.runtime_command as runtime_command_module

sys.modules.setdefault("define", define_module)

import zsim.sim_progress.Buff.BuffXLogic.YanagiPolarityDisorderTrigger as yanagi_module
from zsim.sim_progress.Buff import JudgeTools
from zsim.sim_progress.Buff.BuffXLogic.YanagiPolarityDisorderTrigger import (
    YanagiPolarityDisorderTrigger,
    YanagiPolarityDisorderTriggerRecord,
)
from zsim.sim_progress.data_struct.schedule_dispatch import (
    ScheduledEventEmitterProvider,
    ScheduleDispatchPort,
)
from zsim.sim_progress.Load import LoadingMission
from zsim.sim_progress.Preload import SkillNode


class _FailFastEventList(list):
    def append(self, item):
        raise AssertionError("YanagiPolarityDisorderTrigger should publish via dispatch port")


class _RecordingDispatchPort(ScheduleDispatchPort):
    def __init__(
        self,
        call_order: list[str],
        on_publish: Callable[[object], None] | None = None,
    ) -> None:
        self.events: list[object] = []
        self._call_order = call_order
        self._on_publish = on_publish

    def publish_scheduled(self, event: object) -> None:
        self._call_order.append("publish")
        self.events.append(event)
        if self._on_publish is not None:
            self._on_publish(event)


class _FakeAnomalyBar:
    def __init__(self, *, marker: str, settled: bool = False) -> None:
        self.marker = marker
        self.settled = settled
        self.settled_calls = 0

    def anomaly_settled(self) -> None:
        self.settled = True
        self.settled_calls += 1

    def __deepcopy__(self, memo):
        copied = type(self)(marker=self.marker, settled=self.settled)
        copied.settled_calls = self.settled_calls
        return copied


class _DynamicReadProbe:
    def __init__(self, *, is_active: bool) -> None:
        self.is_active = is_active
        self.calls: list[str] = []

    def is_under_anomaly(self) -> bool:
        self.calls.append("is_under_anomaly")
        return self.is_active


def _block_legacy_event_lookup(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_find_event_list(*args, **kwargs):
        raise AssertionError("YanagiPolarityDisorderTrigger should not read raw event_list")

    monkeypatch.setattr(JudgeTools, "find_event_list", fail_find_event_list, raising=False)


def _patch_runtime_boundary_guards(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_create_runtime_command_port(*args: object, **kwargs: object) -> None:
        raise AssertionError("YanagiPolarityDisorderTrigger should not create RuntimeCommandPort")

    def fail_create_buff_runtime_read_port(*args: object, **kwargs: object) -> None:
        raise AssertionError("YanagiPolarityDisorderTrigger should not create BuffRuntimeReadPort")

    monkeypatch.setattr(
        runtime_command_module,
        "create_runtime_command_port",
        fail_create_runtime_command_port,
        raising=False,
    )
    monkeypatch.setattr(
        scheduled_event_module,
        "create_runtime_command_port",
        fail_create_runtime_command_port,
        raising=False,
    )
    monkeypatch.setattr(
        buff_runtime_module,
        "create_buff_runtime_read_port",
        fail_create_buff_runtime_read_port,
        raising=False,
    )
    monkeypatch.setattr(
        scheduled_event_module,
        "create_buff_runtime_read_port",
        fail_create_buff_runtime_read_port,
        raising=False,
    )


def _build_skill_node(*, skill_tag: str = "1221_Q") -> SkillNode:
    skill = SimpleNamespace(
        skill_tag=skill_tag,
        char_name="鏌?",
        hit_times=1,
        labels=None,
        ticks=12,
        tick_list=[11],
        heavy_attack=False,
        element_type=0,
        trigger_buff_level=6,
    )
    return SkillNode(skill=skill, preload_tick=30)


def test_yanagi_polarity_disorder_trigger_publishes_spawn_output_via_dispatch_port(
    monkeypatch: pytest.MonkeyPatch,
):
    call_order: list[str] = []
    signal_states: list[tuple[str, bool]] = []
    listener_calls: list[tuple[tuple[object, ...], dict[str, object]]] = []

    def fail_listener_broadcast(*args: object, **kwargs: object) -> None:
        listener_calls.append((args, kwargs))
        raise AssertionError(
            "YanagiPolarityDisorderTrigger should leave listener broadcast to spawn_output"
        )

    def fail_change_process_state() -> None:
        raise AssertionError("YanagiPolarityDisorderTrigger has no report-state write")

    dispatch_port = _RecordingDispatchPort(
        call_order,
        on_publish=lambda event: signal_states.append(
            ("publish", record.polarity_disorder_update_signal)
        ),
    )
    active_anomaly_bar = _FakeAnomalyBar(marker="active-anomaly", settled=False)
    schedule_data = SimpleNamespace(
        event_list=_FailFastEventList(),
        change_process_state=fail_change_process_state,
    )
    sim_instance = SimpleNamespace(
        tick=41,
        schedule_data=schedule_data,
        listener_manager=SimpleNamespace(broadcast_event=fail_listener_broadcast),
    )
    buff_instance = SimpleNamespace(
        sim_instance=sim_instance,
        ft=SimpleNamespace(index="yanagi-trigger"),
    )
    logic = YanagiPolarityDisorderTrigger(
        buff_instance,
        scheduled_event_emitter_provider=ScheduledEventEmitterProvider(lambda: dispatch_port),
    )
    record = YanagiPolarityDisorderTriggerRecord()
    record.char = SimpleNamespace(cinema=2)
    dynamic = _DynamicReadProbe(is_active=True)
    record.enemy = SimpleNamespace(
        dynamic=dynamic,
        get_active_anomaly_bar=lambda: active_anomaly_bar,
    )
    record.e_counter = {"update_from": "prev-hit", "count": 2}
    helper_calls: list[object] = []
    active_bar_helper_calls: list[object] = []

    def fake_read_enemy_anomaly_active(enemy: Any) -> bool:
        helper_calls.append(enemy)
        return bool(enemy.dynamic.is_under_anomaly())

    def fake_read_enemy_active_anomaly_bar(enemy: Any) -> object:
        active_bar_helper_calls.append(enemy)
        return enemy.get_active_anomaly_bar()

    monkeypatch.setattr(logic, "check_record_module", lambda: setattr(logic, "record", record))
    monkeypatch.setattr(logic, "get_prepared", lambda **kwargs: None)
    monkeypatch.setattr(
        yanagi_module,
        "read_enemy_anomaly_active",
        fake_read_enemy_anomaly_active,
    )
    monkeypatch.setattr(
        yanagi_module,
        "read_enemy_active_anomaly_bar",
        fake_read_enemy_active_anomaly_bar,
    )
    monkeypatch.setattr(yanagi_module, "find_tick", lambda *, sim_instance: sim_instance.tick)
    _patch_runtime_boundary_guards(monkeypatch)
    _block_legacy_event_lookup(monkeypatch)

    skill_node = _build_skill_node()
    loading_mission = LoadingMission(skill_node)
    loading_mission.mission_start(skill_node.preload_tick, report=False)

    spawn_calls: list[tuple[str, object]] = []
    published_output = SimpleNamespace(marker="polarity-output")

    def fake_spawn_output(
        anomaly_bar,
        mode_number,
        polarity_ratio,
        skill_node,
        sim_instance,
    ):
        call_order.append("spawn_output")
        signal_states.append(("spawn_output", record.polarity_disorder_update_signal))
        spawn_calls.extend(
            [
                ("mode_number", mode_number),
                ("polarity_ratio", polarity_ratio),
                ("skill_node", skill_node),
                ("sim_instance", sim_instance),
                ("settled", anomaly_bar.settled),
                ("same_object", anomaly_bar is active_anomaly_bar),
                ("marker", anomaly_bar.marker),
            ]
        )
        return published_output

    monkeypatch.setattr("zsim.sim_progress.Update.spawn_output", fake_spawn_output)

    assert logic.special_judge_logic(skill_node=cast(Any, loading_mission)) is True
    assert helper_calls == [record.enemy]
    assert dynamic.calls == ["is_under_anomaly"]
    assert record.polarity_disorder_update_signal is True

    logic.special_effect_logic(skill_node=skill_node)

    assert logic.record is record
    assert active_bar_helper_calls == [record.enemy]
    assert dispatch_port.events == [published_output]
    assert schedule_data.event_list == []
    assert listener_calls == []
    assert active_anomaly_bar.settled is False
    assert active_anomaly_bar.settled_calls == 0
    assert spawn_calls == [
        ("mode_number", 2),
        ("polarity_ratio", 0.5),
        ("skill_node", skill_node),
        ("sim_instance", sim_instance),
        ("settled", True),
        ("same_object", False),
        ("marker", "active-anomaly"),
    ]
    assert call_order == ["spawn_output", "publish"]
    assert signal_states == [("spawn_output", True), ("publish", True)]
    assert record.e_counter == {"update_from": "", "count": 0}
    assert record.polarity_disorder_update_signal is False
    assert record.polarity_disorder_basic_dmg_ratio == 0.2


def test_yanagi_polarity_disorder_judge_wrong_skill_is_noop(
    monkeypatch: pytest.MonkeyPatch,
):
    call_order: list[str] = []
    dispatch_port = _RecordingDispatchPort(call_order)
    schedule_data = SimpleNamespace(event_list=_FailFastEventList())
    sim_instance = SimpleNamespace(tick=41, schedule_data=schedule_data)
    buff_instance = SimpleNamespace(
        sim_instance=sim_instance,
        ft=SimpleNamespace(index="yanagi-trigger"),
    )
    logic = YanagiPolarityDisorderTrigger(
        buff_instance,
        scheduled_event_emitter_provider=ScheduledEventEmitterProvider(lambda: dispatch_port),
    )
    record = YanagiPolarityDisorderTriggerRecord()
    record.char = SimpleNamespace(cinema=2)
    dynamic = _DynamicReadProbe(is_active=True)
    record.enemy = SimpleNamespace(dynamic=dynamic)
    record.e_counter = {"update_from": "prev-hit", "count": 2}

    def fail_read_enemy_anomaly_active(enemy: object) -> bool:
        raise AssertionError("Yanagi no-op branch should not read anomaly-active helper")

    monkeypatch.setattr(logic, "check_record_module", lambda: setattr(logic, "record", record))
    monkeypatch.setattr(logic, "get_prepared", lambda **kwargs: None)
    monkeypatch.setattr(
        yanagi_module,
        "read_enemy_anomaly_active",
        fail_read_enemy_anomaly_active,
    )
    monkeypatch.setattr(yanagi_module, "find_tick", lambda *, sim_instance: sim_instance.tick)
    _patch_runtime_boundary_guards(monkeypatch)
    _block_legacy_event_lookup(monkeypatch)

    assert logic.special_judge_logic(skill_node=_build_skill_node(skill_tag="1221_NA_A")) is False

    assert dynamic.calls == []
    assert logic.record is record
    assert call_order == []
    assert dispatch_port.events == []
    assert schedule_data.event_list == []
    assert record.e_counter == {"update_from": "prev-hit", "count": 2}
    assert record.polarity_disorder_update_signal is False


def test_yanagi_polarity_disorder_judge_resets_counter_without_publish_when_no_anomaly(
    monkeypatch: pytest.MonkeyPatch,
):
    call_order: list[str] = []
    dispatch_port = _RecordingDispatchPort(call_order)
    schedule_data = SimpleNamespace(event_list=_FailFastEventList())
    sim_instance = SimpleNamespace(tick=41, schedule_data=schedule_data)
    buff_instance = SimpleNamespace(
        sim_instance=sim_instance,
        ft=SimpleNamespace(index="yanagi-trigger"),
    )
    logic = YanagiPolarityDisorderTrigger(
        buff_instance,
        scheduled_event_emitter_provider=ScheduledEventEmitterProvider(lambda: dispatch_port),
    )
    record = YanagiPolarityDisorderTriggerRecord()
    record.char = SimpleNamespace(cinema=2)
    dynamic = _DynamicReadProbe(is_active=False)
    record.enemy = SimpleNamespace(dynamic=dynamic)
    record.e_counter = {"update_from": "prev-hit", "count": 2}
    helper_calls: list[object] = []

    def fake_read_enemy_anomaly_active(enemy: Any) -> bool:
        helper_calls.append(enemy)
        return bool(enemy.dynamic.is_under_anomaly())

    monkeypatch.setattr(logic, "check_record_module", lambda: setattr(logic, "record", record))
    monkeypatch.setattr(logic, "get_prepared", lambda **kwargs: None)
    monkeypatch.setattr(
        yanagi_module,
        "read_enemy_anomaly_active",
        fake_read_enemy_anomaly_active,
    )
    monkeypatch.setattr(yanagi_module, "find_tick", lambda *, sim_instance: sim_instance.tick)
    _patch_runtime_boundary_guards(monkeypatch)
    _block_legacy_event_lookup(monkeypatch)

    skill_node = _build_skill_node()
    loading_mission = LoadingMission(skill_node)
    loading_mission.mission_start(skill_node.preload_tick, report=False)

    assert logic.special_judge_logic(skill_node=cast(Any, loading_mission)) is False
    assert helper_calls == [record.enemy]
    assert dynamic.calls == ["is_under_anomaly"]
    assert logic.record is record
    assert call_order == []
    assert dispatch_port.events == []
    assert schedule_data.event_list == []
    assert record.e_counter == {"update_from": "", "count": 0}
    assert record.polarity_disorder_update_signal is False
