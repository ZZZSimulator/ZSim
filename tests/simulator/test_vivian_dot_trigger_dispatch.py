from __future__ import annotations

import sys
from types import SimpleNamespace
from typing import Any, cast

import pytest

import zsim.define as define_module

sys.modules.setdefault("define", define_module)

import zsim.sim_progress.Buff.BuffXLogic.VivianCinema1Debuff as vivian_cinema1_module
import zsim.sim_progress.Buff.BuffXLogic.VivianDotTrigger as vivian_module
from zsim.sim_progress.Buff import JudgeTools
from zsim.sim_progress.Buff.BuffXLogic.VivianCinema1Debuff import (
    VivianCinema1Debuff,
    VVivianCinema1DebuffRecord,
)
from zsim.sim_progress.Buff.BuffXLogic.VivianDotTrigger import (
    VivianDotTrigger,
    VivianDotTriggerRecord,
)
from zsim.sim_progress.data_struct.schedule_dispatch import (
    ScheduledEventEmitterProvider,
    ScheduleDispatchPort,
)
from zsim.sim_progress.Load import LoadingMission
from zsim.sim_progress.Preload import SkillNode


class _FailFastEventList(list):
    def append(self, item):
        raise AssertionError("Vivian dot tests should not append raw scheduled events")


class _FailFastDotList(list):
    def append(self, item):
        raise AssertionError("Vivian judge path should not register dots")


class _RecordingDispatchPort(ScheduleDispatchPort):
    def __init__(self, call_order: list[str]) -> None:
        self.events: list[object] = []
        self._call_order = call_order

    def publish_scheduled(self, event: object) -> None:
        self._call_order.append("publish")
        self.events.append(event)


class _RecordingDotList(list):
    def __init__(self, call_order: list[str], items: list[object] | None = None) -> None:
        super().__init__(items or [])
        self._call_order = call_order

    def append(self, item):
        self._call_order.append("register_dot")
        super().append(item)


class _ForbiddenRuntimeCommandPort:
    def __getattr__(self, name: str):
        raise AssertionError("Vivian dot tests should not issue runtime commands")

    def update_anomaly(self, **kwargs):
        raise AssertionError("Vivian dot tests should not issue runtime commands")


def _fail_listener_broadcast(**kwargs) -> None:
    raise AssertionError("Vivian dot tests should not broadcast listener events")


class _FakeViviansProphecy:
    def __init__(self, skill_node_data: SkillNode, call_order: list[str]) -> None:
        self.ft = SimpleNamespace(index="ViviansProphecy")
        self.dy = SimpleNamespace(active=True)
        self.skill_node_data = skill_node_data
        self.started_at: int | None = None
        self._call_order = call_order

    def start(self, timenow: int) -> None:
        self._call_order.append("dot_start")
        self.started_at = timenow


class _PresenceDot:
    def __init__(self, *, active: bool) -> None:
        self.ft = SimpleNamespace(index="ViviansProphecy")
        self.dy = SimpleNamespace(active=active)


class _PreparationContextProbe:
    def __init__(self, registry):
        self._registry = registry

    def find_sub_exist_buff_dict(self, owner_name: str):
        return self._registry[owner_name]


class _CountingAnomalyDynamic:
    def __init__(self, *, anomaly_active: bool) -> None:
        self._anomaly_active = anomaly_active
        self.is_under_anomaly_calls = 0
        self.dynamic_dot_list = _FailFastDotList()

    def is_under_anomaly(self) -> bool:
        self.is_under_anomaly_calls += 1
        return self._anomaly_active


class _JudgeLoadingMission:
    def __init__(self, *, hit_now: bool) -> None:
        self._hit_now = hit_now
        self.hit_checks: list[int] = []

    def is_hit_now(self, tick: int) -> bool:
        self.hit_checks.append(tick)
        return self._hit_now

    def mission_start(self, *args: object, **kwargs: object) -> None:
        raise AssertionError("Vivian judge path should not start dot loading missions")


