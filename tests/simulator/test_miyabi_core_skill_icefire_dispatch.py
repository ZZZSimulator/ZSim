from __future__ import annotations

import inspect
import sys
from types import SimpleNamespace
from typing import Any, cast

import pytest

import zsim.define as define_module

sys.modules.setdefault("define", define_module)


from zsim.sim_progress.Buff import JudgeTools
from zsim.sim_progress.Buff.BuffXLogic.MiyabiCoreSkill_IceFire import (
    MiyabiCoreSkill_IceFire,
    MiyabiCoreSkillIF,
)
from zsim.sim_progress.data_struct.schedule_dispatch import (
    ScheduledEventEmitterProvider,
    ScheduleDispatchPort,
)
from zsim.sim_progress.Preload import SkillNode


class _FailFastEventList(list):
    def append(self, item):
        raise AssertionError("MiyabiCoreSkill_IceFire should publish via dispatch port")


class _RecordingDispatchPort(ScheduleDispatchPort):
    def __init__(self, call_order: list[str]) -> None:
        self.events: list[object] = []
        self._call_order = call_order

    def publish_scheduled(self, event: object) -> None:
        self._call_order.append("publish")
        self.events.append(event)


class _ForbiddenRuntimeCommandPort:
    def update_anomaly(self, *args: object, **kwargs: object) -> None:
        raise AssertionError("MiyabiCoreSkill_IceFire should not issue runtime commands")

    def settle_buffs(self, *args: object, **kwargs: object) -> None:
        raise AssertionError("MiyabiCoreSkill_IceFire should not issue runtime commands")


def _block_legacy_event_lookup(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_find_event_list(*args, **kwargs):
        raise AssertionError("MiyabiCoreSkill_IceFire should not read raw event_list")

    monkeypatch.setattr(JudgeTools, "find_event_list", fail_find_event_list, raising=False)


def test_miyabi_core_skill_icefire_publishes_follow_up_via_dispatch_port_once(
    monkeypatch: pytest.MonkeyPatch,
):
    call_order: list[str] = []
    listener_calls: list[tuple[tuple[object, ...], dict[str, object]]] = []
    dispatch_port = _RecordingDispatchPort(call_order)
    schedule_data = SimpleNamespace(event_list=_FailFastEventList())

    def fail_broadcast_event(*args: object, **kwargs: object) -> None:
        listener_calls.append((args, kwargs))
        raise AssertionError("MiyabiCoreSkill_IceFire should not broadcast listener events")

    sim_instance = SimpleNamespace(
        tick=72,
        schedule_data=schedule_data,
        listener_manager=SimpleNamespace(broadcast_event=fail_broadcast_event),
        runtime_command_port=_ForbiddenRuntimeCommandPort(),
    )
    buff_instance = SimpleNamespace(sim_instance=sim_instance)
    logic = MiyabiCoreSkill_IceFire(
        buff_instance,
        scheduled_event_emitter_provider=ScheduledEventEmitterProvider(lambda: dispatch_port),
    )

    core_passive_skill = SimpleNamespace(
        skill_tag="1091_Core_Passive",
        char_name="雅",
        hit_times=1,
        labels=None,
        ticks=1,
        tick_list=[1],
        heavy_attack=False,
        element_type=5,
    )

    def fake_special_resources(skill_node: SkillNode) -> None:
        call_order.append("special_resources")
        assert skill_node is dispatch_port.events[0]

    record = MiyabiCoreSkillIF()
    record.last_frostbite = False
    record.enemy = SimpleNamespace(dynamic=SimpleNamespace(frost_frostbite=True))
    record.char = SimpleNamespace(
        NAME="雅",
        skills_dict={"1091_Core_Passive": core_passive_skill},
        special_resources=fake_special_resources,
    )
    monkeypatch.setattr(logic, "check_record_module", lambda: setattr(logic, "record", record))
    monkeypatch.setattr(logic, "get_prepared", lambda **kwargs: None)
    _block_legacy_event_lookup(monkeypatch)

    assert logic.special_exit_logic() is True

    assert call_order == ["publish", "special_resources"]
    assert len(dispatch_port.events) == 1
    published_node = cast(Any, dispatch_port.events[0])
    assert isinstance(published_node, SkillNode)
    assert published_node.skill is core_passive_skill
    assert published_node.skill_tag == "1091_Core_Passive"
    assert published_node.preload_tick == 0
    assert record.last_frostbite is True
    assert schedule_data.event_list == []
    assert listener_calls == []

    assert logic.special_exit_logic() is False
    assert call_order == ["publish", "special_resources"]
    assert len(dispatch_port.events) == 1
    assert listener_calls == []


def test_miyabi_core_skill_icefire_exit_source_keeps_runtime_layers_separate():
    source = inspect.getsource(MiyabiCoreSkill_IceFire.special_exit_logic)

    assert "read_enemy_frost_frostbite_edge_state" in source
    assert "find_event_list" not in source
    assert "event_list" not in source
    assert "create_schedule_dispatch_port" not in source
    assert "_create_dispatch_port" not in source
    assert "emit_scheduled" in source
    assert "broadcast_event" not in source
    assert "RuntimeCommandPort" not in source
    assert "create_runtime_command_port" not in source
