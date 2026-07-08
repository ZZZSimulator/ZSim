from __future__ import annotations

import sys
from types import SimpleNamespace
from typing import Any, cast

import pytest

import zsim.define as define_module

sys.modules.setdefault("define", define_module)

import zsim.sim_progress.Buff.BuffXLogic.YixuanCinema1Trigger as yixuan_module
from zsim.sim_progress.Buff import JudgeTools
from zsim.sim_progress.Buff.BuffXLogic.YixuanCinema1Trigger import (
    YixuanCinema1Trigger,
    YixuanCinema1TriggerRecord,
)
from zsim.sim_progress.data_struct.schedule_dispatch import (
    ScheduledEventEmitterProvider,
    ScheduleDispatchPort,
)
from zsim.sim_progress.Load import LoadingMission
from zsim.sim_progress.Preload import SkillNode


class _FailFastEventList(list):
    def append(self, item):
        raise AssertionError("YixuanCinema1Trigger should publish via dispatch port")


class _RecordingDispatchPort(ScheduleDispatchPort):
    def __init__(self, call_order: list[str]) -> None:
        self.events: list[object] = []
        self._call_order = call_order

    def publish_scheduled(self, event: object) -> None:
        self._call_order.append("publish")
        self.events.append(event)


def _block_legacy_event_lookup(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_find_event_list(*args, **kwargs):
        raise AssertionError("YixuanCinema1Trigger should not read raw event_list")

    monkeypatch.setattr(JudgeTools, "find_event_list", fail_find_event_list, raising=False)


def test_yixuan_cinema1_publishes_lightning_after_loading_mission_via_dispatch_port(
    monkeypatch: pytest.MonkeyPatch,
):
    call_order: list[str] = []
    dispatch_port = _RecordingDispatchPort(call_order)
    schedule_data = SimpleNamespace(
        event_list=_FailFastEventList(),
        change_process_state=lambda: None,
    )
    sim_instance = SimpleNamespace(tick=81, schedule_data=schedule_data)
    sub_exist_buff_dict = {"yixuan-cinema-1": object()}

    def fake_simple_start(timenow: int, sub_exist_buff_dict: dict[str, object]) -> None:
        call_order.append("simple_start")
        assert timenow == 81
        assert sub_exist_buff_dict is record.sub_exist_buff_dict

    buff_instance = SimpleNamespace(
        sim_instance=sim_instance,
        ft=SimpleNamespace(index="Buff-角色-仪玄-影画1"),
        simple_start=fake_simple_start,
    )
    logic = YixuanCinema1Trigger(
        buff_instance,
        scheduled_event_emitter_provider=ScheduledEventEmitterProvider(lambda: dispatch_port),
    )

    def fake_update_adrenaline(*, sp_value: int | float) -> None:
        call_order.append("update_adrenaline")
        assert sp_value == 5
        char.adrenaline += sp_value

    char = SimpleNamespace(
        adrenaline=20,
        update_adrenaline=fake_update_adrenaline,
    )
    record = YixuanCinema1TriggerRecord()
    record.char = char
    record.preload_data = SimpleNamespace(skills=[])
    record.sub_exist_buff_dict = sub_exist_buff_dict

    monkeypatch.setattr(logic, "check_record_module", lambda: setattr(logic, "record", record))
    monkeypatch.setattr(logic, "get_prepared", lambda **kwargs: None)
    monkeypatch.setattr(yixuan_module, "YIXUAN_REPORT", False)
    _block_legacy_event_lookup(monkeypatch)

    lightning_skill = SimpleNamespace(
        skill_tag="1371_Cinema_1",
        char_name="仪玄",
        hit_times=2,
        labels=None,
        ticks=16,
        tick_list=[4, 11],
        heavy_attack=False,
    )
    spawned_node = SkillNode(lightning_skill, 81)

    def fake_spawn_node(tag: str, preload_tick: int, skills: list[object]) -> SkillNode:
        assert tag == "1371_Cinema_1"
        assert preload_tick == 81
        assert skills is record.preload_data.skills
        return spawned_node

    monkeypatch.setattr("zsim.sim_progress.Preload.SkillsQueue.spawn_node", fake_spawn_node)

    original_mission_start = LoadingMission.mission_start

    def fake_mission_start(self, timenow: int, **kwargs) -> None:
        call_order.append("mission_start")
        assert timenow == 81
        original_mission_start(self, timenow, **kwargs)

    monkeypatch.setattr(LoadingMission, "mission_start", fake_mission_start)

    logic.special_hit_logic()

    assert call_order == ["mission_start", "publish", "update_adrenaline", "simple_start"]
    assert len(dispatch_port.events) == 1
    published_node = cast(Any, dispatch_port.events[0])
    assert published_node is spawned_node
    assert isinstance(published_node, SkillNode)
    assert published_node.skill_tag == "1371_Cinema_1"
    assert published_node.preload_tick == 81
    assert published_node.loading_mission is not None
    assert isinstance(published_node.loading_mission, LoadingMission)
    assert published_node.loading_mission.mission_node is published_node
    assert published_node.loading_mission.mission_active_state is True
    assert published_node.loading_mission.mission_start_tick == 81
    assert published_node.loading_mission.mission_dict[81.0] == "start"
    assert published_node.loading_mission.mission_dict[85] == "hit"
    assert published_node.loading_mission.mission_dict[92] == "hit"
    assert char.adrenaline == 25
    assert schedule_data.event_list == []


def test_yixuan_cinema1_judge_blocks_yixuan_skill_without_publish(
    monkeypatch: pytest.MonkeyPatch,
):
    schedule_data = SimpleNamespace(event_list=_FailFastEventList())
    sim_instance = SimpleNamespace(tick=81, schedule_data=schedule_data)
    buff_instance = SimpleNamespace(
        sim_instance=sim_instance,
        ft=SimpleNamespace(index="Buff-角色-仪玄-影画1"),
    )
    dispatch_port = _RecordingDispatchPort([])
    logic = YixuanCinema1Trigger(
        buff_instance,
        scheduled_event_emitter_provider=ScheduledEventEmitterProvider(lambda: dispatch_port),
    )
    monkeypatch.setattr(logic, "check_record_module", lambda: None)
    monkeypatch.setattr(logic, "get_prepared", lambda **kwargs: None)

    _block_legacy_event_lookup(monkeypatch)

    yixuan_skill = SimpleNamespace(
        skill_tag="1371_E_EX",
        char_name="仪玄",
        hit_times=1,
        labels=None,
        ticks=12,
        tick_list=[0],
        heavy_attack=False,
    )
    skill_node = SkillNode(yixuan_skill, 81)

    assert logic.special_judge_logic(skill_node=skill_node) is False
    assert dispatch_port.events == []
    assert schedule_data.event_list == []
