from __future__ import annotations

from types import SimpleNamespace

from zsim.sim_progress.Dot.BaseDot import Dot
from zsim.sim_progress.Update.Update_Buff import next_dot_or_anomaly_wakeup_tick


def _dot(*, end_ticks: int, complex_exit_logic: bool = False) -> Dot:
    dot = Dot(None)
    dot.ft.index = "dot"
    dot.ft.complex_exit_logic = complex_exit_logic
    dot.dy.end_ticks = end_ticks
    return dot


def _enemy(*dots: Dot, anomaly_bars: dict[int, object] | None = None) -> SimpleNamespace:
    return SimpleNamespace(
        dynamic=SimpleNamespace(dynamic_dot_list=list(dots)),
        anomaly_bars_dict={} if anomaly_bars is None else anomaly_bars,
    )


def test_dot_wakeup_uses_dot_end_tick() -> None:
    enemy = _enemy(_dot(end_ticks=40))

    assert next_dot_or_anomaly_wakeup_tick(enemy, 10) == 40


def test_complex_dot_wakeup_stays_next_tick() -> None:
    enemy = _enemy(_dot(end_ticks=40, complex_exit_logic=True))

    assert next_dot_or_anomaly_wakeup_tick(enemy, 10) == 11


def test_active_anomaly_wakeup_uses_first_tick_after_duration() -> None:
    enemy = _enemy(
        anomaly_bars={
            3: SimpleNamespace(
                active=True,
                last_active=100,
                max_duration=600,
            )
        }
    )

    assert next_dot_or_anomaly_wakeup_tick(enemy, 120) == 701


def test_dot_anomaly_wakeup_returns_none_when_idle() -> None:
    assert next_dot_or_anomaly_wakeup_tick(_enemy(), 10) is None