def _make_vivian_judge_skill_node(
    *, skill_tag: str, hit_now: bool
) -> tuple[SkillNode, _JudgeLoadingMission]:
    skill = SimpleNamespace(
        skill_tag=skill_tag,
        char_name="薇薇安",
        hit_times=1,
        labels=None,
        ticks=1,
        tick_list=[1],
        heavy_attack=False,
        element_type=4,
    )
    skill_node = SkillNode(skill, 96)
    loading_mission = _JudgeLoadingMission(hit_now=hit_now)
    skill_node.loading_mission = loading_mission
    return skill_node, loading_mission


def _build_vivian_judge_harness(
    monkeypatch: pytest.MonkeyPatch,
    *,
    anomaly_active: bool,
) -> SimpleNamespace:
    dispatch_create_calls: list[object] = []
    spawn_calls: list[object] = []
    dot_adapter_calls: list[object] = []
    schedule_data = SimpleNamespace(
        event_list=_FailFastEventList(),
        change_process_state=lambda: None,
    )
    sim_instance = SimpleNamespace(
        tick=96,
        schedule_data=schedule_data,
        listener_manager=SimpleNamespace(broadcast_event=_fail_listener_broadcast),
        runtime_command_port=_ForbiddenRuntimeCommandPort(),
    )
    buff_instance = SimpleNamespace(
        sim_instance=sim_instance,
        ft=SimpleNamespace(index="Buff-角色-薇薇安-核心被动-Dot触发器"),
    )
    dispatch_port = _RecordingDispatchPort([])

    def create_dispatch_port() -> _RecordingDispatchPort:
        dispatch_create_calls.append(sim_instance)
        return dispatch_port

    logic = VivianDotTrigger(
        buff_instance,
        scheduled_event_emitter_provider=ScheduledEventEmitterProvider(create_dispatch_port),
    )
    dynamic = _CountingAnomalyDynamic(anomaly_active=anomaly_active)
    enemy = SimpleNamespace(dynamic=dynamic)
    record = VivianDotTriggerRecord()
    record.enemy = enemy
    record.char = SimpleNamespace(NAME="薇薇安")
    prepared_calls: list[dict[str, object]] = []

    def fail_spawn_normal_dot(*args: object, **kwargs: object) -> object:
        spawn_calls.append((args, kwargs))
        raise AssertionError("Vivian judge path should not spawn dots")

    def fail_dot_runtime_state_from_enemy(enemy: object) -> object:
        dot_adapter_calls.append(enemy)
        raise AssertionError("Vivian judge path should not use dot runtime state")

    monkeypatch.setattr(logic, "check_record_module", lambda: setattr(logic, "record", record))
    monkeypatch.setattr(logic, "get_prepared", lambda **kwargs: prepared_calls.append(kwargs))
    monkeypatch.setattr(
        vivian_module.DotRuntimeStateAdapter,
        "from_enemy",
        staticmethod(fail_dot_runtime_state_from_enemy),
    )
    monkeypatch.setattr(
        "zsim.sim_progress.Update.UpdateAnomaly.spawn_normal_dot",
        fail_spawn_normal_dot,
    )
    _block_legacy_event_lookup(monkeypatch)

    return SimpleNamespace(
        dispatch_create_calls=dispatch_create_calls,
        dot_adapter_calls=dot_adapter_calls,
        dynamic=dynamic,
        logic=logic,
        prepared_calls=prepared_calls,
        schedule_data=schedule_data,
        spawn_calls=spawn_calls,
    )


def _assert_vivian_judge_path_stayed_pure(harness: SimpleNamespace) -> None:
    assert harness.schedule_data.event_list == []
    assert harness.dynamic.dynamic_dot_list == []
    assert harness.dispatch_create_calls == []
    assert harness.spawn_calls == []
    assert harness.dot_adapter_calls == []


