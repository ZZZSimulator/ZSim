from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast

import pytest

import zsim.simulator.simulator_class as simulator_class
from zsim.sim_progress.data_struct.planned_queue import PlannedEventQueue
from zsim.sim_progress.ScheduledEvent.buff_runtime import BuffRuntimeState
from zsim.sim_progress.SimulationEngine import (
    PlannedEventQueueWakeupSource,
    StopTickWakeupSource,
)
from zsim.simulator.simulator_class import (
    EnemySpecialStateWakeupSource,
    LoadMissionWakeupSource,
    Simulator,
)


class _DueEvent:
    def __init__(self, execute_tick: int) -> None:
        self.execute_tick = execute_tick


def _minimal_runtime_state() -> BuffRuntimeState:
    return BuffRuntimeState(
        template_registry={"alpha": {}, "enemy": {}},
        pending_queue={"alpha": [], "enemy": []},
        active_store={"alpha": [], "enemy": []},
        enemy_mirror=[],
    )


def test_main_loop_can_jump_to_next_planned_due_tick_without_conservative_source(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, Any]] = []
    events: list[Any] = [_DueEvent(5)]
    planned_queue = PlannedEventQueue(
        get_events=lambda: events,
        set_events=lambda new_events: events.__setitem__(slice(None), new_events),
    )

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
            return cls(kwargs["tick"])

        def __init__(self, tick: int) -> None:
            self.tick = tick

        def event_start(self) -> None:
            calls.append(("event_start", self.tick))
            events[:] = [
                event
                for event in events
                if getattr(event, "execute_tick", self.tick + 1) > self.tick
            ]

    sim = cast(Any, Simulator())
    sim.tick = 0
    sim.buff_runtime_state = _minimal_runtime_state()
    sim.schedule_data = SimpleNamespace(
        enemy=object(),
        planned_event_queue=planned_queue,
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
        sim,
        "_main_loop_wakeup_sources",
        lambda stop_tick, buff_runtime=None: [
            PlannedEventQueueWakeupSource(planned_queue),
            StopTickWakeupSource(stop_tick),
        ],
    )
    monkeypatch.setattr(
        simulator_class,
        "DamageEventJudge",
        lambda *_, **__: calls.append(("damage", None)),
    )
    monkeypatch.setattr(simulator_class, "ScE", FakeScheduledEvent)
    monkeypatch.setattr(
        simulator_class,
        "stop_report_threads",
        lambda: calls.append(("stop", None)),
    )

    sim.main_loop(stop_tick=6, use_api=True)

    assert [tick for phase, tick in calls if phase == "update"] == [0, 5, 6]
    assert [tick for phase, tick in calls if phase == "preload"] == [0, 5, 6]
    assert 1 not in [tick for phase, tick in calls if phase == "update"]
    assert ("scheduled", 5) in calls
    assert ("stop", None) in calls


def test_default_main_loop_wakeup_sources_do_not_include_legacy_conservative_source() -> None:
    sim = cast(Any, Simulator())
    events: list[Any] = []
    sim.schedule_data = SimpleNamespace(
        enemy=SimpleNamespace(dynamic=SimpleNamespace(stun=False)),
        planned_event_queue=PlannedEventQueue(
            get_events=lambda: events,
            set_events=lambda new_events: events.__setitem__(slice(None), new_events),
        ),
    )
    sim.preload = SimpleNamespace(
        preload_data=SimpleNamespace(
            preload_action_list_before_confirm=[],
            personal_node_stack={},
            current_node_stack=[],
        )
    )
    sim.char_data = SimpleNamespace(char_obj_list=[])
    sim.load_data = SimpleNamespace(load_mission_dict={})

    source_names = [
        source.name
        for source in sim._main_loop_wakeup_sources(
            100,
            buff_runtime=None,
        )
    ]

    assert "legacy-hidden-tick-dependencies" not in source_names
    assert source_names == [
        "planned-event-queue",
        "load-mission",
        "preload-action",
        "character-resource",
        "enemy-stun",
        "enemy-special-state",
        "stop-tick",
    ]


