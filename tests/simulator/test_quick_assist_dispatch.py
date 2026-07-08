from types import SimpleNamespace

import pytest

from zsim.sim_progress.Buff import JudgeTools
from zsim.sim_progress.data_struct.planned_queue import PlannedEventQueue
from zsim.sim_progress.data_struct.QuickAssistSystem import QuickAssistSystem
from zsim.sim_progress.data_struct.QuickAssistSystem.quick_assist_manager import (
    QuickAssistManager,
)


def _build_quick_assist_system():
    chars = []
    managers = {}
    for name in ("alpha", "beta", "gamma"):
        char = SimpleNamespace(NAME=name, CID=name)
        manager = QuickAssistManager(char)
        char.dynamic = SimpleNamespace(quick_assist_manager=manager)
        chars.append(char)
        managers[name] = manager
    schedule_data = SimpleNamespace(event_list=[])
    schedule_data.planned_event_queue = PlannedEventQueue(
        get_events=lambda: schedule_data.event_list,
        set_events=lambda events: setattr(schedule_data, "event_list", events),
    )
    sim_instance = SimpleNamespace(schedule_data=schedule_data)
    return QuickAssistSystem(chars, sim_instance), sim_instance, managers


def _make_skill_node(
    *,
    char_name: str,
    aid_direction: int = 0,
    aid_lag_ticks: int = 2,
    trigger_buff_level: int = 0,
):
    return SimpleNamespace(
        char_name=char_name,
        preload_tick=0,
        skill=SimpleNamespace(
            aid_direction=aid_direction,
            aid_lag_ticks=aid_lag_ticks,
            trigger_buff_level=trigger_buff_level,
        ),
    )


def _block_legacy_event_lookup(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_find_event_list(*args, **kwargs):
        raise AssertionError("QuickAssistSystem should publish via dispatch port")

    monkeypatch.setattr(JudgeTools, "find_event_list", fail_find_event_list, raising=False)


def test_force_active_quick_assist_preserves_start_then_end_queue_order(
    monkeypatch: pytest.MonkeyPatch,
):
    system, sim_instance, managers = _build_quick_assist_system()
    skill_node = _make_skill_node(char_name="alpha", aid_lag_ticks=2)

    _block_legacy_event_lookup(monkeypatch)

    system.force_active_quick_assist(10, skill_node, "beta")

    event_list = sim_instance.schedule_data.event_list

    assert [event.operation for event in event_list] == [True, False]
    assert [event.exit_mode for event in event_list] == [False, False]
    assert [event.execute_tick for event in event_list] == [12, 72]
    assert all(event.manager is managers["beta"] for event in event_list)
    assert managers["beta"].assist_event_update_tick == 10
    assert managers["beta"].last_update_node is skill_node


def test_answer_assist_publishes_immediate_end_event_via_dispatch_port(
    monkeypatch: pytest.MonkeyPatch,
):
    system, sim_instance, managers = _build_quick_assist_system()
    skill_node = _make_skill_node(char_name="alpha", aid_lag_ticks=5)

    _block_legacy_event_lookup(monkeypatch)

    system.answer_assist(10, skill_node)

    event_list = sim_instance.schedule_data.event_list

    assert len(event_list) == 1
    assert event_list[0].operation is False
    assert event_list[0].exit_mode is True
    assert event_list[0].execute_tick == 10
    assert event_list[0].manager is managers["alpha"]


def test_quick_assist_update_keeps_spawn_and_answer_event_order(
    monkeypatch: pytest.MonkeyPatch,
):
    system, sim_instance, managers = _build_quick_assist_system()
    managers["alpha"].quick_assist_available = True
    skill_node = _make_skill_node(
        char_name="alpha",
        aid_direction=1,
        aid_lag_ticks=2,
        trigger_buff_level=7,
    )

    _block_legacy_event_lookup(monkeypatch)

    system.update(
        10,
        skill_node,
        {
            "alpha": ["alpha", "beta", "gamma"],
            "beta": ["beta", "gamma", "alpha"],
            "gamma": ["gamma", "alpha", "beta"],
        },
    )

    event_list = sim_instance.schedule_data.event_list

    assert [event.manager.char.NAME for event in event_list] == ["beta", "beta", "alpha"]
    assert [event.operation for event in event_list] == [True, False, False]
    assert [event.exit_mode for event in event_list] == [False, False, True]
    assert [event.execute_tick for event in event_list] == [12, 72, 10]
