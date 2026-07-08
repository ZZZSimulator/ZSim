from __future__ import annotations

from types import SimpleNamespace

import pytest

from zsim.sim_progress.Buff.BuffXLogic.enemy_anomaly_read import (
    read_enemy_anomaly_active,
)


class _EnemyDynamicProbe:
    def __init__(self, *, under_anomaly: bool) -> None:
        self.under_anomaly = under_anomaly
        self.calls = 0

    def is_under_anomaly(self) -> bool:
        self.calls += 1
        return self.under_anomaly


@pytest.mark.parametrize("under_anomaly", [True, False])
def test_read_enemy_anomaly_active_forwards_boolean_once(
    *,
    under_anomaly: bool,
) -> None:
    dynamic = _EnemyDynamicProbe(under_anomaly=under_anomaly)
    enemy = SimpleNamespace(dynamic=dynamic)

    assert read_enemy_anomaly_active(enemy) is under_anomaly
    assert dynamic.calls == 1
