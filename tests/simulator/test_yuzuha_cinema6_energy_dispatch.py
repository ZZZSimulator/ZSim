from __future__ import annotations

import sys
from types import SimpleNamespace
from typing import cast

import zsim.define as define_module

sys.modules.setdefault("define", define_module)

from zsim.sim_progress.Character.Yuzuha import Yuzuha
from zsim.sim_progress.data_struct.schedule_dispatch import (
    ScheduledEventEmitterProvider,
    ScheduleDispatchPort,
)
from zsim.sim_progress.data_struct.sp_update_data import ScheduleRefreshData
from zsim.sim_progress.Preload import SkillNode


class _FailFastEventList(list):
    def append(self, item):
        raise AssertionError("Yuzuha cinema-6 energy fan-out should publish via dispatch port")


class _RecordingDispatchPort:
    def __init__(self) -> None:
        self.events: list[object] = []

    def publish_scheduled(self, event: object) -> None:
        self.events.append(event)


def _build_skill_node(*, char_name: str = "柚叶", trigger_buff_level: int = 6) -> SkillNode:
    skill = SimpleNamespace(
        skill_tag="1411_Ultimate",
        char_name=char_name,
        hit_times=1,
        labels=None,
        ticks=10,
        tick_list=[],
        trigger_buff_level=trigger_buff_level,
    )
    return SkillNode(skill=skill, preload_tick=20)


def test_yuzuha_cinema6_team_energy_fanout_publishes_via_dispatch_port(monkeypatch):
    dispatch_port = _RecordingDispatchPort()
    broadcast_calls: list[object] = []
    schedule_data = SimpleNamespace(
        event_list=_FailFastEventList(),
        enemy=SimpleNamespace(
            special_state_manager=SimpleNamespace(
                broadcast_and_update=lambda **kwargs: broadcast_calls.append(kwargs)
            )
        ),
    )
    sim_instance = SimpleNamespace(
        schedule_data=schedule_data,
        char_data=SimpleNamespace(
            char_obj_list=[
                SimpleNamespace(NAME="柚叶"),
                SimpleNamespace(NAME="仪玄"),
                SimpleNamespace(NAME="薇薇安"),
            ]
        ),
    )
    yuzuha = object.__new__(Yuzuha)
    yuzuha.NAME = "柚叶"
    yuzuha.cinema = 6
    yuzuha.sim_instance = sim_instance
    yuzuha.sugar_points = 3
    yuzuha.max_sugar_points = 6
    yuzuha._scheduled_event_emitter_provider = ScheduledEventEmitterProvider(
        lambda: cast(ScheduleDispatchPort, dispatch_port)
    )

    skill_node = _build_skill_node()

    yuzuha.special_resources(skill_node)

    assert len(broadcast_calls) == 1
    assert broadcast_calls[0]["skill_node"] is skill_node
    assert len(dispatch_port.events) == 2
    assert schedule_data.event_list == []

    published_targets = []
    for event in dispatch_port.events:
        assert isinstance(event, ScheduleRefreshData)
        assert event.sp_value == 25
        published_targets.append(event.sp_target)

    assert published_targets == [("仪玄",), ("薇薇安",)]
