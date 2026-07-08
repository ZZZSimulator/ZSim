from __future__ import annotations

import ast
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Mapping, Sequence, cast

import pytest

import zsim.define as define_module
from zsim.sim_progress.ScheduledEvent.buff_runtime import (
    BuffRuntimeReadPort,
    BuffRuntimeState,
)

sys.modules.setdefault("define", define_module)

from zsim.sim_progress.Buff.BuffXLogic.IceJadeTeaPotExtraDMGBonus import (
    IceJadeTeaPotExtraDMGBonus,
)

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_ICEJADE_SOURCE_PATH = (
    _PROJECT_ROOT
    / "zsim"
    / "sim_progress"
    / "Buff"
    / "BuffXLogic"
    / "IceJadeTeaPotExtraDMGBonus.py"
)
_ICEJADE_ITEM_NAME = "玉壶青冰"
_ICEJADE_EQUIPPER = "青衣"
_ICEJADE_TRIGGER_INDEX = "Buff-武器-玉壶青冰-普攻加冲击"


class _FailIfCountRead:
    @property
    def count(self) -> float:
        raise AssertionError("later matching IceJade Buff must not be inspected")


class _FailingGlobalStats:
    @property
    def DYNAMIC_BUFF_DICT(self) -> object:
        raise AssertionError("Ice Jade should read active Buffs through BuffRuntimeReadPort")


class _RuntimeViewProbe(BuffRuntimeReadPort):
    def __init__(self, active_buff_view: Mapping[str, Sequence[object]]) -> None:
        self.active_buff_view = active_buff_view
        self.active_view_calls = 0

    def get_active_buffs(self, beneficiary: str) -> Sequence[object]:
        return tuple(self.active_buff_view.get(beneficiary, ()))

    def get_active_buff_view(self) -> Mapping[str, Sequence[object]]:
        self.active_view_calls += 1
        return self.active_buff_view

    def get_exist_buff_snapshot(self, beneficiary: str) -> Mapping[str, object]:
        return {}

    def get_exist_buff_snapshot_view(self) -> Mapping[str, Mapping[str, object]]:
        return {}


class _RuntimeStateProbe:
    def __init__(self, runtime_view: _RuntimeViewProbe) -> None:
        self.runtime_view = runtime_view
        self.create_read_port_calls = 0

    def create_read_port(self) -> _RuntimeViewProbe:
        self.create_read_port_calls += 1
        return self.runtime_view


def _dynamic_buff(index: str, count: float) -> object:
    return SimpleNamespace(
        ft=SimpleNamespace(index=index),
        dy=SimpleNamespace(count=count),
    )


def _dynamic_buff_with_failing_count(index: str) -> object:
    return SimpleNamespace(
        ft=SimpleNamespace(index=index),
        dy=_FailIfCountRead(),
    )


def _make_sim_instance(
    *,
    dynamic_buff_dict: dict[Any, list[object]],
    judge_list_set: list[list[str]] | None = None,
) -> object:
    if judge_list_set is None:
        judge_list_set = [[_ICEJADE_EQUIPPER, _ICEJADE_ITEM_NAME, "test-slot", "test-2pc"]]
    enemy = SimpleNamespace(dynamic=SimpleNamespace(dynamic_debuff_list=[]))
    return SimpleNamespace(
        char_data=SimpleNamespace(char_obj_list=[]),
        init_data=SimpleNamespace(Judge_list_set=judge_list_set),
        load_data=SimpleNamespace(exist_buff_dict={}, action_stack=SimpleNamespace()),
        schedule_data=SimpleNamespace(enemy=enemy),
        global_stats=_FailingGlobalStats(),
        preload=SimpleNamespace(preload_data=SimpleNamespace()),
        buff_runtime_state=BuffRuntimeState(
            template_registry={},
            pending_queue={},
            active_store=dynamic_buff_dict,
            enemy_mirror=enemy.dynamic.dynamic_debuff_list,
        ),
    )


def _make_logic(
    *,
    dynamic_buff_dict: dict[Any, list[object]],
    judge_list_set: list[list[str]] | None = None,
) -> IceJadeTeaPotExtraDMGBonus:
    sim_instance = _make_sim_instance(
        dynamic_buff_dict=dynamic_buff_dict,
        judge_list_set=judge_list_set,
    )
    buff_instance = SimpleNamespace(
        ft=SimpleNamespace(index="Buff-武器-玉壶青冰-额外增伤"),
        sim_instance=sim_instance,
    )
    return IceJadeTeaPotExtraDMGBonus(cast(Any, buff_instance))


def test_ice_jade_first_matching_count_at_or_above_threshold_returns_true() -> None:
    later_matching_buff = _dynamic_buff_with_failing_count(f"{_ICEJADE_TRIGGER_INDEX}-later-copy")
    logic = _make_logic(
        dynamic_buff_dict={
            _ICEJADE_EQUIPPER: [
                _dynamic_buff("Buff-武器-玉壶青冰-其他层数", 99),
                _dynamic_buff(_ICEJADE_TRIGGER_INDEX, 15),
                later_matching_buff,
            ]
        }
    )

    assert logic.special_judge_logic() is True


