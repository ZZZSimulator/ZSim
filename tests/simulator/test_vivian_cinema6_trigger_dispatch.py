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

import zsim.sim_progress.Buff.BuffXLogic.VivianCinema6Trigger as trigger_module
from zsim.sim_progress.anomaly_bar import AnomalyBar
from zsim.sim_progress.anomaly_bar.CopyAnomalyForOutput import DirgeOfDestinyAnomaly
from zsim.sim_progress.Buff import JudgeTools
from zsim.sim_progress.Buff.BuffXLogic.VivianCinema6Trigger import (
    VivianCinema6Trigger,
    VivianCinema6TriggerRecord,
)
from zsim.sim_progress.data_struct.schedule_dispatch import (
    ScheduledEventEmitterProvider,
    ScheduleDispatchPort,
)
from zsim.sim_progress.Preload import SkillNode


class _FailFastEventList(list):
    def append(self, item):
        raise AssertionError("VivianCinema6Trigger should publish via dispatch port")


class _RecordingDispatchPort(ScheduleDispatchPort):
    def __init__(self, action_log: list[tuple[str, object]] | None = None) -> None:
        self.events: list[object] = []
        self.action_log = action_log

    def publish_scheduled(self, event: object) -> None:
        if self.action_log is not None:
            self.action_log.append(("publish_scheduled", event))
        self.events.append(event)


class _FeatherManagerProbe:
    def __init__(
        self,
        *,
        guard_feather: int,
        c1_counter: int,
        flight_feather: int,
        action_log: list[tuple[str, object]],
    ) -> None:
        self._guard_feather = guard_feather
        self._c1_counter = c1_counter
        self._flight_feather = flight_feather
        self.action_log = action_log
        self.mutation_log: list[tuple[str, object]] = []
        self.update_calls: list[bool] = []

    def _record(self, field: str, value: object) -> None:
        entry = (field, value)
        self.mutation_log.append(entry)
        self.action_log.append(entry)

    @property
    def guard_feather(self) -> int:
        return self._guard_feather

    @guard_feather.setter
    def guard_feather(self, value: int) -> None:
        self._record("guard_feather", value)
        self._guard_feather = value

    @property
    def c1_counter(self) -> int:
        return self._c1_counter

    @c1_counter.setter
    def c1_counter(self, value: int) -> None:
        self._record("c1_counter", value)
        self._c1_counter = value

    @property
    def flight_feather(self) -> int:
        return self._flight_feather

    @flight_feather.setter
    def flight_feather(self, value: int) -> None:
        self._record("flight_feather", value)
        self._flight_feather = value

    def update_myself(self, *, c6_signal: bool) -> None:
        self.update_calls.append(c6_signal)
        self.action_log.append(("update_myself", c6_signal))


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
        raise AssertionError("VivianCinema6Trigger xeffect should own active anomaly reads")

    monkeypatch.setattr(
        trigger_module,
        "read_enemy_anomaly_active",
        fail_read_enemy_anomaly_active,
    )


