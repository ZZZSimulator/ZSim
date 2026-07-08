from __future__ import annotations

from typing import Any, cast

import pytest

from zsim.sim_progress.Buff.BuffXLogic.enemy_anomaly_map_read import (
    read_enemy_anomaly_state,
    snapshot_enemy_anomaly_states,
)

ANOMALY_NAMES = (
    "frostbite",
    "assault",
    "shock",
    "burn",
    "corruption",
    "frost_frostbite",
)
ANOMALY_SNAPSHOT_NAMES = (
    "frostbite",
    "assault",
    "shock",
    "burn",
    "corruption",
)
_MISSING = object()


class _EnemyDynamicAnomalyMapProbe:
    def __init__(self, **values: Any) -> None:
        self._values = {name: values.get(name, _MISSING) for name in ANOMALY_NAMES}
        self.reads = {name: 0 for name in ANOMALY_NAMES}

    def set_value(self, name: str, value: Any) -> None:
        self._values[name] = value

    def __getattribute__(self, name: str) -> Any:
        if name in ANOMALY_NAMES:
            reads = object.__getattribute__(self, "reads")
            values = object.__getattribute__(self, "_values")
            reads[name] += 1
            value = values[name]
            if value is _MISSING:
                raise AssertionError(f"anomaly-map helper must not read missing {name}")
            return value
        return object.__getattribute__(self, name)


class _EnemyProbe:
    dynamic: _EnemyDynamicAnomalyMapProbe

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
            "action_stack",
            "effect_count",
            "disorder",
        }
    )

    def __init__(self, dynamic: _EnemyDynamicAnomalyMapProbe) -> None:
        object.__setattr__(self, "dynamic", dynamic)
        object.__setattr__(self, "forbidden_reads", [])

    def __getattribute__(self, name: str) -> Any:
        if name in object.__getattribute__(self, "_FORBIDDEN_SURFACES"):
            object.__getattribute__(self, "forbidden_reads").append(name)
            raise AssertionError(
                "anomaly-map helper must not traverse record, scheduled, listener, "
                f"runtime, action, counter, disorder, or old-container surface {name}"
            )
        return object.__getattribute__(self, name)


def _enemy_with_dynamic(dynamic: _EnemyDynamicAnomalyMapProbe) -> _EnemyProbe:
    return _EnemyProbe(dynamic)


@pytest.mark.parametrize("name", ANOMALY_NAMES)
@pytest.mark.parametrize("value", [True, False])
def test_read_enemy_anomaly_state_reads_only_named_field_once(
    *,
    name: str,
    value: bool,
) -> None:
    dynamic = _EnemyDynamicAnomalyMapProbe(**{name: value})
    enemy = _enemy_with_dynamic(dynamic)

    assert read_enemy_anomaly_state(cast(Any, enemy), name) is value

    assert dynamic.reads[name] == 1
    assert all(dynamic.reads[sibling] == 0 for sibling in ANOMALY_NAMES if sibling != name)
    assert enemy.forbidden_reads == []


def test_read_enemy_anomaly_state_preserves_frost_frostbite_none_exactly() -> None:
    dynamic = _EnemyDynamicAnomalyMapProbe(frost_frostbite=None)
    enemy = _enemy_with_dynamic(dynamic)

    assert read_enemy_anomaly_state(cast(Any, enemy), "frost_frostbite") is None

    assert dynamic.reads["frost_frostbite"] == 1
    assert all(
        dynamic.reads[sibling] == 0 for sibling in ANOMALY_NAMES if sibling != "frost_frostbite"
    )
    assert enemy.forbidden_reads == []


def test_read_enemy_anomaly_state_does_not_cache_named_field() -> None:
    dynamic = _EnemyDynamicAnomalyMapProbe(frostbite=False)
    enemy = _enemy_with_dynamic(dynamic)

    assert read_enemy_anomaly_state(cast(Any, enemy), "frostbite") is False
    dynamic.set_value("frostbite", True)
    assert read_enemy_anomaly_state(cast(Any, enemy), "frostbite") is True

    assert dynamic.reads["frostbite"] == 2
    assert enemy.forbidden_reads == []


def test_snapshot_enemy_anomaly_states_reads_explicit_iterable_once() -> None:
    values = {
        "frostbite": True,
        "assault": False,
        "shock": True,
        "burn": False,
        "corruption": True,
    }
    dynamic = _EnemyDynamicAnomalyMapProbe(**values)
    enemy = _enemy_with_dynamic(dynamic)

    assert snapshot_enemy_anomaly_states(cast(Any, enemy), ANOMALY_SNAPSHOT_NAMES) == values

    assert all(dynamic.reads[name] == 1 for name in ANOMALY_SNAPSHOT_NAMES)
    assert dynamic.reads["frost_frostbite"] == 0
    assert enemy.forbidden_reads == []


def test_snapshot_enemy_anomaly_states_uses_only_provided_names() -> None:
    dynamic = _EnemyDynamicAnomalyMapProbe(
        frostbite=True,
        frost_frostbite=False,
    )
    enemy = _enemy_with_dynamic(dynamic)

    assert snapshot_enemy_anomaly_states(
        cast(Any, enemy),
        ("frostbite", "frost_frostbite"),
    ) == {"frostbite": True, "frost_frostbite": False}

    assert dynamic.reads["frostbite"] == 1
    assert dynamic.reads["frost_frostbite"] == 1
    assert all(
        dynamic.reads[sibling] == 0
        for sibling in ANOMALY_NAMES
        if sibling not in {"frostbite", "frost_frostbite"}
    )
    assert enemy.forbidden_reads == []
