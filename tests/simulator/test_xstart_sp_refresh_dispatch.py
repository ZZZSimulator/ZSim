from __future__ import annotations

import ast
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import pytest

import zsim.define as define_module

sys.modules.setdefault("define", define_module)

from zsim.sim_progress.Buff import JudgeTools
from zsim.sim_progress.Buff.BuffXLogic.ElegantVanitySpRecover import ElegantVanitySpRecover
from zsim.sim_progress.Buff.BuffXLogic.LunarNoviluna import LunarNoviluna
from zsim.sim_progress.Buff.JudgeTools.PreparationContext import (
    ResourceRefreshCommandPort,
)
from zsim.sim_progress.data_struct.schedule_dispatch import (
    ScheduledEventEmitterProvider,
    ScheduleDispatchPort,
)
from zsim.sim_progress.data_struct.sp_update_data import ScheduleRefreshData

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BUFF_XLOGIC_ROOT = PROJECT_ROOT / "zsim" / "sim_progress" / "Buff" / "BuffXLogic"
XSTART_RESOURCE_REFRESH_FILES = (
    BUFF_XLOGIC_ROOT / "ElegantVanitySpRecover.py",
    BUFF_XLOGIC_ROOT / "LunarNoviluna.py",
)


class _FailFastEventList(list):
    def append(self, item):
        raise AssertionError("xstart SP refresh producer should publish via dispatch port")


class _RecordingDispatchPort(ScheduleDispatchPort):
    def __init__(self, call_order: list[str]) -> None:
        self.events: list[object] = []
        self._call_order = call_order

    def publish_scheduled(self, event: object) -> None:
        self._call_order.append("publish")
        self.events.append(event)


def _block_legacy_event_lookup(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_find_event_list(*args, **kwargs):
        raise AssertionError("xstart SP refresh producer should not read raw event_list")

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


def test_xstart_resource_refresh_files_do_not_directly_construct_schedule_refresh_data() -> None:
    findings = [
        finding
        for path in XSTART_RESOURCE_REFRESH_FILES
        for finding in _direct_schedule_refresh_constructor_findings(path)
    ]

    assert not findings, (
        "Migrated xstart resource-refresh producers directly construct ScheduleRefreshData:\n"
        + "\n".join(f"- {finding}" for finding in findings)
    )


def test_resource_refresh_command_port_publishes_sp_only_payload_via_emitter() -> None:
    call_order: list[str] = []
    dispatch_port = _RecordingDispatchPort(call_order)
    command_port = ResourceRefreshCommandPort(ScheduledEventEmitterProvider(lambda: dispatch_port))

    command_port.publish_refresh(sp_target=("可琳",), sp_value=6)

    assert call_order == ["publish"]
    assert len(dispatch_port.events) == 1
    refresh_data = dispatch_port.events[0]
    assert isinstance(refresh_data, ScheduleRefreshData)
    assert refresh_data.sp_target == ("可琳",)
    assert refresh_data.sp_value == 6
    assert refresh_data.decibel_target == ("",)
    assert refresh_data.decibel_value == 0


def test_resource_refresh_command_port_keeps_schedule_refresh_numeric_validation() -> None:
    command_port = ResourceRefreshCommandPort(
        ScheduledEventEmitterProvider(lambda: _RecordingDispatchPort([]))
    )

    with pytest.raises(TypeError, match="sp_value 必须是数字"):
        command_port.publish_refresh(sp_target=("可琳",), sp_value=object())  # type: ignore[arg-type]


def test_elegant_vanity_sp_recover_publishes_after_simple_start_via_dispatch_port(
    monkeypatch: pytest.MonkeyPatch,
):
    call_order: list[str] = []
    dispatch_port = _RecordingDispatchPort(call_order)
    sim_instance = SimpleNamespace(
        tick=27, schedule_data=SimpleNamespace(event_list=_FailFastEventList())
    )
    buff_instance = SimpleNamespace(
        sim_instance=sim_instance,
        ft=SimpleNamespace(refinement="3"),
    )
    logic = ElegantVanitySpRecover(
        buff_instance,
        scheduled_event_emitter_provider=ScheduledEventEmitterProvider(lambda: dispatch_port),
    )
    sub_exist_buff_dict = {"EV": object()}
    record = SimpleNamespace(
        sub_exist_buff_dict=sub_exist_buff_dict,
        energy_value_dict={1: 5, 2: 5.5, 3: 6, 4: 6.5, 5: 7},
        char=SimpleNamespace(NAME="可琳"),
    )
    monkeypatch.setattr(logic, "check_record_module", lambda: setattr(logic, "record", record))
    monkeypatch.setattr(logic, "get_prepared", lambda **kwargs: None)
    _block_legacy_event_lookup(monkeypatch)

    def fake_simple_start(tick_now, target_sub_exist_buff_dict):
        call_order.append("simple_start")
        assert tick_now == 27
        assert target_sub_exist_buff_dict is sub_exist_buff_dict

    cast(Any, buff_instance).simple_start = fake_simple_start

    logic.special_start_logic()

    assert call_order == ["simple_start", "publish"]
    assert len(dispatch_port.events) == 1
    refresh_data = dispatch_port.events[0]
    assert isinstance(refresh_data, ScheduleRefreshData)
    assert refresh_data.sp_target == ("可琳",)
    assert refresh_data.sp_value == 6
    assert refresh_data.decibel_target == ("",)
    assert refresh_data.decibel_value == 0
    assert sim_instance.schedule_data.event_list == []


def test_lunar_noviluna_preserves_publish_then_simple_start_order_via_dispatch_port(
    monkeypatch: pytest.MonkeyPatch,
):
    call_order: list[str] = []
    dispatch_port = _RecordingDispatchPort(call_order)
    sim_instance = SimpleNamespace(
        tick=31, schedule_data=SimpleNamespace(event_list=_FailFastEventList())
    )
    buff_instance = SimpleNamespace(
        sim_instance=sim_instance,
        ft=SimpleNamespace(refinement=4),
    )
    logic = LunarNoviluna(
        buff_instance,
        scheduled_event_emitter_provider=ScheduledEventEmitterProvider(lambda: dispatch_port),
    )
    sub_exist_buff_dict = {"LN": object()}
    record = SimpleNamespace(
        sub_exist_buff_dict=sub_exist_buff_dict,
        enegy_value_map={1: 3, 2: 3.5, 3: 4, 4: 4.5, 5: 5},
        char=SimpleNamespace(NAME="露娜"),
    )
    monkeypatch.setattr(logic, "check_record_module", lambda: setattr(logic, "record", record))
    monkeypatch.setattr(logic, "get_prepared", lambda **kwargs: None)
    _block_legacy_event_lookup(monkeypatch)

    def fake_simple_start(tick_now, target_sub_exist_buff_dict):
        call_order.append("simple_start")
        assert tick_now == 31
        assert target_sub_exist_buff_dict is sub_exist_buff_dict

    cast(Any, buff_instance).simple_start = fake_simple_start

    logic.special_start_logic()

    assert len(dispatch_port.events) == 1
    refresh_data = dispatch_port.events[0]
    assert isinstance(refresh_data, ScheduleRefreshData)
    assert refresh_data.sp_target == ("露娜",)
    assert refresh_data.sp_value == 4.5
    assert refresh_data.decibel_target == ("",)
    assert refresh_data.decibel_value == 0
    assert call_order == ["publish", "simple_start"]
    assert sim_instance.schedule_data.event_list == []
