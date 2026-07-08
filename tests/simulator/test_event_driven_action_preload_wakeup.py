from __future__ import annotations

from types import SimpleNamespace

from zsim.sim_progress.Preload.wakeup import PreloadWakeupSource


class _Stack:
    def __init__(self, nodes: list[object]) -> None:
        self.stack = nodes

    def __iter__(self):
        return iter(self.stack)


def _node(
    *,
    preload_tick: int,
    end_tick: int,
    swap_cancel_ticks: int = 0,
    ticks: int = 100,
    active_generation: bool = True,
    labels: list[str] | None = None,
    tick_list: list[float] | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        preload_tick=preload_tick,
        end_tick=end_tick,
        active_generation=active_generation,
        tick_list=tick_list or [],
        skill=SimpleNamespace(
            swap_cancel_ticks=swap_cancel_ticks,
            ticks=ticks,
            labels=labels,
        ),
    )


def _preload(*nodes: object, pending_confirm: bool = False) -> SimpleNamespace:
    preload_data = SimpleNamespace(
        preload_action_list_before_confirm=[("skill", True, 0)] if pending_confirm else [],
        personal_node_stack={1371: _Stack(list(nodes))} if nodes else {},
        current_node_stack=_Stack(list(nodes)),
    )
    return SimpleNamespace(preload_data=preload_data)


def test_preload_wakeup_uses_pending_confirm_as_next_tick() -> None:
    source = PreloadWakeupSource(_preload(pending_confirm=True))

    assert source.next_wakeup_tick(20) == 21


def test_preload_wakeup_uses_pending_external_due_tick() -> None:
    node = _node(
        preload_tick=10,
        end_tick=100,
        active_generation=False,
        labels=["additional_damage"],
    )
    preload_data = SimpleNamespace(
        preload_action_list_before_confirm=[("skill", True, 0, 44)],
        personal_node_stack={1371: _Stack([node])},
        current_node_stack=_Stack([node]),
    )
    source = PreloadWakeupSource(SimpleNamespace(preload_data=preload_data))

    assert source.next_wakeup_tick(20) == 44


def test_preload_wakeup_uses_next_action_end_tick() -> None:
    source = PreloadWakeupSource(
        _preload(
            _node(
                preload_tick=10,
                end_tick=50,
                active_generation=False,
                labels=["additional_damage"],
            )
        )
    )

    assert source.next_wakeup_tick(20) == 50


def test_preload_wakeup_uses_next_action_start_tick() -> None:
    source = PreloadWakeupSource(
        _preload(
            _node(
                preload_tick=30,
                end_tick=80,
                active_generation=False,
            )
        )
    )

    assert source.next_wakeup_tick(20) == 30


def test_preload_wakeup_uses_next_skill_hit_tick() -> None:
    source = PreloadWakeupSource(
        _preload(
            _node(
                preload_tick=10,
                end_tick=100,
                tick_list=[20.25, 45.0],
            )
        )
    )

    assert source.next_wakeup_tick(20) == 21


def test_preload_wakeup_uses_swap_cancel_release_tick() -> None:
    source = PreloadWakeupSource(
        _preload(
            _node(
                preload_tick=10,
                end_tick=100,
                swap_cancel_ticks=5,
                ticks=20,
            )
        )
    )

    assert source.next_wakeup_tick(12) == 21


def test_preload_wakeup_uses_inactive_generation_swap_cancel_release_tick() -> None:
    source = PreloadWakeupSource(
        _preload(
            _node(
                preload_tick=3544,
                end_tick=3589,
                ticks=45,
                active_generation=False,
            )
        )
    )

    assert source.next_wakeup_tick(3545) == 3558


def test_preload_wakeup_uses_character_change_cd_release_tick() -> None:
    source = PreloadWakeupSource(
        _preload(
            _node(
                preload_tick=3544,
                end_tick=3589,
                ticks=45,
                active_generation=False,
                labels=["additional_damage"],
            )
        )
    )

    assert source.next_wakeup_tick(3640) == 3649


def test_preload_wakeup_bootstraps_empty_action_state() -> None:
    source = PreloadWakeupSource(_preload())

    assert source.next_wakeup_tick(0) == 1