def test_main_loop_wakeup_sources_include_processed_event_followup() -> None:
    sim = cast(Any, Simulator())
    events: list[Any] = []
    sim.tick = 4095
    sim.schedule_data = SimpleNamespace(
        enemy=SimpleNamespace(dynamic=SimpleNamespace(stun=False)),
        planned_event_queue=PlannedEventQueue(
            get_events=lambda: events,
            set_events=lambda new_events: events.__setitem__(slice(None), new_events),
        ),
        processed_state_this_tick=True,
    )
    sim.preload = SimpleNamespace(
        preload_data=SimpleNamespace(
            preload_action_list_before_confirm=[],
            personal_node_stack={},
            current_node_stack=[],
        )
    )
    sim.char_data = SimpleNamespace(char_obj_list=[])
    sim.load_data = SimpleNamespace(load_mission_dict={})

    source = next(
        source
        for source in sim._main_loop_wakeup_sources(10000, buff_runtime=None)
        if source.name == "processed-event-followup"
    )

    assert source.next_wakeup_tick(4095) == 4096


def test_main_loop_wakeup_sources_pass_apl_resource_thresholds() -> None:
    sim = cast(Any, Simulator())
    seen: dict[str, Any] = {}

    def next_resource_wakeup_tick(
        current_tick: int,
        *,
        thresholds: Any = None,
    ) -> int:
        seen["thresholds"] = thresholds
        return current_tick + 1

    char = SimpleNamespace(CID=1361, next_resource_wakeup_tick=next_resource_wakeup_tick)
    apl_condition = SimpleNamespace(
        check_target="1361",
        check_stat="energy",
        check_value=60,
    )
    apl_unit = SimpleNamespace(
        sub_conditions_unit_list=[apl_condition],
        builtin_percond_list=[],
    )
    sim.preload = SimpleNamespace(
        preload_data=SimpleNamespace(
            preload_action_list_before_confirm=[],
            personal_node_stack={},
            current_node_stack=[],
        ),
        strategy=SimpleNamespace(
            apl_engine=SimpleNamespace(
                apl=SimpleNamespace(apl_operator=SimpleNamespace(apl_unit_inventory={1: apl_unit}))
            )
        ),
    )
    sim.char_data = SimpleNamespace(char_obj_list=[char])
    sim.load_data = SimpleNamespace(load_mission_dict={})
    sim.schedule_data = SimpleNamespace(
        enemy=SimpleNamespace(
            dynamic=SimpleNamespace(stun=False),
            special_state_manager=SimpleNamespace(observers={}),
        ),
        planned_event_queue=PlannedEventQueue(
            get_events=lambda: [],
            set_events=lambda new_events: None,
        ),
    )

    source = next(
        source
        for source in sim._main_loop_wakeup_sources(100, buff_runtime=None)
        if source.name == "character-resource"
    )

    assert source.next_wakeup_tick(10) == 11
    assert seen["thresholds"].energy == (60.0,)


def test_enemy_special_state_wakeup_source_uses_registered_state_tick() -> None:
    state = SimpleNamespace(next_wakeup_tick=lambda current_tick: current_tick + 12)
    duplicate_state = state
    enemy = SimpleNamespace(
        special_state_manager=SimpleNamespace(
            observers={
                "before": [state],
                "character": [duplicate_state],
            }
        )
    )

    source = EnemySpecialStateWakeupSource(enemy)

    assert source.next_wakeup_tick(20) == 32


def test_load_mission_wakeup_source_uses_next_mission_hit_tick() -> None:
    mission = SimpleNamespace(
        mission_dict={
            12.5: "hit",
            30.0: "end",
        },
        mission_end_tick=30,
    )
    source = LoadMissionWakeupSource({"mission": mission})

    assert source.next_wakeup_tick(10) == 13
