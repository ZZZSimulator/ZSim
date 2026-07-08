from __future__ import annotations

from types import SimpleNamespace

from zsim.sim_progress.Buff.BuffXLogic._preparation_helpers import (
    prepare_with_context,
)


def _logic_probe() -> SimpleNamespace:
    return SimpleNamespace(
        buff_instance=SimpleNamespace(sim_instance=SimpleNamespace(buff_runtime_state=object())),
        buff_0=SimpleNamespace(history=SimpleNamespace(record=object())),
    )


def test_prepare_with_context_reuses_successful_preparation_signature() -> None:
    logic = _logic_probe()
    builder_calls = 0
    preparation_calls = 0

    def context_builder(buff_instance: object) -> object:
        nonlocal builder_calls
        builder_calls += 1
        return object()

    def check_preparation_func(**kwargs: object) -> None:
        nonlocal preparation_calls
        preparation_calls += 1

    prepare_with_context(
        logic,
        check_preparation_func=check_preparation_func,
        context_builder=context_builder,
        enemy=1,
    )
    prepare_with_context(
        logic,
        check_preparation_func=check_preparation_func,
        context_builder=context_builder,
        enemy=1,
    )

    assert builder_calls == 1
    assert preparation_calls == 1


def test_prepare_with_context_invalidates_when_runtime_state_changes() -> None:
    logic = _logic_probe()
    preparation_calls = 0

    def check_preparation_func(**kwargs: object) -> None:
        nonlocal preparation_calls
        preparation_calls += 1

    prepare_with_context(
        logic,
        check_preparation_func=check_preparation_func,
        context_builder=lambda buff_instance: object(),
        enemy=1,
    )
    logic.buff_instance.sim_instance.buff_runtime_state = object()
    prepare_with_context(
        logic,
        check_preparation_func=check_preparation_func,
        context_builder=lambda buff_instance: object(),
        enemy=1,
    )

    assert preparation_calls == 2


def test_prepare_with_context_does_not_skip_missing_record() -> None:
    logic = _logic_probe()
    logic.buff_0.history.record = None
    preparation_calls = 0

    def check_preparation_func(**kwargs: object) -> None:
        nonlocal preparation_calls
        preparation_calls += 1

    prepare_with_context(
        logic,
        check_preparation_func=check_preparation_func,
        context_builder=lambda buff_instance: object(),
        enemy=1,
    )
    prepare_with_context(
        logic,
        check_preparation_func=check_preparation_func,
        context_builder=lambda buff_instance: object(),
        enemy=1,
    )

    assert preparation_calls == 2
