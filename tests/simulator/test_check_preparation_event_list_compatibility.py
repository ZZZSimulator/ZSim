from __future__ import annotations

import ast
import csv
import importlib
import inspect
import json
import textwrap
import tomllib
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

import pytest

import zsim.sim_progress.Buff.JudgeTools as judge_tools
from zsim.sim_progress.Buff.BuffXLogic._buff_record_base_class import BuffRecordBaseClass
from zsim.sim_progress.Buff.BuffXLogic.AliceAdditionalAbilityApBonus import (
    AliceAdditionalAbilityApBonus,
    AliceAdditionalAbilityApBonusRecord,
)
from zsim.sim_progress.Buff.BuffXLogic.WoodpeckerElectroSet4_NA import (
    WoodpeckerElectroSet4_NA,
)
from zsim.sim_progress.ScheduledEvent.buff_runtime import BuffRuntimeState

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BUFF_XLOGIC_ROOT = PROJECT_ROOT / "zsim" / "sim_progress" / "Buff" / "BuffXLogic"
DATA_ROOT = PROJECT_ROOT / "zsim" / "data"
CONFIG_FILES = [
    PROJECT_ROOT / "zsim" / "config.json",
    PROJECT_ROOT / "zsim" / "config_example.json",
]


@dataclass(frozen=True)
class EventListPreparationFinding:
    path: str
    line: int
    expression: str

    def message(self) -> str:
        return (
            f"{self.path}:{self.line}: {self.expression} -> "
            "event_list=True is a deleted legacy discovery surface; migrate planned-event "
            "writers to ScheduleDispatchPort or add an explicit compatibility note"
        )


@dataclass(frozen=True)
class ConfigEventListFinding:
    path: str
    location: str
    value: str

    def message(self) -> str:
        return (
            f"{self.path}:{self.location}: {self.value} -> "
            "Buff data/config must not request check_preparation(event_list=True)"
        )


def _relative_path(path: Path) -> str:
    return path.relative_to(PROJECT_ROOT).as_posix()


def _source_for(source: str, node: ast.AST) -> str:
    segment = ast.get_source_segment(source, node)
    if segment is None:
        return f"<{type(node).__name__}>"
    return " ".join(segment.strip().split())


def _call_name(func: ast.expr) -> str | None:
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def _collect_check_preparation_cache_findings() -> list[str]:
    source = inspect.getsource(judge_tools.check_preparation)
    tree = ast.parse(source)
    findings: list[str] = []
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "get"
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "kwargs"
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and node.args[0].value == "event_list"
        ):
            findings.append(_source_for(source, node))
        if (
            isinstance(node, ast.Attribute)
            and node.attr == "event_list"
            and isinstance(node.value, ast.Name)
            and node.value.id == "record"
        ):
            findings.append(_source_for(source, node))
    return findings


def _may_request_event_list(value: ast.expr) -> bool:
    if isinstance(value, ast.Constant):
        return bool(value.value)
    return True


def _unpacked_event_list_values(value: ast.expr) -> list[ast.expr]:
    if not isinstance(value, ast.Dict):
        return []
    matches: list[ast.expr] = []
    for key, item in zip(value.keys, value.values, strict=True):
        if isinstance(key, ast.Constant) and key.value == "event_list":
            matches.append(item)
    return matches


def _collect_event_list_preparation_findings() -> list[EventListPreparationFinding]:
    findings: list[EventListPreparationFinding] = []
    for path in sorted(BUFF_XLOGIC_ROOT.rglob("*.py")):
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if _call_name(node.func) not in {"get_prepared", "check_preparation"}:
                continue
            for keyword in node.keywords:
                if keyword.arg == "event_list" and _may_request_event_list(keyword.value):
                    findings.append(
                        EventListPreparationFinding(
                            path=_relative_path(path),
                            line=keyword.value.lineno,
                            expression=_source_for(source, node),
                        )
                    )
                if keyword.arg is None:
                    for value in _unpacked_event_list_values(keyword.value):
                        if _may_request_event_list(value):
                            findings.append(
                                EventListPreparationFinding(
                                    path=_relative_path(path),
                                    line=value.lineno,
                                    expression=_source_for(source, node),
                                )
                            )
    return findings


def _contains_event_list_token(value: object) -> bool:
    return isinstance(value, str) and "event_list" in value


