from __future__ import annotations

import sys
from types import SimpleNamespace
from typing import Any

import pytest

import zsim.define as define_module
import zsim.sim_progress.ScheduledEvent as scheduled_event_module
import zsim.sim_progress.ScheduledEvent.buff_runtime as buff_runtime_module
import zsim.sim_progress.ScheduledEvent.runtime_command as runtime_command_module

sys.modules.setdefault("define", define_module)

import zsim.sim_progress.Buff.BuffXLogic.VivianCorePassiveTrigger as trigger_module
from zsim.sim_progress.anomaly_bar import AnomalyBar
from zsim.sim_progress.anomaly_bar.CopyAnomalyForOutput import DirgeOfDestinyAnomaly
from zsim.sim_progress.Buff import JudgeTools
from zsim.sim_progress.Buff.BuffXLogic.VivianCorePassiveTrigger import (
    VivianCorePassiveTrigger,
    VivianCorePassiveTriggerRecord,
)
from zsim.sim_progress.data_struct.schedule_dispatch import (
    ScheduledEventEmitterProvider,
    ScheduleDispatchPort,
)
from zsim.sim_progress.Preload import SkillNode


class _FailFastEventList(list):
    def append(self, item):
        raise AssertionError("VivianCorePassiveTrigger should publish via dispatch port")


class _RecordingDispatchPort(ScheduleDispatchPort):
    def __init__(self, action_log: list[str] | None = None) -> None:
        self.events: list[object] = []
        self.action_log = action_log

    def publish_scheduled(self, event: object) -> None:
        if self.action_log is not None:
            self.action_log.append("publish_scheduled")
        self.events.append(event)


class _RecordingReaderService:
    def __init__(self, *, ap: float) -> None:
        self.ap = ap
        self.contexts: list[object] = []

    def read_anomaly_proficiency(self, context: object) -> float:
        self.contexts.append(context)
        return self.ap


class _DynamicReadProbe:
    def __init__(self, active_anomalies: list[AnomalyBar]) -> None:
        self.active_anomalies = active_anomalies
        self.calls: list[str] = []

    def is_under_anomaly(self) -> bool:
        self.calls.append("is_under_anomaly")
        return bool(self.active_anomalies)

    def get_active_anomaly(self) -> list[AnomalyBar]:
        self.calls.append("get_active_anomaly")
        return self.active_anomalies


def _patch_anomaly_helper(monkeypatch: pytest.MonkeyPatch) -> list[object]:
    helper_calls: list[object] = []

    def fake_read_enemy_anomaly_active(enemy: Any) -> bool:
        helper_calls.append(enemy)
        return bool(enemy.dynamic.is_under_anomaly())

    monkeypatch.setattr(
        trigger_module,
        "read_enemy_anomaly_active",
        fake_read_enemy_anomaly_active,
    )
    return helper_calls


def _patch_active_anomaly_list_helper(monkeypatch: pytest.MonkeyPatch) -> list[object]:
    helper_calls: list[object] = []

    def fake_read_enemy_active_anomaly_list(enemy: Any) -> list[AnomalyBar]:
        helper_calls.append(enemy)
        return enemy.dynamic.get_active_anomaly()

    monkeypatch.setattr(
        trigger_module,
        "read_enemy_active_anomaly_list",
        fake_read_enemy_active_anomaly_list,
    )
    return helper_calls


