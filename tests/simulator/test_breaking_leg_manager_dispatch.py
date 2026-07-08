from __future__ import annotations

import inspect
import sys
from importlib import import_module
from types import SimpleNamespace
from typing import Any, cast

import pytest

import zsim.define as define_module

sys.modules.setdefault("define", define_module)

import zsim.sim_progress.Buff as buff_module
from zsim.sim_progress.data_struct.planned_queue import PlannedEventQueue
from zsim.sim_progress.data_struct.schedule_dispatch import (
    ScheduledEventEmitterProvider,
    ScheduleDispatchPort,
)
from zsim.sim_progress.data_struct.sp_update_data import ScheduleRefreshData

breaking_module = import_module("zsim.sim_progress.Enemy.EnemyUniqueMechanic.BreakingLegManager")
BreakingLegManager = breaking_module.BreakingLegManager
BreakingEvent = breaking_module.BreakingEvent
SingleLeg = breaking_module.SingleLeg


class _FailFastEventList(list):
    def append(self, item):
        raise AssertionError("BreakingEvent should publish refresh data via dispatch port")


def _attach_planned_queue(schedule_data: SimpleNamespace) -> None:
    schedule_data.planned_event_queue = PlannedEventQueue(
        get_events=lambda: schedule_data.event_list,
        set_events=lambda events: setattr(schedule_data, "event_list", events),
    )


class _RecordingDispatchPort:
    def __init__(self, call_order: list[str]) -> None:
        self.call_order = call_order
        self.events: list[object] = []

    def publish_scheduled(self, event: object) -> None:
        self.call_order.append("publish")
        self.events.append(event)


class _EnemyDynamic:
    stun = False

    def get_status(self) -> dict[str, object]:
        return {}


class _FakeEnemy:
    def __init__(self, sim_instance: object, call_order: list[str]) -> None:
        self.max_stun = 2000
        self.max_HP = 100000
        self.sim_instance = sim_instance
        self.dynamic = _EnemyDynamic()
        self.call_order = call_order
        self.stun_updates: list[float] = []
        self.hp_updates: list[float] = []
        self.stun_judge_calls: list[tuple[int, object]] = []
        self._Enemy__HP_update = self._hp_update

    def update_stun(self, stun_value: float) -> None:
        self.call_order.append("update_stun")
        self.stun_updates.append(stun_value)

    def stun_judge(self, tick: int, *, single_hit: object) -> None:
        self.call_order.append("stun_judge")
        self.stun_judge_calls.append((tick, single_hit))

    def _hp_update(self, dmg_value: float) -> None:
        self.call_order.append("hp_update")
        self.hp_updates.append(dmg_value)


def _patch_breaking_dependencies(
    monkeypatch: pytest.MonkeyPatch,
    *,
    call_order: list[str],
) -> list[tuple[int, object]]:
    find_calls: list[tuple[int, object]] = []

    def fake_find_char_from_cid(char_cid: int, found_sim_instance: object) -> object:
        find_calls.append((char_cid, found_sim_instance))
        return SimpleNamespace(NAME="安比")

    def fake_report_dmg_result(**kwargs: Any) -> None:
        call_order.append("report")
        assert kwargs["tick"] == 120
        assert kwargs["skill_tag"] == "破腿"
        assert kwargs["dmg_expect"] == 5500
        assert kwargs["stun"] == 300

    monkeypatch.setattr(buff_module, "find_char_from_CID", fake_find_char_from_cid)
    monkeypatch.setattr(breaking_module, "report_dmg_result", fake_report_dmg_result)
    return find_calls


def test_breaking_event_publishes_part_break_refresh_before_same_tick_side_effects(
    monkeypatch: pytest.MonkeyPatch,
):
    call_order: list[str] = []
    dispatch_port = _RecordingDispatchPort(call_order)
    schedule_data = SimpleNamespace(event_list=_FailFastEventList())
    sim_instance = SimpleNamespace(schedule_data=schedule_data)
    enemy = _FakeEnemy(sim_instance, call_order)
    single_hit = SimpleNamespace(skill_tag="1301_TEST_1")
    find_calls = _patch_breaking_dependencies(
        monkeypatch,
        call_order=call_order,
    )

    BreakingEvent(
        enemy,
        scheduled_event_emitter_provider=ScheduledEventEmitterProvider(
            lambda: cast(ScheduleDispatchPort, dispatch_port)
        ),
    ).active(single_hit, tick=120)

    assert call_order == ["publish", "update_stun", "stun_judge", "hp_update", "report"]
    assert len(dispatch_port.events) == 1
    refresh_data = dispatch_port.events[0]
    assert isinstance(refresh_data, ScheduleRefreshData)
    assert refresh_data.sp_target == ("安比",)
    assert refresh_data.decibel_target == ("安比",)
    assert refresh_data.decibel_value == 1000
    assert schedule_data.event_list == []
    assert enemy.stun_updates == [300]
    assert enemy.stun_judge_calls == [(120, single_hit)]
    assert enemy.hp_updates == [5500]
    assert find_calls == [(1301, sim_instance)]