def _walk_config_value(
    path: Path, value: object, location: str = "$"
) -> list[ConfigEventListFinding]:
    findings: list[ConfigEventListFinding] = []
    if isinstance(value, dict):
        for key, item in value.items():
            child_location = f"{location}.{key}"
            if _contains_event_list_token(str(key)):
                findings.append(
                    ConfigEventListFinding(_relative_path(path), child_location, str(key))
                )
            findings.extend(_walk_config_value(path, item, child_location))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            findings.extend(_walk_config_value(path, item, f"{location}[{index}]"))
    elif _contains_event_list_token(value):
        findings.append(ConfigEventListFinding(_relative_path(path), location, str(value)))
    return findings


def _collect_csv_event_list_findings(path: Path) -> list[ConfigEventListFinding]:
    findings: list[ConfigEventListFinding] = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        for row_index, row in enumerate(csv.reader(handle), start=1):
            for column_index, cell in enumerate(row, start=1):
                if "event_list" in cell:
                    findings.append(
                        ConfigEventListFinding(
                            _relative_path(path),
                            f"row {row_index}, column {column_index}",
                            cell,
                        )
                    )
    return findings


def _collect_config_event_list_findings() -> list[ConfigEventListFinding]:
    findings: list[ConfigEventListFinding] = []
    config_paths = [path for path in CONFIG_FILES if path.exists()]
    config_paths.extend(
        path
        for path in sorted(DATA_ROOT.rglob("*"))
        if path.suffix.lower() in {".csv", ".json", ".toml"}
    )
    for path in config_paths:
        suffix = path.suffix.lower()
        if suffix == ".csv":
            findings.extend(_collect_csv_event_list_findings(path))
        elif suffix == ".json":
            findings.extend(_walk_config_value(path, json.loads(path.read_text(encoding="utf-8"))))
        elif suffix == ".toml":
            findings.extend(
                _walk_config_value(path, tomllib.loads(path.read_text(encoding="utf-8")))
            )
    return findings


def _make_preparation_context_fixture() -> SimpleNamespace:
    character = SimpleNamespace(NAME="安比", CID=1011)
    enemy = SimpleNamespace(name="enemy")
    action_stack = SimpleNamespace(name="action_stack")
    active_buff_view: dict[str, list[object]] = {character.NAME: []}
    preload_data = SimpleNamespace(name="preload_data")
    sim_instance = SimpleNamespace(
        char_data=SimpleNamespace(char_obj_list=[character]),
        init_data=SimpleNamespace(
            Judge_list_set=[
                [character.NAME, "啄木鸟电音", "任意音擎", "激素朋克二件套"],
            ]
        ),
        load_data=SimpleNamespace(
            exist_buff_dict={character.NAME: {}},
            action_stack=action_stack,
        ),
        schedule_data=SimpleNamespace(enemy=enemy),
        global_stats=SimpleNamespace(DYNAMIC_BUFF_DICT=active_buff_view),
        preload=SimpleNamespace(preload_data=preload_data),
    )
    sim_instance.buff_runtime_state = BuffRuntimeState(
        template_registry=sim_instance.load_data.exist_buff_dict,
        pending_queue={character.NAME: []},
        active_store=active_buff_view,
        enemy_mirror=[],
    )
    return SimpleNamespace(
        character=character,
        enemy=enemy,
        action_stack=action_stack,
        active_buff_view=active_buff_view,
        preload_data=preload_data,
        sim_instance=sim_instance,
        buff_instance=SimpleNamespace(sim_instance=sim_instance),
    )