def _block_anomaly_helper(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_read_enemy_anomaly_active(enemy: object) -> bool:
        raise AssertionError("VivianCorePassiveTrigger xeffect should own active anomaly reads")

    monkeypatch.setattr(
        trigger_module,
        "read_enemy_anomaly_active",
        fail_read_enemy_anomaly_active,
    )


def _block_legacy_event_lookup(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_find_event_list(*args, **kwargs):
        raise AssertionError("VivianCorePassiveTrigger should not read raw event_list")

    monkeypatch.setattr(JudgeTools, "find_event_list", fail_find_event_list, raising=False)


def _patch_runtime_boundary_guards(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_create_runtime_command_port(*args: object, **kwargs: object) -> None:
        raise AssertionError("VivianCorePassiveTrigger should not create RuntimeCommandPort")

    def fail_create_buff_runtime_read_port(*args: object, **kwargs: object) -> None:
        raise AssertionError("VivianCorePassiveTrigger should not create BuffRuntimeReadPort")

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


def _patch_calculator_reader_service(
    monkeypatch: pytest.MonkeyPatch,
    *,
    ap: float,
) -> tuple[object, list[dict[str, object]], _RecordingReaderService]:
    context = object()
    context_calls: list[dict[str, object]] = []
    reader_service = _RecordingReaderService(ap=ap)

    def fake_create_context(**kwargs: object) -> object:
        context_calls.append(kwargs)
        return context

    monkeypatch.setattr(
        trigger_module,
        "create_calculator_runtime_read_context_from_sim_instance",
        fake_create_context,
    )
    monkeypatch.setattr(
        trigger_module,
        "get_calculator_buff_attribute_reader_service",
        lambda: reader_service,
    )
    return context, context_calls, reader_service


def _build_active_anomaly(*, sim_instance: object) -> AnomalyBar:
    anomaly_bar = AnomalyBar.__new__(AnomalyBar)
    anomaly_bar.sim_instance = sim_instance
    anomaly_bar.element_type = 3
    anomaly_bar.settled = False
    anomaly_bar.settled_calls = 0
    anomaly_bar.marker = "active-anomaly"
    anomaly_bar.activated_by = None
    return anomaly_bar


def _build_skill_node(
    *,
    uuid: str = "vivian-core-node",
    skill_tag: str = "1331_CoAttack_A",
) -> SkillNode:
    skill_node = SkillNode.__new__(SkillNode)
    skill_node.skill_tag = skill_tag
    skill_node.UUID = uuid
    return skill_node


def test_vivian_core_passive_publishes_dirge_anomaly_via_dispatch_port(
    monkeypatch: pytest.MonkeyPatch,
):
    action_log: list[str] = []
    listener_calls: list[tuple[tuple[object, ...], dict[str, object]]] = []

    def fail_listener_broadcast(*args: object, **kwargs: object) -> None:
        listener_calls.append((args, kwargs))
        raise AssertionError("VivianCorePassiveTrigger should not broadcast listener events")

    dispatch_port = _RecordingDispatchPort(action_log=action_log)

    def change_process_state() -> None:
        action_log.append("change_process_state")

    schedule_data = SimpleNamespace(
        event_list=_FailFastEventList(),
        change_process_state=change_process_state,
    )
    char = SimpleNamespace(NAME="\u8587\u8587\u5b89", cinema=2)
    sim_instance = SimpleNamespace(
        schedule_data=schedule_data,
        listener_manager=SimpleNamespace(broadcast_event=fail_listener_broadcast),
        char_data=SimpleNamespace(
            find_char_obj=lambda CID: char if CID == 1331 else None,
        ),
    )
    active_anomaly = _build_active_anomaly(sim_instance=sim_instance)
    dynamic = _DynamicReadProbe([active_anomaly])
    enemy = SimpleNamespace(sim_instance=sim_instance, dynamic=dynamic)
    buff_instance = SimpleNamespace(
        sim_instance=sim_instance,
        ft=SimpleNamespace(index="vivian-core-passive"),
    )
    dispatch_factory_calls: list[object] = []

    def create_dispatch_port() -> _RecordingDispatchPort:
        dispatch_factory_calls.append(sim_instance)
        return dispatch_port

    logic = VivianCorePassiveTrigger(
        buff_instance,
        scheduled_event_emitter_provider=ScheduledEventEmitterProvider(create_dispatch_port),
    )
    record = VivianCorePassiveTriggerRecord()
    record.char = char
    record.enemy = enemy
    monkeypatch.setattr(logic, "check_record_module", lambda: setattr(logic, "record", record))
    monkeypatch.setattr(logic, "get_prepared", lambda **kwargs: None)
    monkeypatch.setattr(trigger_module, "VIVIAN_REPORT", True)
    monkeypatch.setattr("builtins.print", lambda *args, **kwargs: None)
    _block_anomaly_helper(monkeypatch)
    active_list_helper_calls = _patch_active_anomaly_list_helper(monkeypatch)
    _patch_runtime_boundary_guards(monkeypatch)
    _block_legacy_event_lookup(monkeypatch)

    def fake_anomaly_settled(self: AnomalyBar) -> None:
        self.settled = True
        self.settled_calls = getattr(self, "settled_calls", 0) + 1

    monkeypatch.setattr(AnomalyBar, "anomaly_settled", fake_anomaly_settled)
    reader_context, context_calls, reader_service = _patch_calculator_reader_service(
        monkeypatch,
        ap=250.0,
    )

    assert dispatch_factory_calls == []

    logic.special_effect_logic()

    assert len(dispatch_port.events) == 1
    assert dispatch_factory_calls == [sim_instance]
    assert active_list_helper_calls == [enemy]
    assert dynamic.calls == ["get_active_anomaly"]
    assert action_log == ["publish_scheduled", "change_process_state"]
    assert listener_calls == []
    published_event = dispatch_port.events[0]
    assert isinstance(published_event, DirgeOfDestinyAnomaly)
    assert published_event is not active_anomaly
    assert published_event.marker == "active-anomaly"
    assert published_event.element_type == 3
    assert published_event.settled is True
    assert published_event.settled_calls == 1
    assert published_event.sim_instance is sim_instance
    assert published_event.activated_by.char_name == "\u8587\u8587\u5b89"
    assert published_event.activated_by.skill_tag == "1331"
    assert published_event.anomaly_dmg_ratio == pytest.approx(1.04)
    assert record.cinema_ratio == 1.3
    assert active_anomaly.settled is False
    assert active_anomaly.settled_calls == 0
    assert schedule_data.event_list == []
    assert context_calls == [
        {
            "sim_instance": sim_instance,
            "enemy": enemy,
            "character": char,
        }
    ]
    assert reader_service.contexts == [reader_context]


def test_vivian_core_passive_judge_wrong_skill_is_noop(
    monkeypatch: pytest.MonkeyPatch,
):
    dispatch_port = _RecordingDispatchPort()
    schedule_data = SimpleNamespace(
        event_list=_FailFastEventList(),
        change_process_state=lambda: None,
    )
    sim_instance = SimpleNamespace(schedule_data=schedule_data)
    active_anomaly = _build_active_anomaly(sim_instance=sim_instance)
    dynamic = _DynamicReadProbe([active_anomaly])
    enemy = SimpleNamespace(sim_instance=sim_instance, dynamic=dynamic)
    buff_instance = SimpleNamespace(
        sim_instance=sim_instance,
        ft=SimpleNamespace(index="vivian-core-passive"),
    )
    logic = VivianCorePassiveTrigger(
        buff_instance,
        scheduled_event_emitter_provider=ScheduledEventEmitterProvider(lambda: dispatch_port),
    )
    record = VivianCorePassiveTriggerRecord()
    record.enemy = enemy
    monkeypatch.setattr(logic, "check_record_module", lambda: setattr(logic, "record", record))
    monkeypatch.setattr(logic, "get_prepared", lambda **kwargs: None)
    helper_calls = _patch_anomaly_helper(monkeypatch)
    _patch_runtime_boundary_guards(monkeypatch)
    _block_legacy_event_lookup(monkeypatch)

    assert logic.special_judge_logic(skill_node=_build_skill_node(skill_tag="1331_SNA_2")) is False

    assert dynamic.calls == []
    assert helper_calls == []
    assert record.last_update_node is None
    assert dispatch_port.events == []
    assert schedule_data.event_list == []


def test_vivian_core_passive_judge_no_anomaly_does_not_publish_or_update_node(
    monkeypatch: pytest.MonkeyPatch,
):
    dispatch_port = _RecordingDispatchPort()
    schedule_data = SimpleNamespace(
        event_list=_FailFastEventList(),
        change_process_state=lambda: None,
    )
    sim_instance = SimpleNamespace(schedule_data=schedule_data)
    dynamic = _DynamicReadProbe([])
    enemy = SimpleNamespace(sim_instance=sim_instance, dynamic=dynamic)
    buff_instance = SimpleNamespace(
        sim_instance=sim_instance,
        ft=SimpleNamespace(index="vivian-core-passive"),
    )
    logic = VivianCorePassiveTrigger(
        buff_instance,
        scheduled_event_emitter_provider=ScheduledEventEmitterProvider(lambda: dispatch_port),
    )
    record = VivianCorePassiveTriggerRecord()
    record.enemy = enemy
    monkeypatch.setattr(logic, "check_record_module", lambda: setattr(logic, "record", record))
    monkeypatch.setattr(logic, "get_prepared", lambda **kwargs: None)
    helper_calls = _patch_anomaly_helper(monkeypatch)
    _patch_runtime_boundary_guards(monkeypatch)
    _block_legacy_event_lookup(monkeypatch)

    assert logic.special_judge_logic(skill_node=_build_skill_node()) is False

    assert helper_calls == [enemy]
    assert dynamic.calls == ["is_under_anomaly"]
    assert record.last_update_node is None
    assert dispatch_port.events == []
    assert schedule_data.event_list == []


def test_vivian_core_passive_judge_active_anomaly_updates_node_once(
    monkeypatch: pytest.MonkeyPatch,
):
    schedule_data = SimpleNamespace(
        event_list=_FailFastEventList(),
        change_process_state=lambda: None,
    )
    sim_instance = SimpleNamespace(schedule_data=schedule_data)
    active_anomaly = _build_active_anomaly(sim_instance=sim_instance)
    dynamic = _DynamicReadProbe([active_anomaly])
    enemy = SimpleNamespace(sim_instance=sim_instance, dynamic=dynamic)
    buff_instance = SimpleNamespace(
        sim_instance=sim_instance,
        ft=SimpleNamespace(index="vivian-core-passive"),
    )
    logic = VivianCorePassiveTrigger(buff_instance)
    record = VivianCorePassiveTriggerRecord()
    record.enemy = enemy
    monkeypatch.setattr(logic, "check_record_module", lambda: setattr(logic, "record", record))
    monkeypatch.setattr(logic, "get_prepared", lambda **kwargs: None)
    helper_calls = _patch_anomaly_helper(monkeypatch)
    _patch_runtime_boundary_guards(monkeypatch)
    _block_legacy_event_lookup(monkeypatch)

    skill_node = _build_skill_node()

    assert logic.special_judge_logic(skill_node=skill_node) is True
    assert logic.special_judge_logic(skill_node=skill_node) is False

    assert helper_calls == [enemy, enemy]
    assert dynamic.calls == ["is_under_anomaly", "is_under_anomaly"]
    assert record.last_update_node is skill_node
    assert schedule_data.event_list == []