def test_breaking_event_reuses_cached_char_for_repeated_part_break_rewards(
    monkeypatch: pytest.MonkeyPatch,
):
    call_order: list[str] = []
    dispatch_port = _RecordingDispatchPort(call_order)
    schedule_data = SimpleNamespace(event_list=_FailFastEventList())
    sim_instance = SimpleNamespace(schedule_data=schedule_data)
    enemy = _FakeEnemy(sim_instance, call_order)
    event = BreakingEvent(
        enemy,
        scheduled_event_emitter_provider=ScheduledEventEmitterProvider(
            lambda: cast(ScheduleDispatchPort, dispatch_port)
        ),
    )
    find_calls = _patch_breaking_dependencies(
        monkeypatch,
        call_order=call_order,
    )

    event.update_decibel(SimpleNamespace(skill_tag="1301_TEST_1"))
    event.update_decibel(SimpleNamespace(skill_tag="1301_TEST_2"))

    assert len(dispatch_port.events) == 2
    assert all(isinstance(event, ScheduleRefreshData) for event in dispatch_port.events)
    assert find_calls == [(1301, sim_instance)]
    assert schedule_data.event_list == []


def test_breaking_leg_manager_injects_rebound_safe_emitter_provider(
    monkeypatch: pytest.MonkeyPatch,
):
    call_order: list[str] = []
    old_event_list: list[object] = []
    new_event_list: list[object] = []
    schedule_data = SimpleNamespace(event_list=old_event_list)
    _attach_planned_queue(schedule_data)
    sim_instance = SimpleNamespace(schedule_data=schedule_data)
    enemy = _FakeEnemy(sim_instance, call_order)
    manager = BreakingLegManager(enemy)
    find_calls = _patch_breaking_dependencies(
        monkeypatch,
        call_order=call_order,
    )

    event = manager.leg_group[0].event
    event.update_decibel(SimpleNamespace(skill_tag="1301_TEST_1"))
    schedule_data.event_list = new_event_list
    event.update_decibel(SimpleNamespace(skill_tag="1301_TEST_2"))

    assert manager.leg_group[0].event._scheduled_event_emitter_provider is (
        manager._scheduled_event_emitter_provider
    )
    assert len(old_event_list) == 1
    assert len(new_event_list) == 1
    assert all(
        isinstance(event, ScheduleRefreshData) for event in [old_event_list[0], new_event_list[0]]
    )
    assert find_calls == [(1301, sim_instance)]


def test_breaking_event_family_moves_provider_fallback_out_of_producer() -> None:
    breaking_event_source = inspect.getsource(BreakingEvent)
    single_leg_source = inspect.getsource(SingleLeg)
    manager_source = inspect.getsource(BreakingLegManager)

    assert "from_sim_instance" not in breaking_event_source
    assert "scheduled_event_emitter_provider or" not in breaking_event_source
    assert "scheduled_event_emitter_provider=scheduled_event_emitter_provider" in single_leg_source
    assert "ScheduledEventEmitterProvider.from_sim_instance_getter" in manager_source


def test_non_buffxlogic_producers_receive_emitters_not_dispatch_ports():
    producer_module_names = [
        "zsim.sim_progress.Character.Yuzuha",
        "zsim.sim_progress.Enemy.EnemyUniqueMechanic.BreakingLegManager",
        "zsim.sim_progress.data_struct.DecibelManager.DecibelManagerClass",
        "zsim.sim_progress.data_struct.QuickAssistSystem",
        "zsim.sim_progress.data_struct.PolarizedAssaultEventClass",
        "zsim.sim_progress.data_struct.SchedulePreload",
        "zsim.sim_progress.data_struct.BattleEventListener.AliceDotTriggerListener",
    ]
    forbidden_terms = (
        "_create_dispatch_port",
        "create_schedule_dispatch_port",
        "ScheduleDispatchPort",
    )

    for module_name in producer_module_names:
        source = inspect.getsource(import_module(module_name))
        assert "ScheduledEventEmitterProvider" in source
        for forbidden_term in forbidden_terms:
            assert forbidden_term not in source
