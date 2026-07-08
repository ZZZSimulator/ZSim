from __future__ import annotations

from collections.abc import Iterable
from typing import Any, Protocol

from zsim.sim_progress.Buff.buff_class import Buff
from zsim.sim_progress.Dot.BaseDot import Dot


class _EnemyDynamicWithShockRead(Protocol):
    @property
    def shock(self) -> bool: ...


class _EnemyWithDynamicShockRead(Protocol):
    dynamic: _EnemyDynamicWithShockRead


class _EnemyDynamicWithStunRead(Protocol):
    @property
    def stun(self) -> bool: ...


class _EnemyWithDynamicStunRead(Protocol):
    dynamic: _EnemyDynamicWithStunRead


class _EnemyWithStunRestTickRead(Protocol):
    def get_stun_rest_tick(self) -> float: ...


class _EnemyDynamicWithStateRead(
    _EnemyDynamicWithShockRead,
    _EnemyDynamicWithStunRead,
    Protocol,
):
    pass


class _EnemyWithDynamicStateRead(Protocol):
    dynamic: _EnemyDynamicWithStateRead


class _EnemyDynamicWithAnomalyRead(Protocol):
    def is_under_anomaly(self) -> bool: ...


class _EnemyWithDynamicAnomalyRead(Protocol):
    dynamic: _EnemyDynamicWithAnomalyRead


class _EnemyDynamicWithActiveAnomalyListRead(Protocol):
    def get_active_anomaly(self) -> list[Any]: ...


class _EnemyWithDynamicActiveAnomalyListRead(Protocol):
    dynamic: _EnemyDynamicWithActiveAnomalyListRead


class _EnemyWithActiveAnomalyBarRead(Protocol):
    def get_active_anomaly_bar(self) -> Any: ...


class _EnemyDynamicWithFrozenEdgeRead(Protocol):
    @property
    def frozen(self) -> bool | None: ...


class _EnemyWithDynamicFrozenEdgeRead(Protocol):
    dynamic: _EnemyDynamicWithFrozenEdgeRead


class _EnemyDynamicWithStunEdgeRead(Protocol):
    @property
    def stun(self) -> bool | None: ...


class _EnemyWithDynamicStunEdgeRead(Protocol):
    dynamic: _EnemyDynamicWithStunEdgeRead


class _EnemyDynamicWithFrostFrostbiteEdgeRead(Protocol):
    @property
    def frost_frostbite(self) -> bool | None: ...


class _EnemyWithDynamicFrostFrostbiteEdgeRead(Protocol):
    dynamic: _EnemyDynamicWithFrostFrostbiteEdgeRead


class _EnemyDynamicWithEdgeStateRead(
    _EnemyDynamicWithFrozenEdgeRead,
    _EnemyDynamicWithStunEdgeRead,
    _EnemyDynamicWithFrostFrostbiteEdgeRead,
    Protocol,
):
    pass


class _EnemyWithDynamicEdgeStateRead(Protocol):
    dynamic: _EnemyDynamicWithEdgeStateRead


class _EnemyWithDynamicAnomalyMapRead(Protocol):
    dynamic: object


class _EnemyDynamicWithDebuffMirrorRead(Protocol):
    @property
    def dynamic_debuff_list(self) -> Iterable[object]: ...


class _EnemyWithDynamicDebuffMirrorRead(Protocol):
    dynamic: _EnemyDynamicWithDebuffMirrorRead


class _EnemyDynamicWithDotRuntimeRead(Protocol):
    @property
    def dynamic_dot_list(self) -> Iterable[Dot]: ...


class _EnemyWithDotRuntimeRead(Protocol):
    dynamic: _EnemyDynamicWithDotRuntimeRead


def read_enemy_shock_active(enemy: _EnemyWithDynamicShockRead) -> bool:
    return enemy.dynamic.shock


def read_enemy_stun_active(enemy: _EnemyWithDynamicStunRead) -> bool:
    return enemy.dynamic.stun


def read_enemy_stun_rest_tick(enemy: _EnemyWithStunRestTickRead) -> float:
    return enemy.get_stun_rest_tick()


class EnemyStateReadPort:
    def __init__(self, enemy: _EnemyWithDynamicStateRead) -> None:
        self._enemy = enemy

    def shock_active(self) -> bool:
        return read_enemy_shock_active(self._enemy)

    def stun_active(self) -> bool:
        return read_enemy_stun_active(self._enemy)


