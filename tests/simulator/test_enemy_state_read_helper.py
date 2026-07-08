from __future__ import annotations

import inspect
from types import SimpleNamespace

import pytest

from zsim.sim_progress.Buff.BuffXLogic.enemy_state_read import (
    read_enemy_shock_active,
    read_enemy_stun_active,
    read_enemy_stun_rest_tick,
)


class _EnemyDynamicStateProbe:
    def __init__(self, *, shock: bool, stun: bool) -> None:
        self._shock = shock
        self._stun = stun
        self.shock_reads = 0
        self.stun_reads = 0

    @property
    def shock(self) -> bool:
        self.shock_reads += 1
        return self._shock

    @property
    def stun(self) -> bool:
        self.stun_reads += 1
        return self._stun


class _EnemyDynamicRestTickTrap:
    def __init__(self) -> None:
        self.rest_tick_reads = 0

    def get_stun_rest_tick(self) -> float:
        self.rest_tick_reads += 1
        raise AssertionError("stun rest tick must be read from the enemy object")


class _EnemyStunRestTickProbe:
    def __init__(self, rest_tick: float) -> None:
        self._rest_tick = rest_tick
        self.rest_tick_reads = 0
        self.dynamic = _EnemyDynamicRestTickTrap()

    def get_stun_rest_tick(self) -> float:
        self.rest_tick_reads += 1
        return self._rest_tick


@pytest.mark.parametrize("shock", [True, False])
def test_read_enemy_shock_active_reads_dynamic_shock_once(*, shock: bool) -> None:
    dynamic = _EnemyDynamicStateProbe(shock=shock, stun=not shock)
    enemy = SimpleNamespace(dynamic=dynamic)

    assert read_enemy_shock_active(enemy) is shock
    assert dynamic.shock_reads == 1
    assert dynamic.stun_reads == 0


@pytest.mark.parametrize("stun", [True, False])
def test_read_enemy_stun_active_reads_dynamic_stun_once(*, stun: bool) -> None:
    dynamic = _EnemyDynamicStateProbe(shock=not stun, stun=stun)
    enemy = SimpleNamespace(dynamic=dynamic)

    assert read_enemy_stun_active(enemy) is stun
    assert dynamic.stun_reads == 1
    assert dynamic.shock_reads == 0


@pytest.mark.parametrize("rest_tick", [-7.5, 0.0, 360.25, 999.75])
def test_read_enemy_stun_rest_tick_delegates_once_without_transform(
    rest_tick: float,
) -> None:
    enemy = _EnemyStunRestTickProbe(rest_tick=rest_tick)

    assert read_enemy_stun_rest_tick(enemy) == rest_tick
    assert enemy.rest_tick_reads == 1
    assert enemy.dynamic.rest_tick_reads == 0


def test_read_enemy_stun_rest_tick_preserves_missing_method_failure() -> None:
    enemy = SimpleNamespace(dynamic=_EnemyDynamicRestTickTrap())

    with pytest.raises(AttributeError, match="get_stun_rest_tick"):
        read_enemy_stun_rest_tick(enemy)

    assert enemy.dynamic.rest_tick_reads == 0


def test_read_enemy_stun_rest_tick_stays_inside_enemy_read_boundary() -> None:
    source = inspect.getsource(read_enemy_stun_rest_tick)

    assert "return enemy.get_stun_rest_tick()" in source
    for forbidden_term in (
        "BuffRuntimeReadPort",
        "RuntimeCommandPort",
        "ScheduleDispatchPort",
        "listener",
        "broadcast",
        "scheduled",
        "queue",
        "read_enemy_active_anomaly_list",
        "read_enemy_active_anomaly_bar",
        "read_enemy_anomaly_active",
    ):
        assert forbidden_term not in source