def _block_legacy_event_lookup(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_find_event_list(*args, **kwargs):
        raise AssertionError("VivianCinema6Trigger should not read raw event_list")

    monkeypatch.setattr(JudgeTools, "find_event_list", fail_find_event_list, raising=False)


def _patch_runtime_boundary_guards(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_create_runtime_command_port(*args: object, **kwargs: object) -> None:
        raise AssertionError("VivianCinema6Trigger should not create RuntimeCommandPort")

    def fail_create_buff_runtime_read_port(*args: object, **kwargs: object) -> None:
        raise AssertionError("VivianCinema6Trigger should not create BuffRuntimeReadPort")

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
    anomaly_bar.element_type = 4
    anomaly_bar.settled = False
    anomaly_bar.settled_calls = 0
    anomaly_bar.marker = "c6-active-anomaly"
    anomaly_bar.activated_by = None
    return anomaly_bar


def _build_skill_node(
    *,
    uuid: str = "vivian-cinema6-node",
    skill_tag: str = "1331_SNA_2",
) -> SkillNode:
    skill_node = SkillNode.__new__(SkillNode)
    skill_node.skill_tag = skill_tag
    skill_node.UUID = uuid
    return skill_node


def _build_logic_harness(
    *, active_anomalies: list[AnomalyBar]
) -> tuple[
    VivianCinema6Trigger,
    VivianCinema6TriggerRecord,
    _RecordingDispatchPort,
    SimpleNamespace,
]:
    action_log: list[tuple[str, object]] = []
    dispatch_port = _RecordingDispatchPort(action_log=action_log)
    schedule_data = SimpleNamespace(
        event_list=_FailFastEventList(),
    )

    def change_process_state() -> None:
        action_log.append(("change_process_state", None))

    schedule_data.change_process_state = change_process_state
    feather_manager = _FeatherManagerProbe(
        guard_feather=3,
        c1_counter=1,
        flight_feather=2,
        action_log=action_log,
    )
    char = SimpleNamespace(
        NAME="\u8587\u8587\u5b89",
        cinema=6,
        feather_manager=feather_manager,
        get_special_stats=lambda: {},
    )
    sim_instance = SimpleNamespace(
        schedule_data=schedule_data,
        char_data=SimpleNamespace(
            find_char_obj=lambda CID: char if CID == 1331 else None,
        ),
    )
    listener_calls: list[tuple[tuple[object, ...], dict[str, object]]] = []

    def fail_listener_broadcast(*args: object, **kwargs: object) -> None:
        listener_calls.append((args, kwargs))
        raise AssertionError("VivianCinema6Trigger should not broadcast listener events")

    sim_instance.listener_manager = SimpleNamespace(broadcast_event=fail_listener_broadcast)
    dynamic = _DynamicReadProbe(active_anomalies)
    enemy = SimpleNamespace(sim_instance=sim_instance, dynamic=dynamic)
    buff_instance = SimpleNamespace(
        sim_instance=sim_instance,
        ft=SimpleNamespace(index="vivian-cinema6"),
    )
    emitter_factory_calls: list[object] = []

    def create_dispatch_port() -> _RecordingDispatchPort:
        emitter_factory_calls.append(sim_instance)
        action_log.append(("create_scheduled_event_emitter", sim_instance))
        return dispatch_port

    logic = VivianCinema6Trigger(
        buff_instance,
        scheduled_event_emitter_provider=ScheduledEventEmitterProvider(create_dispatch_port),
    )
    record = VivianCinema6TriggerRecord()
    record.char = char
    record.enemy = enemy
    record.guard_feather = 3
    return (
        logic,
        record,
        dispatch_port,
        SimpleNamespace(
            sim_instance=sim_instance,
            schedule_data=schedule_data,
            char=char,
            feather_manager=feather_manager,
            feather_updates=feather_manager.update_calls,
            action_log=action_log,
            dynamic=dynamic,
            emitter_factory_calls=emitter_factory_calls,
            listener_calls=listener_calls,
        ),
    )


def test_vivian_cinema6_publishes_extra_dirge_anomaly_via_dispatch_port(
    monkeypatch: pytest.MonkeyPatch,
):
    active_anomaly = _build_active_anomaly(sim_instance=SimpleNamespace())
    logic, record, dispatch_port, harness = _build_logic_harness(active_anomalies=[active_anomaly])
    active_anomaly.sim_instance = harness.sim_instance

    monkeypatch.setattr(logic, "check_record_module", lambda: setattr(logic, "record", record))
    monkeypatch.setattr(logic, "get_prepared", lambda **kwargs: None)
    monkeypatch.setattr(trigger_module, "VIVIAN_REPORT", True)
    monkeypatch.setattr("builtins.print", lambda *args, **kwargs: None)
    _patch_runtime_boundary_guards(monkeypatch)
    helper_calls = _patch_anomaly_helper(monkeypatch)
    active_list_helper_calls = _patch_active_anomaly_list_helper(monkeypatch)
    _block_legacy_event_lookup(monkeypatch)

    def fake_anomaly_settled(self: AnomalyBar) -> None:
        self.settled = True
        self.settled_calls = getattr(self, "settled_calls", 0) + 1

    monkeypatch.setattr(AnomalyBar, "anomaly_settled", fake_anomaly_settled)
    reader_context, context_calls, reader_service = _patch_calculator_reader_service(
        monkeypatch,
        ap=250.0,
    )

    skill_node = _build_skill_node()

    assert logic.special_judge_logic(skill_node=skill_node) is True
    assert helper_calls == [record.enemy]
    assert active_list_helper_calls == []
    assert harness.dynamic.calls == ["is_under_anomaly"]
    assert record.last_update_node is skill_node
    assert record.guard_feather == 3
    assert harness.feather_manager.guard_feather == 0
    assert harness.feather_manager.c1_counter == 0
    assert harness.feather_manager.flight_feather == 3
    assert harness.emitter_factory_calls == []
    assert dispatch_port.events == []

    logic.special_effect_logic()

    assert len(dispatch_port.events) == 1
    published_event = dispatch_port.events[0]
    assert helper_calls == [record.enemy]
    assert active_list_helper_calls == [record.enemy]
    assert harness.emitter_factory_calls == [harness.sim_instance]
    assert harness.dynamic.calls == ["is_under_anomaly", "get_active_anomaly"]
    assert [entry[0] for entry in harness.action_log] == [
        "change_process_state",
        "guard_feather",
        "c1_counter",
        "c1_counter",
        "flight_feather",
        "change_process_state",
        "create_scheduled_event_emitter",
        "publish_scheduled",
        "change_process_state",
        "update_myself",
    ]
    assert harness.action_log[6][1] is harness.sim_instance
    assert harness.action_log[7][1] is published_event
    assert harness.listener_calls == []
    assert isinstance(published_event, DirgeOfDestinyAnomaly)
    assert published_event is not active_anomaly
    assert published_event.marker == "c6-active-anomaly"
    assert published_event.element_type == 4
    assert published_event.settled is True
    assert published_event.settled_calls == 1
    assert published_event.sim_instance is logic.buff_instance.sim_instance
    assert published_event.activated_by.char_name == "\u8587\u8587\u5b89"
    assert published_event.activated_by.skill_tag == "1331"
    assert published_event.anomaly_dmg_ratio == pytest.approx(4.797)
    assert record.cinema_ratio == 1.3
    assert record.guard_feather == 0
    assert harness.feather_updates == [True]
    assert active_anomaly.settled is False
    assert active_anomaly.settled_calls == 0
    assert harness.schedule_data.event_list == []
    assert context_calls == [
        {
            "sim_instance": harness.sim_instance,
            "enemy": record.enemy,
            "character": harness.char,
        }
    ]
    assert reader_service.contexts == [reader_context]


def test_vivian_cinema6_judge_wrong_skill_is_noop(
    monkeypatch: pytest.MonkeyPatch,
):
    active_anomaly = _build_active_anomaly(sim_instance=SimpleNamespace())
    logic, record, dispatch_port, harness = _build_logic_harness(active_anomalies=[active_anomaly])

    monkeypatch.setattr(logic, "check_record_module", lambda: setattr(logic, "record", record))
    monkeypatch.setattr(logic, "get_prepared", lambda **kwargs: None)
    monkeypatch.setattr(trigger_module, "VIVIAN_REPORT", False)
    helper_calls = _patch_anomaly_helper(monkeypatch)
    active_list_helper_calls = _patch_active_anomaly_list_helper(monkeypatch)
    _patch_runtime_boundary_guards(monkeypatch)
    _block_legacy_event_lookup(monkeypatch)

    assert (
        logic.special_judge_logic(skill_node=_build_skill_node(skill_tag="1331_CoAttack_A"))
        is False
    )

    assert harness.dynamic.calls == []
    assert helper_calls == []
    assert active_list_helper_calls == []
    assert harness.action_log == []
    assert record.last_update_node is None
    assert dispatch_port.events == []
    assert harness.schedule_data.event_list == []
    assert harness.listener_calls == []


def test_vivian_cinema6_no_anomaly_branch_updates_feathers_without_publish(
    monkeypatch: pytest.MonkeyPatch,
):
    logic, record, dispatch_port, harness = _build_logic_harness(active_anomalies=[])
    record.guard_feather = 4

    monkeypatch.setattr(logic, "check_record_module", lambda: setattr(logic, "record", record))
    monkeypatch.setattr(logic, "get_prepared", lambda **kwargs: None)
    monkeypatch.setattr(trigger_module, "VIVIAN_REPORT", True)
    monkeypatch.setattr("builtins.print", lambda *args, **kwargs: None)
    helper_calls = _patch_anomaly_helper(monkeypatch)
    active_list_helper_calls = _patch_active_anomaly_list_helper(monkeypatch)
    _patch_runtime_boundary_guards(monkeypatch)
    _block_legacy_event_lookup(monkeypatch)

    skill_node = _build_skill_node()

    assert logic.special_judge_logic(skill_node=skill_node) is True
    assert helper_calls == [record.enemy]
    assert active_list_helper_calls == []
    assert harness.dynamic.calls == ["is_under_anomaly"]

    logic.special_effect_logic()

    assert dispatch_port.events == []
    assert harness.schedule_data.event_list == []
    assert helper_calls == [record.enemy]
    assert active_list_helper_calls == [record.enemy]
    assert harness.dynamic.calls == ["is_under_anomaly", "get_active_anomaly"]
    assert [entry[0] for entry in harness.action_log] == [
        "change_process_state",
        "change_process_state",
        "guard_feather",
        "c1_counter",
        "c1_counter",
        "flight_feather",
        "change_process_state",
        "update_myself",
        "change_process_state",
        "update_myself",
    ]
    assert record.guard_feather == 0
    assert harness.feather_updates == [True, True]
