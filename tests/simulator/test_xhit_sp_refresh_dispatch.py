from __future__ import annotations

import ast
import sys
from collections.abc import Callable
from pathlib import Path
from types import SimpleNamespace

import pytest

import zsim.define as define_module

sys.modules.setdefault("define", define_module)

import zsim.sim_progress.Buff.BuffXLogic.SeedAdditionalAbilityTrigger as seed_module
from zsim.sim_progress.Buff import JudgeTools
from zsim.sim_progress.Buff.BuffXLogic.MagneticStormCharlieSpRecover import (
    MagneticStormCharlieSpRecover,
)
from zsim.sim_progress.Buff.BuffXLogic.SeedAdditionalAbilityTrigger import (
    SeedAdditionalAbilityTrigger,
    SeedAdditionalAbilityTriggerRecord,
)
from zsim.sim_progress.data_struct.schedule_dispatch import (
    ScheduledEventEmitterProvider,
    ScheduleDispatchPort,
)
from zsim.sim_progress.data_struct.sp_update_data import ScheduleRefreshData

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BUFF_XLOGIC_ROOT = PROJECT_ROOT / "zsim" / "sim_progress" / "Buff" / "BuffXLogic"
XHIT_RESOURCE_REFRESH_FILES = (
    BUFF_XLOGIC_ROOT / "MagneticStormCharlieSpRecover.py",
    BUFF_XLOGIC_ROOT / "SeedAdditionalAbilityTrigger.py",
)


class _FailFastEventList(list):
    def append(self, item):
        raise AssertionError("xhit SP refresh producer should publish via dispatch port")


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
        if self._on_publish is not None:
            self._on_publish(event)
        self.events.append(event)


def _block_legacy_event_lookup(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_find_event_list(*args, **kwargs):
        raise AssertionError("xhit SP refresh producer should not read raw event_list")

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


def test_xhit_resource_refresh_files_do_not_directly_construct_schedule_refresh_data() -> None:
    findings = [
        finding
        for path in XHIT_RESOURCE_REFRESH_FILES
        for finding in _direct_schedule_refresh_constructor_findings(path)
    ]

    assert not findings, (
        "Migrated xhit resource-refresh producers directly construct ScheduleRefreshData:\n"
        + "\n".join(f"- {finding}" for finding in findings)
    )


def test_magnetic_storm_charlie_sp_recover_publishes_after_simple_start_via_dispatch_port(
    monkeypatch: pytest.MonkeyPatch,
):
    call_order: list[str] = []
    dispatch_port = _RecordingDispatchPort(call_order)
    sim_instance = SimpleNamespace(
        tick=42,
        schedule_data=SimpleNamespace(event_list=_FailFastEventList()),
    )
    buff_instance = SimpleNamespace(
        sim_instance=sim_instance,
        ft=SimpleNamespace(refinement="5"),
    )
    logic = MagneticStormCharlieSpRecover(
        buff_instance,
        scheduled_event_emitter_provider=ScheduledEventEmitterProvider(lambda: dispatch_port),
    )
    sub_exist_buff_dict = {"MSC": object()}
    record = SimpleNamespace(
        sub_exist_buff_dict=sub_exist_buff_dict,
        energy_value_dict={1: 3.5, 2: 4, 3: 4.5, 4: 5, 5: 5.5},
        char=SimpleNamespace(NAME="青衣"),
    )
    monkeypatch.setattr(logic, "check_record_module", lambda: setattr(logic, "record", record))
    monkeypatch.setattr(logic, "get_prepared", lambda **kwargs: None)
    _block_legacy_event_lookup(monkeypatch)

    def fake_simple_start(tick_now, target_sub_exist_buff_dict):
        call_order.append("simple_start")
        assert tick_now == 42
        assert target_sub_exist_buff_dict is sub_exist_buff_dict

    buff_instance.simple_start = fake_simple_start

    logic.special_hit_logic()

    assert call_order == ["simple_start", "publish"]
    assert len(dispatch_port.events) == 1
    refresh_data = dispatch_port.events[0]
    assert isinstance(refresh_data, ScheduleRefreshData)
    assert refresh_data.sp_target == ("青衣",)
    assert refresh_data.sp_value == 5.5
    assert refresh_data.decibel_target == ("",)
    assert refresh_data.decibel_value == 0
    assert sim_instance.schedule_data.event_list == []


def test_seed_additional_ability_trigger_publishes_for_vanguard_via_dispatch_port(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
):
    call_order: list[str] = []
    schedule_data = SimpleNamespace(
        event_list=_FailFastEventList(),
        change_process_state=lambda: call_order.append("change_process_state"),
    )
    sim_instance = SimpleNamespace(
        tick=73,
        schedule_data=schedule_data,
    )
    buff_instance = SimpleNamespace(
        sim_instance=sim_instance,
        ft=SimpleNamespace(index="seed-trigger"),
    )
    record = SeedAdditionalAbilityTriggerRecord()
    record.char = SimpleNamespace(
        NAME="席德",
        vanguard=SimpleNamespace(NAME="柯蕾妲"),
    )

    def assert_record_not_updated_at_publish(event: object) -> None:
        assert isinstance(event, ScheduleRefreshData)
        assert record.last_active_tick == 0

    dispatch_port = _RecordingDispatchPort(
        call_order,
        on_publish=assert_record_not_updated_at_publish,
    )
    logic = SeedAdditionalAbilityTrigger(
        buff_instance,
        scheduled_event_emitter_provider=ScheduledEventEmitterProvider(lambda: dispatch_port),
    )
    monkeypatch.setattr(logic, "check_record_module", lambda: setattr(logic, "record", record))
    monkeypatch.setattr(logic, "get_prepared", lambda **kwargs: None)
    monkeypatch.setattr(seed_module, "SEED_REPORT", True)
    _block_legacy_event_lookup(monkeypatch)

    logic.special_hit_logic()

    assert call_order == ["publish", "change_process_state"]
    assert len(dispatch_port.events) == 1
    refresh_data = dispatch_port.events[0]
    assert isinstance(refresh_data, ScheduleRefreshData)
    assert refresh_data.sp_target == ("柯蕾妲",)
    assert refresh_data.sp_value == 2
    assert refresh_data.decibel_target == ("",)
    assert refresh_data.decibel_value == 0
    assert record.last_active_tick == 73
    assert sim_instance.schedule_data.event_list == []
    assert "【席德事件】额外能力触发" in capsys.readouterr().out
