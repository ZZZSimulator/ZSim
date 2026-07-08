from __future__ import annotations

import ast
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

import zsim.define as define_module

sys.modules.setdefault("define", define_module)

import zsim.sim_progress.Buff.BuffXLogic.SliceofTimeExtraResources as slice_module
from zsim.sim_progress.Buff import JudgeTools
from zsim.sim_progress.Buff.BuffXLogic.SliceofTimeExtraResources import (
    SliceofTimeExtraResources,
    SliceofTimeExtraResourcesRecord,
)
from zsim.sim_progress.Buff.JudgeTools.PreparationContext import (
    ResourceRefreshCommandPort,
)
from zsim.sim_progress.data_struct.schedule_dispatch import (
    ScheduledEventEmitterProvider,
    ScheduleDispatchPort,
)
from zsim.sim_progress.data_struct.sp_update_data import ScheduleRefreshData

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SLICE_OF_TIME_RESOURCE_REFRESH_FILE = Path(slice_module.__file__).resolve()


class _FailFastEventList(list):
    def append(self, item):
        raise AssertionError(
            "SliceofTimeExtraResources should publish combined refresh data via dispatch port"
        )


class _RecordingDispatchPort(ScheduleDispatchPort):
    def __init__(self, call_order: list[str]) -> None:
        self.events: list[object] = []
        self._call_order = call_order

    def publish_scheduled(self, event: object) -> None:
        self._call_order.append("publish")
        self.events.append(event)


def _block_legacy_event_lookup(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_find_event_list(*args, **kwargs):
        raise AssertionError("SliceofTimeExtraResources should not read raw event_list")

    monkeypatch.setattr(JudgeTools, "find_event_list", fail_find_event_list, raising=False)


def _schedule_refresh_constructor_names(tree: ast.AST) -> set[str]:
    constructor_names = {"ScheduleRefreshData"}
    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom):
            continue
        for alias in node.names:
            if alias.name == "ScheduleRefreshData":
                constructor_names.add(alias.asname or alias.name)
    return constructor_names


def _direct_schedule_refresh_constructor_findings(path: Path) -> list[str]:
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    constructor_names = _schedule_refresh_constructor_names(tree)
    findings: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if isinstance(node.func, ast.Name) and node.func.id in constructor_names:
            findings.append(f"{path.relative_to(PROJECT_ROOT).as_posix()}:{node.lineno}")
        if isinstance(node.func, ast.Attribute) and node.func.attr == "ScheduleRefreshData":
            findings.append(f"{path.relative_to(PROJECT_ROOT).as_posix()}:{node.lineno}")
    return findings


def test_slice_of_time_extra_resources_does_not_directly_construct_schedule_refresh_data() -> None:
    findings = _direct_schedule_refresh_constructor_findings(SLICE_OF_TIME_RESOURCE_REFRESH_FILE)

    assert not findings, (
        "Migrated SliceofTimeExtraResources directly constructs ScheduleRefreshData:\n"
        + "\n".join(f"- {finding}" for finding in findings)
    )


def test_resource_refresh_command_port_publishes_mixed_refresh_at_call_site() -> None:
    call_order: list[str] = ["before_publish_call"]
    dispatch_port = _RecordingDispatchPort(call_order)
    command_port = ResourceRefreshCommandPort(ScheduledEventEmitterProvider(lambda: dispatch_port))
    unused_raw_queue = _FailFastEventList()

    command_port.publish_refresh(
        sp_target=("support",),
        sp_value=1.0,
        decibel_target=("actor",),
        decibel_value=50,
    )
    call_order.append("after_publish_call")

    assert call_order == ["before_publish_call", "publish", "after_publish_call"]
    assert unused_raw_queue == []
    assert len(dispatch_port.events) == 1
    refresh_data = dispatch_port.events[0]
    assert isinstance(refresh_data, ScheduleRefreshData)
    assert refresh_data.sp_target == ("support",)
    assert refresh_data.sp_value == 1.0
    assert refresh_data.decibel_target == ("actor",)
    assert refresh_data.decibel_value == 50


def test_slice_of_time_extra_resources_publishes_mixed_refresh_via_dispatch_port(
    monkeypatch: pytest.MonkeyPatch,
):
    call_order: list[str] = []
    dispatch_port = _RecordingDispatchPort(call_order)
    sim_instance = SimpleNamespace(
        tick=91,
        schedule_data=SimpleNamespace(event_list=_FailFastEventList()),
    )
    buff_instance = SimpleNamespace(
        sim_instance=sim_instance,
        ft=SimpleNamespace(refinement=4),
    )
    logic = SliceofTimeExtraResources(
        buff_instance,
        scheduled_event_emitter_provider=ScheduledEventEmitterProvider(lambda: dispatch_port),
    )
    sub_exist_buff_dict = {"slice": object()}
    action_now = SimpleNamespace(
        mission_node=SimpleNamespace(skill=SimpleNamespace(trigger_buff_level=5)),
        mission_character="actor",
    )
    record = SliceofTimeExtraResourcesRecord()
    record.char = SimpleNamespace(NAME="support")
    record.sub_exist_buff_dict = sub_exist_buff_dict
    record.action_stack = SimpleNamespace(peek=lambda: action_now)
    monkeypatch.setattr(logic, "check_record_module", lambda: setattr(logic, "record", record))
    monkeypatch.setattr(logic, "get_prepared", lambda **kwargs: None)
    _block_legacy_event_lookup(monkeypatch)

    def fake_simple_start(tick_now, target_sub_exist_buff_dict):
        call_order.append("simple_start")
        assert tick_now == 91
        assert target_sub_exist_buff_dict is sub_exist_buff_dict

    buff_instance.simple_start = fake_simple_start

    logic.special_start_logic()

    assert call_order == ["simple_start", "publish"]
    assert len(dispatch_port.events) == 1
    refresh_data = dispatch_port.events[0]
    assert isinstance(refresh_data, ScheduleRefreshData)
    assert refresh_data.sp_target == ("support",)
    assert refresh_data.sp_value == 1.0
    assert refresh_data.decibel_target == ("actor",)
    assert refresh_data.decibel_value == 50
    assert sim_instance.schedule_data.event_list == []
