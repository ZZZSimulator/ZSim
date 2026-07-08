from __future__ import annotations

from collections.abc import Callable
from typing import Any, cast

import pytest

from zsim.sim_progress.Buff.BuffXLogic.enemy_edge_state_read import (
    read_enemy_frost_frostbite_edge_state,
    read_enemy_frozen_edge_state,
    read_enemy_stun_edge_state,
)

_MISSING = object()


class _EnemyDynamicStateProbe:
    def __init__(
        self,
        *,
        frozen: bool | None | object = _MISSING,
        stun: bool | None | object = _MISSING,
        frost_frostbite: bool | None | object = _MISSING,
    ) -> None:
        self._values = {
            "frozen": frozen,
            "stun": stun,
            "frost_frostbite": frost_frostbite,
        }
        self.reads = {
            "frozen": 0,
            "stun": 0,
            "frost_frostbite": 0,
            "shock": 0,
            "burn": 0,
            "assault": 0,
            "corruption": 0,
        }

    def set_value(self, name: str, value: bool | None) -> None:
        self._values[name] = value

    def _read_edge_field(self, name: str) -> bool | None:
        self.reads[name] += 1
        value = self._values[name]
        if value is _MISSING:
            raise AssertionError(f"edge helper must not read missing {name}")
        return value  # type: ignore[return-value]

    def _read_sibling_field(self, name: str) -> bool:
        self.reads[name] += 1
        raise AssertionError(f"edge helper must not read sibling property {name}")

    @property
    def frozen(self) -> bool | None:
        return self._read_edge_field("frozen")

    @property
    def stun(self) -> bool | None:
        return self._read_edge_field("stun")

    @property
    def frost_frostbite(self) -> bool | None:
        return self._read_edge_field("frost_frostbite")

    @property
    def shock(self) -> bool:
        return self._read_sibling_field("shock")

    @property
    def burn(self) -> bool:
        return self._read_sibling_field("burn")

    @property
    def assault(self) -> bool:
        return self._read_sibling_field("assault")

    @property
    def corruption(self) -> bool:
        return self._read_sibling_field("corruption")


class _EnemyProbe:
    dynamic: _EnemyDynamicStateProbe

    _FORBIDDEN_SURFACES = frozenset(
        {
            "buff_0",
            "history",
            "record",
            "sim_instance",
            "load_data",
            "schedule_data",
            "event_list",
            "listener_manager",
            "runtime_command_port",
            "sub_exist_buff_dict",
            "old_container",
        }
    )

    def __init__(self, dynamic: _EnemyDynamicStateProbe) -> None:
        object.__setattr__(self, "dynamic", dynamic)
        object.__setattr__(self, "forbidden_reads", [])

    def __getattribute__(self, name: str) -> Any:
        if name in object.__getattribute__(self, "_FORBIDDEN_SURFACES"):
            object.__getattribute__(self, "forbidden_reads").append(name)
            raise AssertionError(
                "edge helper must not traverse scheduled, listener, runtime, "
                f"or old-container surface {name}"
            )
        return object.__getattribute__(self, name)


def _enemy_with_dynamic(dynamic: _EnemyDynamicStateProbe) -> _EnemyProbe:
    return _EnemyProbe(dynamic)


@pytest.mark.parametrize(
    ("frozen", "expected"),
    [(True, True), (False, False), (None, False)],
)
def test_read_enemy_frozen_edge_state_normalizes_only_frozen_none(
    *,
    frozen: bool | None,
    expected: bool,
) -> None:
    dynamic = _EnemyDynamicStateProbe(frozen=frozen)
    enemy = _enemy_with_dynamic(dynamic)

    assert read_enemy_frozen_edge_state(cast(Any, enemy)) is expected

    assert dynamic.reads["frozen"] == 1
    assert dynamic.reads["stun"] == 0
    assert dynamic.reads["frost_frostbite"] == 0
    assert dynamic.reads["shock"] == 0
    assert dynamic.reads["burn"] == 0
    assert dynamic.reads["assault"] == 0
    assert dynamic.reads["corruption"] == 0
    assert enemy.forbidden_reads == []


@pytest.mark.parametrize("stun", [True, False, None])
def test_read_enemy_stun_edge_state_forwards_current_property_exactly(
    *,
    stun: bool | None,
) -> None:
    dynamic = _EnemyDynamicStateProbe(stun=stun)
    enemy = _enemy_with_dynamic(dynamic)

    assert read_enemy_stun_edge_state(cast(Any, enemy)) is stun

    assert dynamic.reads["stun"] == 1
    assert dynamic.reads["frozen"] == 0
    assert dynamic.reads["frost_frostbite"] == 0
    assert dynamic.reads["shock"] == 0
    assert dynamic.reads["burn"] == 0
    assert dynamic.reads["assault"] == 0
    assert dynamic.reads["corruption"] == 0
    assert enemy.forbidden_reads == []


@pytest.mark.parametrize("frost_frostbite", [True, False, None])
def test_read_enemy_frost_frostbite_edge_state_forwards_current_property_exactly(
    *,
    frost_frostbite: bool | None,
) -> None:
    dynamic = _EnemyDynamicStateProbe(frost_frostbite=frost_frostbite)
    enemy = _enemy_with_dynamic(dynamic)

    assert read_enemy_frost_frostbite_edge_state(cast(Any, enemy)) is frost_frostbite

    assert dynamic.reads["frost_frostbite"] == 1
    assert dynamic.reads["frozen"] == 0
    assert dynamic.reads["stun"] == 0
    assert dynamic.reads["shock"] == 0
    assert dynamic.reads["burn"] == 0
    assert dynamic.reads["assault"] == 0
    assert dynamic.reads["corruption"] == 0
    assert enemy.forbidden_reads == []


@pytest.mark.parametrize(
    (
        "helper",
        "field_name",
        "first_value",
        "first_expected",
        "second_value",
        "second_expected",
    ),
    [
        (
            read_enemy_frozen_edge_state,
            "frozen",
            None,
            False,
            True,
            True,
        ),
        (
            read_enemy_stun_edge_state,
            "stun",
            True,
            True,
            False,
            False,
        ),
        (
            read_enemy_frost_frostbite_edge_state,
            "frost_frostbite",
            None,
            None,
            True,
            True,
        ),
    ],
)
def test_edge_state_read_helpers_do_not_cache_current_property(
    *,
    helper: Callable[[Any], bool | None],
    field_name: str,
    first_value: bool | None,
    first_expected: bool | None,
    second_value: bool | None,
    second_expected: bool | None,
) -> None:
    dynamic = _EnemyDynamicStateProbe(**{field_name: first_value})
    enemy = _enemy_with_dynamic(dynamic)

    assert helper(enemy) is first_expected
    dynamic.set_value(field_name, second_value)
    assert helper(enemy) is second_expected

    assert dynamic.reads[field_name] == 2
    assert enemy.forbidden_reads == []