def test_ice_jade_first_matching_count_below_threshold_returns_false() -> None:
    later_matching_buff = _dynamic_buff_with_failing_count(f"{_ICEJADE_TRIGGER_INDEX}-later-copy")
    logic = _make_logic(
        dynamic_buff_dict={
            _ICEJADE_EQUIPPER: [
                _dynamic_buff("Buff-武器-玉壶青冰-其他层数", 99),
                _dynamic_buff(_ICEJADE_TRIGGER_INDEX, 14),
                later_matching_buff,
            ]
        }
    )

    assert logic.special_judge_logic() is False


def test_ice_jade_no_matching_dynamic_buff_falls_through_to_none() -> None:
    logic = _make_logic(
        dynamic_buff_dict={
            _ICEJADE_EQUIPPER: [
                _dynamic_buff("Buff-武器-玉壶青冰-非普攻冲击", 99),
                _dynamic_buff("Buff-驱动盘-其他-普攻加冲击", 99),
            ]
        }
    )

    assert logic.special_judge_logic() is None


def test_ice_jade_missing_equipper_uses_none_key_and_raises_key_error() -> None:
    logic = _make_logic(
        dynamic_buff_dict={_ICEJADE_EQUIPPER: []},
        judge_list_set=[[_ICEJADE_EQUIPPER, "不是玉壶青冰", "test-slot", "test-2pc"]],
    )

    with pytest.raises(KeyError) as exc_info:
        logic.special_judge_logic()

    assert exc_info.value.args == (None,)


def test_ice_jade_missing_dynamic_list_key_raises_equipper_key_error() -> None:
    logic = _make_logic(dynamic_buff_dict={"其他角色": []})

    with pytest.raises(KeyError) as exc_info:
        logic.special_judge_logic()

    assert exc_info.value.args == (_ICEJADE_EQUIPPER,)


def test_ice_jade_reads_active_view_through_runtime_read_port() -> None:
    runtime_view = _RuntimeViewProbe(
        {_ICEJADE_EQUIPPER: [_dynamic_buff(_ICEJADE_TRIGGER_INDEX, 15)]}
    )
    runtime_state = _RuntimeStateProbe(runtime_view)
    sim_instance = _make_sim_instance(dynamic_buff_dict={})
    sim_instance.buff_runtime_state = runtime_state
    buff_instance = SimpleNamespace(
        ft=SimpleNamespace(index="Buff-武器-玉壶青冰-额外增伤"),
        sim_instance=sim_instance,
    )

    logic = IceJadeTeaPotExtraDMGBonus(cast(Any, buff_instance))

    assert logic.special_judge_logic() is True
    assert runtime_state.create_read_port_calls == 1
    assert runtime_view.active_view_calls == 1


def _special_judge_logic_node(tree: ast.Module) -> ast.FunctionDef:
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "special_judge_logic":
            return node
    raise AssertionError("special_judge_logic(...) source node was not found")


def _call_name(call: ast.Call) -> str | None:
    if isinstance(call.func, ast.Name):
        return call.func.id
    if isinstance(call.func, ast.Attribute) and isinstance(call.func.value, ast.Name):
        return f"{call.func.value.id}.{call.func.attr}"
    return None


def _direct_dynamic_lookup_calls(special_judge_node: ast.FunctionDef) -> list[ast.Call]:
    return [
        call
        for call in ast.walk(special_judge_node)
        if isinstance(call, ast.Call) and _call_name(call) == "JudgeTools.find_dynamic_buff_list"
    ]


def _direct_global_active_view_reads(tree: ast.Module) -> list[ast.Attribute]:
    return [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Attribute) and node.attr == "DYNAMIC_BUFF_DICT"
    ]


def _replacement_helper_or_view_is_present(
    tree: ast.Module,
    special_judge_node: ast.FunctionDef,
) -> bool:
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name not in {
            "__init__",
            "special_judge_logic",
        }:
            return True
        if isinstance(node, ast.ClassDef) and node.name != "IceJadeTeaPotExtraDMGBonus":
            return True

    legacy_calls = {
        "JudgeTools.find_equipper",
        "JudgeTools.find_dynamic_buff_list",
    }
    return any(
        _call_name(call) not in legacy_calls
        for call in ast.walk(special_judge_node)
        if isinstance(call, ast.Call)
    )


def test_post_replacement_guard_rejects_direct_dynamic_lookup_in_judge_logic() -> None:
    source = _ICEJADE_SOURCE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    special_judge_node = _special_judge_logic_node(tree)

    if not _replacement_helper_or_view_is_present(tree, special_judge_node):
        pytest.skip("US-002 pins pre-replacement behavior before helper/view exists")

    assert _direct_dynamic_lookup_calls(special_judge_node) == []
    assert _direct_global_active_view_reads(tree) == []