def read_enemy_anomaly_active(enemy: _EnemyWithDynamicAnomalyRead) -> bool:
    return enemy.dynamic.is_under_anomaly()


def read_enemy_active_anomaly_list(
    enemy: _EnemyWithDynamicActiveAnomalyListRead,
) -> list[Any]:
    return enemy.dynamic.get_active_anomaly()


def read_enemy_active_anomaly_bar(enemy: _EnemyWithActiveAnomalyBarRead) -> Any:
    return enemy.get_active_anomaly_bar()


def read_enemy_frozen_edge_state(enemy: _EnemyWithDynamicFrozenEdgeRead) -> bool:
    frozen = enemy.dynamic.frozen
    return False if frozen is None else frozen


def read_enemy_stun_edge_state(
    enemy: _EnemyWithDynamicStunEdgeRead,
) -> bool | None:
    return enemy.dynamic.stun


def read_enemy_frost_frostbite_edge_state(
    enemy: _EnemyWithDynamicFrostFrostbiteEdgeRead,
) -> bool | None:
    return enemy.dynamic.frost_frostbite


class EnemyEdgeStateReadPort:
    def __init__(self, enemy: _EnemyWithDynamicEdgeStateRead) -> None:
        self._enemy = enemy

    def frozen_edge_state(self) -> bool:
        return read_enemy_frozen_edge_state(self._enemy)

    def stun_edge_state(self) -> bool | None:
        return read_enemy_stun_edge_state(self._enemy)

    def frost_frostbite_edge_state(self) -> bool | None:
        return read_enemy_frost_frostbite_edge_state(self._enemy)


def read_enemy_anomaly_state(
    enemy: _EnemyWithDynamicAnomalyMapRead,
    name: str,
) -> Any:
    return getattr(enemy.dynamic, name)


def snapshot_enemy_anomaly_states(
    enemy: _EnemyWithDynamicAnomalyMapRead,
    names: Iterable[str],
) -> dict[str, Any]:
    return {name: getattr(enemy.dynamic, name) for name in names}


_MIYABI_FROSTBURN_DEBUFF_INDEX = "Buff-角色-雅-核心被动-霜灼"


class MiyabiFrostburnDebuffMirrorReader:
    def __init__(self, enemy: _EnemyWithDynamicDebuffMirrorRead) -> None:
        self._dynamic_debuff_list = enemy.dynamic.dynamic_debuff_list

    def has_miyabi_frostburn_debuff(self) -> bool:
        for debuff in self._dynamic_debuff_list:
            if not isinstance(debuff, Buff):
                raise TypeError(f"{debuff}不是Buff类！")
            if debuff.ft.index == _MIYABI_FROSTBURN_DEBUFF_INDEX:
                return True
        return False


def snapshot_enemy_dot_runtime_state(
    enemy: _EnemyWithDotRuntimeRead,
) -> tuple[Dot, ...]:
    return tuple(enemy.dynamic.dynamic_dot_list)


class DotRuntimeStateReadPort:
    def __init__(self, enemy: _EnemyWithDotRuntimeRead) -> None:
        self._enemy = enemy

    def snapshot(self) -> tuple[Dot, ...]:
        return snapshot_enemy_dot_runtime_state(self._enemy)

    def find_by_index(self, dot_index: str | None) -> Dot | None:
        for dot in self.snapshot():
            if dot.ft.index == dot_index:
                return dot
        return None

    def find_active_by_index(self, dot_index: str | None) -> Dot | None:
        for dot in self.snapshot():
            if dot.ft.index == dot_index and dot.dy.active:
                return dot
        return None


__all__ = [
    "DotRuntimeStateReadPort",
    "EnemyEdgeStateReadPort",
    "EnemyStateReadPort",
    "MiyabiFrostburnDebuffMirrorReader",
    "read_enemy_active_anomaly_bar",
    "read_enemy_active_anomaly_list",
    "read_enemy_anomaly_active",
    "read_enemy_anomaly_state",
    "read_enemy_frost_frostbite_edge_state",
    "read_enemy_frozen_edge_state",
    "read_enemy_shock_active",
    "read_enemy_stun_active",
    "read_enemy_stun_edge_state",
    "read_enemy_stun_rest_tick",
    "snapshot_enemy_anomaly_states",
    "snapshot_enemy_dot_runtime_state",
]
