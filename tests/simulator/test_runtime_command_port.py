from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast

import pytest

import zsim.sim_progress.ScheduledEvent as scheduled_event_module
from zsim.sim_progress.ScheduledEvent import runtime_command as runtime_command_module
from zsim.sim_progress.ScheduledEvent.buff_runtime import BuffRuntimeState
from zsim.sim_progress.ScheduledEvent.runtime_command import (
    DefaultRuntimeCommandAdapter,
    create_runtime_command_port,
)


def _runtime_state_for_test() -> BuffRuntimeState:
    return BuffRuntimeState(
        template_registry={"alpha": {}, "enemy": {}},
        pending_queue={"alpha": [], "enemy": []},
        active_store={"alpha": [], "enemy": []},
        enemy_mirror=[],
    )


def test_runtime_command_module_exports_only_owner_backed_adapter() -> None:
    assert "LegacyRuntimeCommandAdapter" not in runtime_command_module.__all__
    assert not hasattr(runtime_command_module, "LegacyRuntimeCommandAdapter")
    assert not hasattr(runtime_command_module, "legacy_update_anomaly")


def test_runtime_command_factory_requires_buff_runtime_state() -> None:
    data = SimpleNamespace(char_obj_list=[])
    factory = cast(Any, create_runtime_command_port)

    with pytest.raises(TypeError):
        factory(
            data=data,
            action_stack=object(),
            sim_instance=object(),
        )


def test_runtime_command_factory_returns_default_adapter_for_owner_state() -> None:
    data = SimpleNamespace(char_obj_list=[])
    runtime_state = _runtime_state_for_test()

    port = create_runtime_command_port(
        data=data,
        action_stack=object(),
        sim_instance=cast(Any, object()),
        buff_runtime_state=runtime_state,
    )

    assert isinstance(port, DefaultRuntimeCommandAdapter)


def test_update_anomaly_uses_runtime_context_without_active_store_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}
    runtime_context = SimpleNamespace(buff_runtime_view=object())

    def fake_create_context(**kwargs: Any) -> object:
        captured["context_kwargs"] = kwargs
        return runtime_context

    def fake_run_update_anomaly(**kwargs: Any) -> None:
        captured["update_kwargs"] = kwargs

    monkeypatch.setattr(
        runtime_command_module,
        "create_anomaly_runtime_context",
        fake_create_context,
    )
    monkeypatch.setattr(runtime_command_module, "run_update_anomaly", fake_run_update_anomaly)

    data = SimpleNamespace(char_obj_list=["char"])
    runtime_state = _runtime_state_for_test()
    runtime_view = cast(Any, object())
    sim_instance = cast(Any, object())
    enemy = object()
    skill_node = SimpleNamespace(element_type=3)
    port = create_runtime_command_port(
        data=data,
        action_stack=object(),
        sim_instance=sim_instance,
        buff_runtime_state=runtime_state,
        buff_runtime_view=runtime_view,
    )

    port.update_anomaly(
        element_type=3,
        enemy=enemy,
        tick=42,
        skill_node=skill_node,
    )

    assert captured["context_kwargs"]["sim_instance"] is sim_instance
    assert captured["context_kwargs"]["enemy"] is enemy
    assert captured["context_kwargs"]["buff_runtime_view"] is runtime_view
    assert captured["update_kwargs"]["dynamic_buff_dict"] is None
    assert captured["update_kwargs"]["runtime_context"] is runtime_context


def test_settle_buffs_routes_through_runtime_state_facade() -> None:
    calls: list[dict[str, Any]] = []

    class Facade:
        def settle_schedule_buffs(self, **kwargs: Any) -> None:
            calls.append(kwargs)

    runtime_state = _runtime_state_for_test()
    runtime_state.create_facade = cast(Any, lambda: Facade())  # type: ignore[method-assign]
    data = SimpleNamespace(char_obj_list=[])
    sim_instance = cast(Any, object())
    enemy = object()
    skill_node = object()
    anomaly_bar = object()
    port = create_runtime_command_port(
        data=data,
        action_stack=object(),
        sim_instance=sim_instance,
        buff_runtime_state=runtime_state,
    )

    port.settle_buffs(
        tick=7,
        enemy=enemy,
        skill_node=skill_node,
        anomaly_bar=anomaly_bar,
    )

    assert calls == [
        {
            "tick": 7,
            "enemy": enemy,
            "sim_instance": sim_instance,
            "skill_node": skill_node,
            "anomaly_bar": anomaly_bar,
        }
    ]


def test_scheduled_event_from_runtime_state_binds_schedule_data_to_runtime_owners() -> None:
    runtime_state = _runtime_state_for_test()
    schedule_data = SimpleNamespace(enemy=object(), char_obj_list=[])

    scheduled_event = scheduled_event_module.ScheduledEvent.from_runtime_state(
        schedule_data=schedule_data,
        tick=1,
        action_stack=object(),
        buff_runtime_state=runtime_state,
        sim_instance=cast(Any, object()),
    )

    assert scheduled_event.buff_runtime_state is runtime_state
    assert schedule_data.dynamic_buff is runtime_state.active_store_owner().mutable_stores()
    assert schedule_data.loading_buff is runtime_state.pending_queue_owner().mutable_queues()
    assert not hasattr(scheduled_event, "exist_buff_dict")
