from __future__ import annotations

import pytest

from zsim.sim_progress.SimulationEngine import (
    ConservativeTickWakeupSource,
    FixedTickWakeupSource,
    SimulationClock,
    StopTickWakeupSource,
)


class _BadWakeupSource:
    name = "bad"

    def next_wakeup_tick(self, current_tick: int) -> int:
        return current_tick


def test_simulation_clock_advances_to_earliest_future_wakeup() -> None:
    clock = SimulationClock()

    assert (
        clock.next_wakeup_tick(
            current_tick=10,
            wakeup_sources=[
                FixedTickWakeupSource(name="later", tick=30),
                FixedTickWakeupSource(name="earlier", tick=12),
                FixedTickWakeupSource(name="idle", tick=None),
            ],
        )
        == 12
    )


def test_stop_tick_wakeup_preserves_integer_stop_boundary() -> None:
    assert StopTickWakeupSource(20).next_wakeup_tick(19) == 20
    assert StopTickWakeupSource(20).next_wakeup_tick(20) is None


def test_conservative_wakeup_is_explicit_next_tick_source() -> None:
    assert ConservativeTickWakeupSource("apl").next_wakeup_tick(7) == 8


def test_simulation_clock_rejects_non_future_source() -> None:
    clock = SimulationClock()

    with pytest.raises(ValueError, match="non-future tick"):
        clock.next_wakeup_tick(
            current_tick=10,
            wakeup_sources=[_BadWakeupSource()],
        )


def test_simulation_clock_requires_future_wakeup() -> None:
    clock = SimulationClock()

    with pytest.raises(ValueError, match="至少需要一个未来"):
        clock.next_wakeup_tick(
            current_tick=10,
            wakeup_sources=[FixedTickWakeupSource(name="idle", tick=None)],
        )
