from __future__ import annotations

import sys
from types import SimpleNamespace
from typing import cast

import zsim.define as define_module

sys.modules.setdefault("define", define_module)

from zsim.sim_progress.data_struct.DecibelManager.DecibelManagerClass import Decibelmanager
from zsim.sim_progress.data_struct.planned_queue import PlannedEventQueue
from zsim.sim_progress.data_struct.schedule_dispatch import (
    ScheduledEventEmitterProvider,
    ScheduleDispatchPort,
)
from zsim.sim_progress.data_struct.sp_update_data import ScheduleRefreshData


class _FailFastEventList(list):
    def append(self, item):
        raise AssertionError("Decibelmanager should publish refresh data via dispatch port")


def _attach_planned_queue(schedule_data: SimpleNamespace) -> None:
    schedule_data.planned_event_queue = PlannedEventQueue(
        get_events=lambda: schedule_data.event_list,
        set_events=lambda events: setattr(schedule_data, "event_list", events),
    )


class _RecordingDispatchPort:
    def __init__(self) -> None:
        self.events: list[object] = []

    def publish_scheduled(self, event: object) -> None:
        self.events.append(event)


def test_decibel_manager_publishes_major_and_minor_refreshes_via_dispatch_port(
    monkeypatch,
):
    dispatch_port = _RecordingDispatchPort()
    schedule_data = SimpleNamespace(event_list=_FailFastEventList())
    sim_instance = SimpleNamespace(schedule_data=schedule_data, game_state={})
    manager = Decibelmanager(
        sim_instance,
        scheduled_event_emitter_provider=ScheduledEventEmitterProvider(
            lambda: cast(ScheduleDispatchPort, dispatch_port)
        ),
    )
    manager.char_obj_list = [
        SimpleNamespace(CID=1301, NAME="Major"),
        SimpleNamespace(CID=1201, NAME="MinorOne"),
        SimpleNamespace(CID=1401, NAME="MinorTwo"),
    ]
    skill_node = SimpleNamespace(
        skill_tag="1301_TEST_1",
        active_generation=True,
        skill=SimpleNamespace(trigger_buff_level=5),
    )

    manager.update(skill_node=skill_node)

    assert len(dispatch_port.events) == 3
    assert schedule_data.event_list == []

    major_refresh = dispatch_port.events[0]
    minor_refresh_one = dispatch_port.events[1]
    minor_refresh_two = dispatch_port.events[2]

    assert isinstance(major_refresh, ScheduleRefreshData)
    assert major_refresh.decibel_target == ("Major",)
    assert major_refresh.decibel_value == 10

    assert isinstance(minor_refresh_one, ScheduleRefreshData)
    assert minor_refresh_one.decibel_target == ("MinorOne",)
    assert minor_refresh_one.decibel_value == 5.0

    assert isinstance(minor_refresh_two, ScheduleRefreshData)
    assert minor_refresh_two.decibel_target == ("MinorTwo",)
    assert minor_refresh_two.decibel_value == 5.0


def test_decibel_manager_skips_zero_value_branches_without_publish(monkeypatch):
    dispatch_port = _RecordingDispatchPort()
    schedule_data = SimpleNamespace(event_list=_FailFastEventList())
    sim_instance = SimpleNamespace(schedule_data=schedule_data, game_state={})
    manager = Decibelmanager(
        sim_instance,
        scheduled_event_emitter_provider=ScheduledEventEmitterProvider(
            lambda: cast(ScheduleDispatchPort, dispatch_port)
        ),
    )
    manager.char_obj_list = [
        SimpleNamespace(CID=1301, NAME="Major"),
        SimpleNamespace(CID=1201, NAME="MinorOne"),
    ]

    inactive_generation_node = SimpleNamespace(
        skill_tag="1301_TEST_1",
        active_generation=False,
        skill=SimpleNamespace(trigger_buff_level=5),
    )
    manager.update(skill_node=inactive_generation_node)

    unsupported_trigger_node = SimpleNamespace(
        skill_tag="1301_TEST_2",
        active_generation=True,
        skill=SimpleNamespace(trigger_buff_level=999),
    )
    manager.update(skill_node=unsupported_trigger_node)

    assert dispatch_port.events == []
    assert schedule_data.event_list == []


def test_decibel_manager_on_demand_dispatch_uses_rebound_event_list():
    old_event_list: list[object] = []
    new_event_list: list[object] = []
    schedule_data = SimpleNamespace(event_list=old_event_list)
    _attach_planned_queue(schedule_data)
    sim_instance = SimpleNamespace(schedule_data=schedule_data, game_state={})
    manager = Decibelmanager(sim_instance)

    manager.add_decibel_to_char(10, "Major", "part_break")

    schedule_data.event_list = new_event_list
    manager.add_decibel_to_char(5, "MinorOne", "part_break")

    assert len(old_event_list) == 1
    old_refresh = old_event_list[0]
    assert isinstance(old_refresh, ScheduleRefreshData)
    assert old_refresh.decibel_target == ("Major",)
    assert old_refresh.decibel_value == 10

    assert len(new_event_list) == 1
    new_refresh = new_event_list[0]
    assert isinstance(new_refresh, ScheduleRefreshData)
    assert new_refresh.decibel_target == ("MinorOne",)
    assert new_refresh.decibel_value == 5