def _block_legacy_event_lookup(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_find_event_list(*args, **kwargs):
        raise AssertionError("VivianDotTrigger should not read raw event_list")

    monkeypatch.setattr(JudgeTools, "find_event_list", fail_find_event_list, raising=False)


def test_vivian_dot_trigger_judge_rejects_missing_skill_node_without_side_effects(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = _build_vivian_judge_harness(monkeypatch, anomaly_active=True)

    assert harness.logic.special_judge_logic() is False

    assert harness.prepared_calls == [{"char_CID": 1331, "enemy": 1}]
    assert harness.dynamic.is_under_anomaly_calls == 0
    _assert_vivian_judge_path_stayed_pure(harness)


def test_vivian_dot_trigger_judge_rejects_invalid_skill_node_without_side_effects(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = _build_vivian_judge_harness(monkeypatch, anomaly_active=True)

    with pytest.raises(TypeError):
        harness.logic.special_judge_logic(skill_node=object())

    assert harness.prepared_calls == [{"char_CID": 1331, "enemy": 1}]
    assert harness.dynamic.is_under_anomaly_calls == 0
    _assert_vivian_judge_path_stayed_pure(harness)


@pytest.mark.parametrize(
    (
        "skill_tag",
        "hit_now",
        "anomaly_active",
        "expected",
        "expected_hit_checks",
        "expected_anomaly_reads",
    ),
    [
        ("1331_EX_A", True, True, False, [], 0),
        ("1331_SNA_2", False, True, False, [96], 0),
        ("1331_SNA_2", True, False, False, [96], 1),
        ("1331_CoAttack_A", True, True, True, [96], 1),
    ],
)
def test_vivian_dot_trigger_judge_is_pure_for_tag_hit_and_anomaly_gates(
    monkeypatch: pytest.MonkeyPatch,
    skill_tag: str,
    hit_now: bool,
    anomaly_active: bool,
    expected: bool,
    expected_hit_checks: list[int],
    expected_anomaly_reads: int,
) -> None:
    harness = _build_vivian_judge_harness(monkeypatch, anomaly_active=anomaly_active)
    skill_node, loading_mission = _make_vivian_judge_skill_node(
        skill_tag=skill_tag,
        hit_now=hit_now,
    )

    assert harness.logic.special_judge_logic(skill_node=skill_node) is expected

    assert harness.prepared_calls == [{"char_CID": 1331, "enemy": 1}]
    assert loading_mission.hit_checks == expected_hit_checks
    assert harness.dynamic.is_under_anomaly_calls == expected_anomaly_reads
    _assert_vivian_judge_path_stayed_pure(harness)


@pytest.mark.parametrize(
    ("report_enabled", "expected_report_calls"),
    [
        (False, ()),
        (True, ("change_process_state", "print_report")),
    ],
)
def test_vivian_dot_trigger_registers_dot_and_publishes_skill_node_via_dispatch_port(
    monkeypatch: pytest.MonkeyPatch,
    report_enabled: bool,
    expected_report_calls: tuple[str, ...],
) -> None:
    call_order: list[str] = []
    dispatch_port = _RecordingDispatchPort(call_order)

    def change_process_state() -> None:
        call_order.append("change_process_state")

    schedule_data = SimpleNamespace(
        event_list=_FailFastEventList(),
        change_process_state=change_process_state,
    )
    sim_instance = SimpleNamespace(
        tick=96,
        schedule_data=schedule_data,
        listener_manager=SimpleNamespace(broadcast_event=_fail_listener_broadcast),
        runtime_command_port=_ForbiddenRuntimeCommandPort(),
    )
    buff_instance = SimpleNamespace(
        sim_instance=sim_instance,
        ft=SimpleNamespace(index="Buff-角色-薇薇安-核心被动-Dot触发器"),
    )
    logic = VivianDotTrigger(
        buff_instance,
        scheduled_event_emitter_provider=ScheduledEventEmitterProvider(lambda: dispatch_port),
    )

    inactive_dot = _PresenceDot(active=False)
    dynamic_dot_list = _RecordingDotList(call_order, [inactive_dot])
    enemy = SimpleNamespace(
        dynamic=SimpleNamespace(dynamic_dot_list=dynamic_dot_list),
    )
    enemy.find_dot = lambda dot_index: (_ for _ in ()).throw(
        AssertionError("VivianDotTrigger should use DotRuntimeStateAdapter")
    )
    record = VivianDotTriggerRecord()
    record.enemy = enemy
    record.char = SimpleNamespace(NAME="薇薇安")

    dot_skill = SimpleNamespace(
        skill_tag="1331_Core_Passive",
        char_name="薇薇安",
        hit_times=2,
        labels=None,
        ticks=18,
        tick_list=[6, 14],
        heavy_attack=False,
        element_type=4,
    )
    dot_skill_node = SkillNode(dot_skill, 96)
    fake_dot = _FakeViviansProphecy(dot_skill_node, call_order)
    spawn_calls: list[str] = []

    def fake_spawn_normal_dot(dot_index: str, *, sim_instance: object) -> _FakeViviansProphecy:
        spawn_calls.append(dot_index)
        assert dot_index == "ViviansProphecy"
        assert sim_instance is logic.buff_instance.sim_instance
        return fake_dot

    monkeypatch.setattr(logic, "check_record_module", lambda: setattr(logic, "record", record))
    monkeypatch.setattr(logic, "get_prepared", lambda **kwargs: None)

    def fake_print(message: object, *args: object, **kwargs: object) -> None:
        call_order.append("print_report")
        assert message == "核心被动：薇薇安对敌人施加Dot——薇薇安的预言"
        assert args == ()
        assert kwargs == {}

    monkeypatch.setattr(vivian_module, "VIVIAN_REPORT", report_enabled)
    monkeypatch.setattr(vivian_module, "print", fake_print, raising=False)
    monkeypatch.setattr(
        "zsim.sim_progress.Update.UpdateAnomaly.spawn_normal_dot",
        fake_spawn_normal_dot,
    )
    _block_legacy_event_lookup(monkeypatch)

    original_mission_start = LoadingMission.mission_start

    def fake_mission_start(self, timenow: int, **kwargs) -> None:
        call_order.append("mission_start")
        assert timenow == 96
        original_mission_start(self, timenow, **kwargs)

    monkeypatch.setattr(LoadingMission, "mission_start", fake_mission_start)

    logic.special_hit_logic()

    expected_call_order = [
        "dot_start",
        "mission_start",
        "register_dot",
        "publish",
        *expected_report_calls,
    ]
    assert call_order == expected_call_order
    assert spawn_calls == ["ViviansProphecy"]
    assert dynamic_dot_list == [inactive_dot, fake_dot]
    assert fake_dot.started_at == 96
    assert len(dispatch_port.events) == 1
    published_node = cast(Any, dispatch_port.events[0])
    assert published_node is dot_skill_node
    assert isinstance(published_node, SkillNode)
    assert published_node.skill_tag == "1331_Core_Passive"
    assert published_node.preload_tick == 96
    assert published_node.loading_mission is not None
    assert isinstance(published_node.loading_mission, LoadingMission)
    assert published_node.loading_mission.mission_node is published_node
    assert published_node.loading_mission.mission_active_state is True
    assert published_node.loading_mission.mission_start_tick == 96
    assert published_node.loading_mission.mission_dict[96.0] == "start"
    assert published_node.loading_mission.mission_dict[102] == "hit"
    assert published_node.loading_mission.mission_dict[110] == "hit"
    assert schedule_data.event_list == []

    logic.special_hit_logic()

    assert spawn_calls == ["ViviansProphecy"]
    assert dynamic_dot_list == [inactive_dot, fake_dot]
    assert len(dispatch_port.events) == 1
    assert call_order == expected_call_order


def test_vivian_dot_trigger_record_uses_existing_buff_template(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sim_instance = SimpleNamespace()
    buff_instance = SimpleNamespace(
        sim_instance=sim_instance,
        ft=SimpleNamespace(index="Buff-角色-薇薇安-核心被动-Dot触发器"),
    )
    buff_0 = SimpleNamespace(history=SimpleNamespace(record=None))

    def fake_find_exist_buff_dict(*, sim_instance: object):
        assert sim_instance is buff_instance.sim_instance
        return {"薇薇安": {buff_instance.ft.index: buff_0}}

    monkeypatch.setattr(JudgeTools, "find_exist_buff_dict", fake_find_exist_buff_dict)

    logic = VivianDotTrigger(buff_instance)
    logic.check_record_module()

    assert logic.buff_0 is buff_0
    assert isinstance(buff_0.history.record, VivianDotTriggerRecord)
    assert logic.record is buff_0.history.record


@pytest.mark.parametrize(
    ("existing_dot_active", "expected"),
    [
        (True, True),
        (False, False),
        (None, False),
    ],
)
def test_vivian_cinema1_debuff_judges_by_vivians_prophecy_presence(
    monkeypatch: pytest.MonkeyPatch,
    existing_dot_active: bool | None,
    expected: bool,
) -> None:
    schedule_data = SimpleNamespace(
        event_list=_FailFastEventList(),
        change_process_state=lambda: None,
    )
    sim_instance = SimpleNamespace(
        tick=96,
        schedule_data=schedule_data,
        listener_manager=SimpleNamespace(broadcast_event=_fail_listener_broadcast),
        runtime_command_port=_ForbiddenRuntimeCommandPort(),
    )
    buff_instance = SimpleNamespace(
        sim_instance=sim_instance,
        ft=SimpleNamespace(index="Buff-角色-薇薇安-影画1-预言增伤"),
    )
    logic = VivianCinema1Debuff(buff_instance)
    record = VVivianCinema1DebuffRecord()
    record.char = SimpleNamespace(NAME="薇薇安")
    dynamic_dot_list = (
        [_PresenceDot(active=existing_dot_active)] if existing_dot_active is not None else []
    )

    record.enemy = SimpleNamespace(
        dynamic=SimpleNamespace(dynamic_dot_list=dynamic_dot_list),
        find_dot=lambda dot_index: (_ for _ in ()).throw(
            AssertionError("VivianCinema1Debuff should use DotRuntimeStateAdapter")
        ),
    )
    prepared_calls: list[dict[str, object]] = []

    monkeypatch.setattr(logic, "check_record_module", lambda: setattr(logic, "record", record))
    monkeypatch.setattr(logic, "get_prepared", lambda **kwargs: prepared_calls.append(kwargs))
    _block_legacy_event_lookup(monkeypatch)

    assert logic.special_judge_logic() is expected
    assert prepared_calls == [{"char_CID": 1331, "enemy": 1}]
    assert schedule_data.event_list == []


def test_vivian_cinema1_debuff_record_uses_existing_buff_template(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sim_instance = SimpleNamespace()
    buff_instance = SimpleNamespace(
        sim_instance=sim_instance,
        ft=SimpleNamespace(index="Buff-角色-薇薇安-影画1-预言增伤"),
    )
    buff_0 = SimpleNamespace(history=SimpleNamespace(record=None))

    def fake_find_exist_buff_dict(*, sim_instance: object):
        assert sim_instance is buff_instance.sim_instance
        return {"薇薇安": {buff_instance.ft.index: buff_0}}

    monkeypatch.setattr(
        vivian_cinema1_module,
        "build_preparation_context_from_buff",
        lambda current_buff: _PreparationContextProbe(
            fake_find_exist_buff_dict(sim_instance=current_buff.sim_instance)
        ),
    )
    monkeypatch.setattr(JudgeTools, "find_exist_buff_dict", fake_find_exist_buff_dict)

    logic = VivianCinema1Debuff(buff_instance)
    logic.check_record_module()

    assert logic.buff_0 is buff_0
    assert isinstance(buff_0.history.record, VVivianCinema1DebuffRecord)
    assert logic.record is buff_0.history.record
