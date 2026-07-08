from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast

import pytest

import zsim.simulator.simulator_class as simulator_class
from zsim.sim_progress.Buff.BuffLoad import BuffLoadLoop
from zsim.sim_progress.data_struct.planned_queue import PlannedEventQueue
from zsim.sim_progress.ScheduledEvent.buff_runtime import (
    BuffRuntimeState,
    BuffTemplateRegistry,
    PendingBuffQueue,
)
from zsim.simulator.simulator_class import Simulator


def _planned_queue() -> PlannedEventQueue:
    events: list[Any] = []
    return PlannedEventQueue(
        get_events=lambda: events, set_events=lambda new: events.__setitem__(slice(None), new)
    )


def _minimal_runtime_state() -> BuffRuntimeState:
    return BuffRuntimeState(
        template_registry={"alpha": {}, "enemy": {}},
        pending_queue={"alpha": [], "enemy": []},
        active_store={"alpha": [], "enemy": []},
        enemy_mirror=[],
    )


def test_create_buff_runtime_facade_uses_existing_runtime_state_owner() -> None:
    sim = cast(Any, Simulator())
    sim._buff_runtime_rebuild_counts = {}
    sim.buff_runtime_state = _minimal_runtime_state()

    facade = sim._create_buff_runtime_facade()

    assert facade is not None
    assert sim._buff_runtime_rebuild_counts["default_buff_runtime_facade"] == 1


def test_main_loop_uses_runtime_facade_and_scheduled_event_runtime_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, Any]] = []

    class RuntimeFacade:
        def update_time_related_effects(self, *, tick: int, enemy: Any) -> None:
            calls.append(("update", tick))

        def load_pending_buffs(self, **kwargs: Any) -> dict[str, list[Any]]:
            calls.append(("load", kwargs["time_now"]))
            return {}

        def activate_pending_buffs(self, *, timenow: float) -> dict[str, list[Any]]:
            calls.append(("activate", timenow))
            return {}

    class FakeScheduledEvent:
        @classmethod
        def from_runtime_state(cls, **kwargs: Any) -> "FakeScheduledEvent":
            calls.append(("scheduled", kwargs["tick"]))
            assert kwargs["buff_runtime_state"] is sim.buff_runtime_state
            return cls()

        def event_start(self) -> None:
            calls.append(("event_start", None))

    sim = cast(Any, Simulator())
    sim.tick = 0
    sim.buff_runtime_state = _minimal_runtime_state()
    sim.schedule_data = SimpleNamespace(
        enemy=object(),
        planned_event_queue=_planned_queue(),
        processed_state_this_tick=False,
        reset_processed_event=lambda: calls.append(("reset_processed_event", None)),
    )
    sim.preload = SimpleNamespace(
        preload_data=SimpleNamespace(
            preload_action=[],
            preload_action_list_before_confirm=[],
            personal_node_stack={},
            current_node_stack=[],
        ),
        do_preload=lambda *args, **kwargs: calls.append(("preload", args[0])),
    )
    sim.init_data = SimpleNamespace(name_box=["alpha"])
    sim.char_data = SimpleNamespace(char_obj_list=[])
    sim.load_data = SimpleNamespace(
        load_mission_dict={},
        name_dict={},
        action_stack=object(),
        all_name_order_box={"alpha": ["alpha", "enemy"]},
    )

    monkeypatch.setattr(sim, "_create_buff_runtime_facade", lambda: RuntimeFacade())
    monkeypatch.setattr(
        simulator_class, "DamageEventJudge", lambda *_, **__: calls.append(("damage", None))
    )
    monkeypatch.setattr(simulator_class, "ScE", FakeScheduledEvent)
    monkeypatch.setattr(
        simulator_class, "stop_report_threads", lambda: calls.append(("stop", None))
    )

    sim.main_loop(stop_tick=1, use_api=True)

    assert calls[:6] == [
        ("update", 0),
        ("preload", 0),
        ("damage", None),
        ("load", 0),
        ("activate", 0),
        ("scheduled", 0),
    ]
    assert ("event_start", None) in calls
    assert ("stop", None) in calls


def test_buff_load_loop_requires_runtime_pending_queue_owner() -> None:
    registry = BuffTemplateRegistry({"alpha": {}, "enemy": {}})

    with pytest.raises(TypeError, match="pending_queue_owner"):
        BuffLoadLoop(
            1,
            {},
            registry,
            ["alpha"],
            {"alpha": [], "enemy": []},
            {"alpha": ["alpha", "enemy"]},
            sim_instance=object(),
        )


def test_buff_load_loop_resets_and_returns_owner_backed_pending_queue() -> None:
    registry = BuffTemplateRegistry({"alpha": {}, "enemy": {}})
    pending = PendingBuffQueue({"alpha": ["old"], "enemy": ["old-enemy"]})
    sim_instance = SimpleNamespace()

    result = BuffLoadLoop(
        1,
        {},
        registry,
        ["alpha"],
        pending,
        {"alpha": ["alpha", "enemy"]},
        sim_instance=sim_instance,
    )

    assert result is pending.mutable_queues()
    assert result == {"alpha": [], "enemy": []}
