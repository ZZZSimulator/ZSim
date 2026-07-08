from __future__ import annotations

from types import SimpleNamespace

from zsim.sim_progress.ScheduledEvent.buff_runtime import (
    BuffRuntimeState,
    DefaultBuffRuntimeFacade,
)


def _buff(
    *,
    index: str = "Buff-Test",
    endticks: int = 20,
    alltime: bool = False,
    simple_exit_logic: bool = True,
    individual_settled: bool = False,
    built_in_buff_box: list[tuple[int, int]] | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        ft=SimpleNamespace(
            index=index,
            is_debuff=False,
            simple_exit_logic=simple_exit_logic,
            alltime=alltime,
            individual_settled=individual_settled,
        ),
        dy=SimpleNamespace(
            endticks=endticks,
            built_in_buff_box=[] if built_in_buff_box is None else built_in_buff_box,
        ),
        logic=SimpleNamespace(xexit=lambda beneficiary: False),
    )


def _facade(*buffs: object) -> DefaultBuffRuntimeFacade:
    return DefaultBuffRuntimeFacade(
        runtime_state=BuffRuntimeState(
            template_registry={"alpha": {}, "enemy": {}},
            pending_queue={"alpha": [], "enemy": []},
            active_store={"alpha": list(buffs), "enemy": []},
            enemy_mirror=[],
        )
    )


def _enemy() -> SimpleNamespace:
    return SimpleNamespace(
        dynamic=SimpleNamespace(dynamic_dot_list=[]),
        anomaly_bars_dict={},
    )


def test_active_lifecycle_due_readiness_uses_earliest_simple_end_tick() -> None:
    facade = _facade(_buff(index="late", endticks=30), _buff(index="early", endticks=12))

    assert facade.next_time_related_wakeup_tick(current_tick=10, enemy=_enemy()) == 13


def test_active_lifecycle_due_readiness_ignores_alltime_buffs() -> None:
    facade = _facade(_buff(index="alltime", alltime=True))

    assert facade.next_time_related_wakeup_tick(current_tick=10, enemy=_enemy()) is None


def test_active_lifecycle_due_readiness_keeps_complex_exit_on_conservative_path() -> None:
    facade = _facade(_buff(index="complex", simple_exit_logic=False))

    assert facade.next_time_related_wakeup_tick(current_tick=10, enemy=_enemy()) == 11


def test_active_lifecycle_due_readiness_uses_individual_stack_expiry_order() -> None:
    facade = _facade(
        _buff(
            index="stacked",
            individual_settled=True,
            built_in_buff_box=[(1, 25), (2, 15), (3, 35)],
        )
    )

    assert facade.next_time_related_wakeup_tick(current_tick=10, enemy=_enemy()) == 16