def _make_alice_preparation_fixture() -> SimpleNamespace:
    character = SimpleNamespace(NAME="爱丽丝", CID=1401)
    enemy = SimpleNamespace(name="enemy")
    action_stack = SimpleNamespace(name="action_stack")
    preload_data = SimpleNamespace(name="preload_data")
    buff_index = "alice-additional-ability-ap-bonus"
    buff_0 = SimpleNamespace(history=SimpleNamespace(record=None))
    exist_buff_dict = {character.NAME: {buff_index: buff_0}}
    active_buff_view: dict[str, list[object]] = {character.NAME: []}
    sim_instance = SimpleNamespace(
        char_data=SimpleNamespace(char_obj_list=[character]),
        init_data=SimpleNamespace(Judge_list_set=[]),
        load_data=SimpleNamespace(
            exist_buff_dict=exist_buff_dict,
            action_stack=action_stack,
        ),
        schedule_data=SimpleNamespace(enemy=enemy),
        global_stats=SimpleNamespace(DYNAMIC_BUFF_DICT=active_buff_view),
        preload=SimpleNamespace(preload_data=preload_data),
    )
    sim_instance.buff_runtime_state = BuffRuntimeState(
        template_registry=exist_buff_dict,
        pending_queue={character.NAME: []},
        active_store=active_buff_view,
        enemy_mirror=[],
    )
    return SimpleNamespace(
        character=character,
        enemy=enemy,
        action_stack=action_stack,
        active_buff_view=active_buff_view,
        preload_data=preload_data,
        sim_instance=sim_instance,
        buff_index=buff_index,
        buff_0=buff_0,
        exist_buff_dict=exist_buff_dict,
        buff_instance=SimpleNamespace(
            sim_instance=sim_instance,
            ft=SimpleNamespace(index=buff_index),
        ),
    )


def _patch_legacy_preparation_helpers_to_fail(monkeypatch: pytest.MonkeyPatch) -> None:
    def unexpected_legacy_lookup(*args: object, **kwargs: object) -> object:
        raise AssertionError("PreparationContext path should not call legacy find_* helpers")

    for helper_name in (
        "find_equipper",
        "find_char_from_CID",
        "find_char_from_name",
        "find_enemy",
        "find_stack",
    ):
        monkeypatch.setattr(judge_tools, helper_name, unexpected_legacy_lookup)


def test_find_event_list_legacy_discovery_surface_is_deleted() -> None:
    find_main = importlib.import_module("zsim.sim_progress.Buff.JudgeTools.FindMain")

    assert not hasattr(find_main, "find_event_list")
    assert not hasattr(judge_tools, "find_event_list")


def test_check_preparation_has_no_event_list_cache_branch() -> None:
    findings = _collect_check_preparation_cache_findings()

    assert not findings, (
        "check_preparation still contains legacy event_list cache behavior:\n"
        + "\n".join(f"- {finding}" for finding in findings)
    )


@pytest.mark.parametrize("event_list", [True, False])
def test_check_preparation_explicit_event_list_keyword_is_rejected(
    event_list: bool,
) -> None:
    record = BuffRecordBaseClass()
    buff_0 = SimpleNamespace(history=SimpleNamespace(record=record))
    buff_instance = SimpleNamespace(sim_instance=object())

    with pytest.raises(ValueError, match="event_list"):
        judge_tools.check_preparation(
            buff_0=buff_0,
            buff_instance=buff_instance,
            event_list=event_list,
        )

    assert not hasattr(record, "event_list")


def test_check_preparation_event_list_true_does_not_create_cached_queue() -> None:
    record = BuffRecordBaseClass()
    buff_0 = SimpleNamespace(history=SimpleNamespace(record=record))
    buff_instance = SimpleNamespace(sim_instance=object())

    with pytest.raises(ValueError, match="event_list"):
        judge_tools.check_preparation(
            buff_0=buff_0,
            buff_instance=buff_instance,
            event_list=True,
        )

    assert not hasattr(record, "event_list")


