from __future__ import annotations

import importlib
import inspect
import sys
from types import SimpleNamespace
from typing import Any, cast

import pytest

import zsim.define as define_module

sys.modules.setdefault("define", define_module)

import zsim.sim_progress.Buff.BuffXLogic.CannonRotor as cannon_module
from zsim.sim_progress.Buff import JudgeTools
from zsim.sim_progress.Buff.BuffXLogic.CannonRotor import CannonRotor
from zsim.sim_progress.data_struct.schedule_dispatch import (
    ScheduledEventEmitterProvider,
    ScheduleDispatchPort,
)
from zsim.sim_progress.Load import LoadingMission
from zsim.sim_progress.Preload import SkillNode


class _FailFastEventList(list):
    def append(self, item):
        raise AssertionError("CannonRotor should publish via dispatch port")


class _RecordingDispatchPort(ScheduleDispatchPort):
    def __init__(self, call_order: list[str]) -> None:
        self.call_order = call_order
        self.events: list[object] = []

    def publish_scheduled(self, event: object) -> None:
        self.call_order.append("publish")
        self.events.append(event)


def _block_legacy_event_lookup(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_find_event_list(*args, **kwargs):
        raise AssertionError("CannonRotor should not read raw event_list")

    monkeypatch.setattr(JudgeTools, "find_event_list", fail_find_event_list, raising=False)


@pytest.mark.parametrize(
    "module_name",
    [
        "zsim.sim_progress.Buff.BuffXLogic.AlicePolarizedAssaultTrigger",
        "zsim.sim_progress.Buff.BuffXLogic.CannonRotor",
        "zsim.sim_progress.Buff.BuffXLogic.ElegantVanitySpRecover",
        "zsim.sim_progress.Buff.BuffXLogic.HugoCorePassiveTotalizeTrigger",
        "zsim.sim_progress.Buff.BuffXLogic.LunarNoviluna",
        "zsim.sim_progress.Buff.BuffXLogic.MagneticStormCharlieSpRecover",
        "zsim.sim_progress.Buff.BuffXLogic.MiyabiCoreSkill_IceFire",
        "zsim.sim_progress.Buff.BuffXLogic.SeedAdditionalAbilityTrigger",
        "zsim.sim_progress.Buff.BuffXLogic.SliceofTimeExtraResources",
        "zsim.sim_progress.Buff.BuffXLogic.VivianCinema6Trigger",
        "zsim.sim_progress.Buff.BuffXLogic.VivianCorePassiveTrigger",
        "zsim.sim_progress.Buff.BuffXLogic.VivianDotTrigger",
        "zsim.sim_progress.Buff.BuffXLogic.YanagiPolarityDisorderTrigger",
        "zsim.sim_progress.Buff.BuffXLogic.YixuanCinema1Trigger",
    ],
)
def test_buffxlogic_scheduled_producers_receive_emitters_without_dispatch_factory(
    module_name: str,
) -> None:
    source = inspect.getsource(importlib.import_module(module_name))

    assert "ScheduledEventEmitterProvider" in source
    assert "emit_scheduled" in source
    assert "create_schedule_dispatch_port" not in source
    assert "_create_dispatch_port" not in source
    assert ".publish_scheduled" not in source


def test_cannon_rotor_publishes_follow_up_skill_node_via_dispatch_port(
    monkeypatch: pytest.MonkeyPatch,
):
    call_order: list[str] = []
    dispatch_port = _RecordingDispatchPort(call_order)
    schedule_data = SimpleNamespace(event_list=_FailFastEventList())
    sim_instance = SimpleNamespace(tick=45, schedule_data=schedule_data)
    sub_exist_buff_dict = {"cannon-rotor": object()}

    def fake_simple_start(tick_now, target_sub_exist_buff_dict):
        call_order.append("simple_start")
        assert tick_now == 45
        assert target_sub_exist_buff_dict is sub_exist_buff_dict

    buff_instance = SimpleNamespace(
        sim_instance=sim_instance,
        simple_start=fake_simple_start,
    )
    logic = CannonRotor(
        buff_instance,
        scheduled_event_emitter_provider=ScheduledEventEmitterProvider(lambda: dispatch_port),
    )
    record = SimpleNamespace(
        char=SimpleNamespace(CID=1101),
        skill_tag="CannonRotorAdditionalDamage",
        preload_data=SimpleNamespace(skills=[]),
        sub_exist_buff_dict=sub_exist_buff_dict,
    )
    monkeypatch.setattr(logic, "check_record_module", lambda: setattr(logic, "record", record))
    monkeypatch.setattr(logic, "get_prepared", lambda **kwargs: None)
    monkeypatch.setattr(cannon_module, "find_tick", lambda *, sim_instance: sim_instance.tick)
    _block_legacy_event_lookup(monkeypatch)

    spawned_skill = SimpleNamespace(
        skill_tag="1101_CannonRotorAdditionalDamage",
        char_name="Cannon User",
        preload_tick=45,
        hit_times=2,
        skill=SimpleNamespace(ticks=12, tick_list=[3, 7], heavy_attack=False),
        end_tick=57,
        loading_mission=None,
    )

    def fake_spawn_node(tag, preload_tick, skills):
        assert tag == "1101_CannonRotorAdditionalDamage"
        assert preload_tick == 45
        assert skills is record.preload_data.skills
        return spawned_skill

    monkeypatch.setattr("zsim.sim_progress.Preload.SkillsQueue.spawn_node", fake_spawn_node)

    original_mission_start = LoadingMission.mission_start

    def fake_mission_start(self, timenow: int, **kwargs) -> None:
        call_order.append("mission_start")
        assert timenow == 45
        original_mission_start(self, timenow, **kwargs)

    monkeypatch.setattr(LoadingMission, "mission_start", fake_mission_start)

    logic.special_hit_logic()

    assert call_order == ["mission_start", "publish", "simple_start"]
    assert len(dispatch_port.events) == 1
    published_node = cast(Any, dispatch_port.events[0])
    assert published_node is spawned_skill
    assert isinstance(published_node, SimpleNamespace)
    assert published_node.loading_mission is not None
    assert isinstance(published_node.loading_mission, LoadingMission)
    assert published_node.loading_mission.mission_node is published_node
    assert published_node.loading_mission.mission_active_state is True
    assert published_node.loading_mission.mission_start_tick == 45
    assert published_node.loading_mission.mission_dict[45.0] == "start"
    assert schedule_data.event_list == []


def test_cannon_rotor_judge_blocks_other_character_without_publish(
    monkeypatch: pytest.MonkeyPatch,
):
    schedule_data = SimpleNamespace(event_list=_FailFastEventList())
    sim_instance = SimpleNamespace(tick=45, schedule_data=schedule_data)

    def fail_simple_start(*args, **kwargs) -> None:
        raise AssertionError("CannonRotor failed judge should not start buff state")

    buff_instance = SimpleNamespace(
        sim_instance=sim_instance,
        ft=SimpleNamespace(index="Buff-音擎-加农转子"),
        simple_start=fail_simple_start,
    )
    dispatch_port = _RecordingDispatchPort([])
    logic = CannonRotor(
        buff_instance,
        scheduled_event_emitter_provider=ScheduledEventEmitterProvider(lambda: dispatch_port),
    )
    record = SimpleNamespace(
        char=SimpleNamespace(NAME="Cannon User"),
        enemy=object(),
        dynamic_buff_list=object(),
        sub_exist_buff_dict={"cannon-rotor": object()},
    )
    monkeypatch.setattr(logic, "check_record_module", lambda: setattr(logic, "record", record))
    monkeypatch.setattr(logic, "get_prepared", lambda **kwargs: None)

    _block_legacy_event_lookup(monkeypatch)

    other_skill = SimpleNamespace(
        skill_tag="1101_CannonRotorAdditionalDamage",
        char_name="Other Character",
        hit_times=1,
        labels=None,
        ticks=12,
        tick_list=[0],
        heavy_attack=False,
    )
    skill_node = SkillNode(other_skill, 45)

    assert logic.special_judge_logic(skill_node=skill_node) is False
    assert dispatch_port.events == []
    assert schedule_data.event_list == []
