from __future__ import annotations

from types import SimpleNamespace

from zsim.sim_progress.ScheduledEvent.buff_runtime import (
    BuffRuntimeState,
    BuffTimeRelatedWakeupSource,
    DefaultBuffRuntimeFacade,
)


def _buff(
    *,
    index: str = "Buff-测试",
    endticks: int = 20,
    alltime: bool = False,
    simple_exit_logic: bool = True,
    individual_settled: bool = False,
    built_in_buff_box: list[tuple[int, int]] | None = None,
    logic: object | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        ft=SimpleNamespace(
            index=index,
            simple_exit_logic=simple_exit_logic,
            alltime=alltime,
            individual_settled=individual_settled,
        ),
        dy=SimpleNamespace(
            endticks=endticks,
            built_in_buff_box=[] if built_in_buff_box is None else built_in_buff_box,
        ),
        logic=logic,
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


def test_buff_duration_wakeup_uses_first_tick_after_simple_end() -> None:
    facade = _facade(_buff(endticks=20))

    assert facade.next_time_related_wakeup_tick(current_tick=10, enemy=_enemy()) == 21


def test_buff_duration_wakeup_keeps_complex_exit_logic_on_next_tick() -> None:
    facade = _facade(_buff(simple_exit_logic=False))

    assert facade.next_time_related_wakeup_tick(current_tick=10, enemy=_enemy()) == 11


def test_buff_duration_wakeup_skips_event_settled_complex_exit_polling() -> None:
    facade = _facade(
        _buff(
            index="Buff-角色-仪玄-4画-静心",
            simple_exit_logic=False,
            logic=SimpleNamespace(record=SimpleNamespace(c4_counter=1)),
        )
    )

    assert facade.next_time_related_wakeup_tick(current_tick=10, enemy=_enemy()) is None


def test_buff_duration_wakeup_keeps_event_settled_exit_when_state_flips() -> None:
    facade = _facade(
        _buff(
            index="Buff-角色-耀佳音-咏叹华彩",
            simple_exit_logic=False,
            logic=SimpleNamespace(
                record=SimpleNamespace(
                    char=SimpleNamespace(idyllic_cadenza=False),
                )
            ),
        )
    )

    assert facade.next_time_related_wakeup_tick(current_tick=10, enemy=_enemy()) == 11


def test_buff_duration_wakeup_uses_individual_stack_expiry() -> None:
    facade = _facade(
        _buff(
            individual_settled=True,
            built_in_buff_box=[(1, 30), (3, 15)],
        )
    )

    assert facade.next_time_related_wakeup_tick(current_tick=10, enemy=_enemy()) == 16


def test_buff_time_related_source_returns_none_when_facade_lacks_contract() -> None:
    source = BuffTimeRelatedWakeupSource(runtime_facade=object(), enemy=_enemy())

    assert source.next_wakeup_tick(10) is None