def test_check_preparation_context_hydrates_char_enemy_and_action_stack(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _make_preparation_context_fixture()
    record = BuffRecordBaseClass()
    buff_0 = SimpleNamespace(history=SimpleNamespace(record=record))
    context = judge_tools.build_preparation_context_from_buff(fixture.buff_instance)
    _patch_legacy_preparation_helpers_to_fail(monkeypatch)

    judge_tools.check_preparation(
        buff_0=buff_0,
        buff_instance=fixture.buff_instance,
        preparation_context=context,
        equipper="啄木鸟电音",
        enemy=1,
        action_stack=1,
    )

    assert record.equipper == fixture.character.NAME
    assert record.char is fixture.character
    assert record.enemy is fixture.enemy
    assert record.action_stack is fixture.action_stack


def test_check_preparation_without_context_is_deleted() -> None:
    record = BuffRecordBaseClass()
    buff_0 = SimpleNamespace(history=SimpleNamespace(record=record))
    buff_instance = SimpleNamespace(sim_instance=object())

    with pytest.raises(ValueError, match="PreparationContext"):
        judge_tools.check_preparation(
            buff_0=buff_0,
            buff_instance=buff_instance,
            char_NAME="安比",
        )

    assert record.char is None


def test_woodpecker_na_get_prepared_uses_preparation_context_for_core_reads(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _make_preparation_context_fixture()
    record = BuffRecordBaseClass()
    buff_0 = SimpleNamespace(history=SimpleNamespace(record=record))
    logic = WoodpeckerElectroSet4_NA.__new__(WoodpeckerElectroSet4_NA)
    logic.buff_instance = fixture.buff_instance
    logic.buff_0 = buff_0
    _patch_legacy_preparation_helpers_to_fail(monkeypatch)

    logic.get_prepared(equipper="啄木鸟电音", enemy=1, action_stack=1)

    assert record.equipper == fixture.character.NAME
    assert record.char is fixture.character
    assert record.enemy is fixture.enemy
    assert record.action_stack is fixture.action_stack


def test_woodpecker_na_get_prepared_has_no_broad_findmain_calls() -> None:
    source = textwrap.dedent(inspect.getsource(WoodpeckerElectroSet4_NA.get_prepared))

    assert "build_preparation_context_from_buff" in source
    assert "preparation_context=preparation_context" in source
    assert "JudgeTools.find_" not in source
    assert "FindMain" not in source
    assert "find_enemy(" not in source
    assert "find_stack(" not in source
    assert "find_char" not in source


def test_alice_get_prepared_uses_preparation_context_for_core_reads(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _make_alice_preparation_fixture()
    record = AliceAdditionalAbilityApBonusRecord()
    fixture.buff_0.history.record = record
    logic = AliceAdditionalAbilityApBonus.__new__(AliceAdditionalAbilityApBonus)
    logic.buff_instance = fixture.buff_instance
    logic.buff_0 = fixture.buff_0
    _patch_legacy_preparation_helpers_to_fail(monkeypatch)

    logic.get_prepared(char_CID=1401, sub_exist_buff_dict=1, enemy=1)

    assert record.char is fixture.character
    assert record.enemy is fixture.enemy
    assert record.sub_exist_buff_dict is fixture.exist_buff_dict["爱丽丝"]


def test_alice_check_record_module_uses_template_registry_and_lazy_record(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _make_alice_preparation_fixture()
    logic = AliceAdditionalAbilityApBonus.__new__(AliceAdditionalAbilityApBonus)
    logic.buff_instance = fixture.buff_instance
    logic.buff_0 = None
    logic.record = None
    _patch_legacy_preparation_helpers_to_fail(monkeypatch)

    logic.check_record_module()

    assert logic.buff_0 is fixture.buff_0
    assert logic.record is fixture.buff_0.history.record
    assert isinstance(logic.record, AliceAdditionalAbilityApBonusRecord)

    existing_record = logic.record
    fixture.sim_instance.load_data.exist_buff_dict = {"爱丽丝": {}}
    logic.check_record_module()

    assert logic.buff_0 is fixture.buff_0
    assert logic.record is existing_record
    assert fixture.buff_0.history.record is existing_record


def test_alice_preparation_wrapper_has_no_broad_findmain_calls() -> None:
    source = textwrap.dedent(
        inspect.getsource(AliceAdditionalAbilityApBonus.get_prepared)
        + "\n"
        + inspect.getsource(AliceAdditionalAbilityApBonus.check_record_module)
    )

    assert "build_preparation_context_from_buff" in source
    assert "preparation_context=preparation_context" in source
    assert "JudgeTools.find_" not in source
    assert "find_exist_buff_dict" not in source


def test_buff_xlogic_does_not_request_event_list_preparation_cache() -> None:
    findings = _collect_event_list_preparation_findings()

    assert not findings, (
        "BuffXLogic callsites still request legacy event_list preparation:\n"
        + "\n".join(f"- {finding.message()}" for finding in findings)
    )


def test_buff_data_and_config_do_not_request_event_list_preparation_cache() -> None:
    findings = _collect_config_event_list_findings()

    assert not findings, (
        "Buff data/config files still expose event_list preparation keys:\n"
        + "\n".join(f"- {finding.message()}" for finding in findings)
    )
