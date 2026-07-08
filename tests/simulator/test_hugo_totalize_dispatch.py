from __future__ import annotations

import sys
from collections.abc import Iterable
from types import SimpleNamespace
from typing import Any, Callable, SupportsIndex

import pytest

import zsim.define as define_module
import zsim.sim_progress.ScheduledEvent as scheduled_event_module
import zsim.sim_progress.ScheduledEvent.buff_runtime as buff_runtime_module
import zsim.sim_progress.ScheduledEvent.runtime_command as runtime_command_module

sys.modules.setdefault("define", define_module)

import zsim.sim_progress.Buff.BuffXLogic.HugoCorePassiveTotalizeTrigger as hugo_module
from zsim.sim_progress.Buff import JudgeTools
from zsim.sim_progress.Buff.BuffXLogic.HugoCorePassiveTotalizeTrigger import (
    HugoCorePassiveTotalizeTrigger,
    HugoCorePassiveTotalizeTriggerRecord,
)
from zsim.sim_progress.data_struct import StunForcedTerminationEvent
from zsim.sim_progress.data_struct.schedule_dispatch import (
    ScheduledEventEmitterProvider,
    ScheduleDispatchPort,
)
from zsim.sim_progress.Load import LoadingMission
from zsim.sim_progress.Preload import SkillNode
from zsim.sim_progress.ScheduledEvent.buff_runtime import BuffRuntimeReadPort


class _FailFastEventList(list[Any]):
    def append(self, item: Any) -> None:
        raise AssertionError(
            "HugoCorePassiveTotalizeTrigger should publish planned events via dispatch port"
        )


class _FailFastPendingQueue(list[Any]):
    def append(self, item: Any) -> None:
        raise AssertionError("Hugo totalize should not write raw pending Buff queues")

    def extend(self, items: Iterable[Any]) -> None:
        raise AssertionError("Hugo totalize should not write raw pending Buff queues")

    def insert(self, index: SupportsIndex, item: Any) -> None:
        raise AssertionError("Hugo totalize should not write raw pending Buff queues")


class _RecordingDispatchPort(ScheduleDispatchPort):
    def __init__(self, call_order: list[str]) -> None:
        self.call_order = call_order
        self.events: list[Any] = []
        self.on_publish: Callable[[object], None] | None = None

    def publish_scheduled(self, event: object) -> None:
        self.call_order.append("publish")
        self.events.append(event)
        if self.on_publish is not None:
            self.on_publish(event)


def _block_legacy_event_lookup(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_find_event_list(*args, **kwargs):
        raise AssertionError("HugoCorePassiveTotalizeTrigger should not read raw event_list")

    monkeypatch.setattr(JudgeTools, "find_event_list", fail_find_event_list, raising=False)


def _build_hugo_harness(
    *,
    active_signal: int | None,
    cinema: int,
    enemy_stun: bool,
    rest_tick: int = 360,
) -> SimpleNamespace:
    call_order: list[str] = []
    listener_calls: list[tuple[tuple[object, ...], dict[str, object]]] = []

    def fail_listener_broadcast(*args: object, **kwargs: object) -> None:
        listener_calls.append((args, kwargs))
        raise AssertionError("Hugo totalize should not broadcast listener events")

    dispatch_port = _RecordingDispatchPort(call_order)
    report_calls: list[str] = []

    def change_process_state() -> None:
        report_calls.append("change_process_state")
        call_order.append("change_process_state")

    schedule_data = SimpleNamespace(
        event_list=_FailFastEventList(),
        change_process_state=change_process_state,
    )
    pending_queue = _FailFastPendingQueue()
    sim_instance = SimpleNamespace(
        tick=88,
        schedule_data=schedule_data,
        load_data=SimpleNamespace(LOADING_BUFF_DICT={"雨果": pending_queue}),
        listener_manager=SimpleNamespace(broadcast_event=fail_listener_broadcast),
    )
    buff_instance = SimpleNamespace(
        sim_instance=sim_instance,
        ft=SimpleNamespace(index="hugo-totalize"),
    )
    logic = HugoCorePassiveTotalizeTrigger(
        buff_instance,
        scheduled_event_emitter_provider=ScheduledEventEmitterProvider(lambda: dispatch_port),
    )
    record = HugoCorePassiveTotalizeTriggerRecord()
    record.active_signal = active_signal
    record.char = SimpleNamespace(cinema=cinema)
    record.enemy = SimpleNamespace(
        dynamic=SimpleNamespace(stun=enemy_stun),
        get_stun_rest_tick=lambda: rest_tick,
    )
    record.preload_data = SimpleNamespace(skills=[])
    publish_signal_states: list[int | None] = []
    dispatch_port.on_publish = lambda event: publish_signal_states.append(record.active_signal)
    return SimpleNamespace(
        call_order=call_order,
        dispatch_port=dispatch_port,
        schedule_data=schedule_data,
        sim_instance=sim_instance,
        logic=logic,
        record=record,
        publish_signal_states=publish_signal_states,
        pending_queue=pending_queue,
        listener_calls=listener_calls,
        report_calls=report_calls,
    )


def _patch_runtime_boundary_guards(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_create_runtime_command_port(*args: object, **kwargs: object) -> None:
        raise AssertionError("Hugo totalize should not create RuntimeCommandPort")

    def fail_create_buff_runtime_read_port(*args: object, **kwargs: object) -> None:
        raise AssertionError("Hugo totalize should not create BuffRuntimeReadPort")

    monkeypatch.setattr(
        runtime_command_module,
        "create_runtime_command_port",
        fail_create_runtime_command_port,
    )
    monkeypatch.setattr(
        scheduled_event_module,
        "create_runtime_command_port",
        fail_create_runtime_command_port,
        raising=False,
    )
    monkeypatch.setattr(
        buff_runtime_module,
        "create_buff_runtime_read_port",
        fail_create_buff_runtime_read_port,
    )
    monkeypatch.setattr(
        scheduled_event_module,
        "create_buff_runtime_read_port",
        fail_create_buff_runtime_read_port,
        raising=False,
    )


def _patch_hugo_dependencies(
    monkeypatch: pytest.MonkeyPatch,
    harness: SimpleNamespace,
) -> None:
    _patch_runtime_boundary_guards(monkeypatch)
    monkeypatch.setattr(hugo_module, "HUGO_REPORT", False)

    def fake_check_record_module() -> None:
        harness.logic.record = harness.record

    def fake_get_prepared(**kwargs) -> None:
        return None

    monkeypatch.setattr(harness.logic, "check_record_module", fake_check_record_module)
    monkeypatch.setattr(harness.logic, "get_prepared", fake_get_prepared)
    monkeypatch.setattr(
        hugo_module,
        "find_tick",
        lambda *, sim_instance: sim_instance.tick,
    )
    stun_helper_calls: list[object] = []

    def fake_read_enemy_stun_active(enemy: Any) -> bool:
        stun_helper_calls.append(enemy)
        return bool(enemy.dynamic.stun)

    monkeypatch.setattr(
        hugo_module,
        "read_enemy_stun_active",
        fake_read_enemy_stun_active,
    )
    _block_legacy_event_lookup(monkeypatch)

    buff_add_calls: list[tuple[str, dict[str, object]]] = []

    def fake_buff_add_strategy(buff_index, **kwargs):
        harness.call_order.append(buff_index)
        buff_add_calls.append((buff_index, kwargs))

    monkeypatch.setattr(
        "zsim.sim_progress.Buff.BuffAddStrategy.buff_add_strategy",
        fake_buff_add_strategy,
    )

    expected_node_tag = (
        harness.record.E_totalize_tag
        if harness.record.active_signal == 2
        else harness.record.Q_totalize_tag
    )
    spawned_skill = SimpleNamespace(
        skill_tag=expected_node_tag,
        char_name="Hugo",
        preload_tick=88,
        hit_times=1,
        skill=SimpleNamespace(ticks=20, tick_list=[6], heavy_attack=False),
        end_tick=108,
        loading_mission=None,
    )

    def fake_spawn_node(tag, preload_tick, skills):
        assert tag == expected_node_tag
        assert preload_tick == 88
        assert skills is harness.record.preload_data.skills
        return spawned_skill

    monkeypatch.setattr("zsim.sim_progress.Preload.SkillsQueue.spawn_node", fake_spawn_node)

    original_mission_start = LoadingMission.mission_start

    def fake_mission_start(self, timenow: int, **kwargs) -> None:
        harness.call_order.append("mission_start")
        assert timenow == 88
        original_mission_start(self, timenow, **kwargs)

    monkeypatch.setattr(LoadingMission, "mission_start", fake_mission_start)

    harness.buff_add_calls = buff_add_calls
    harness.spawned_skill = spawned_skill
    harness.stun_helper_calls = stun_helper_calls


def _build_hugo_judge_skill(
    *,
    skill_tag: str = "1291_E_EX_2",
    trigger_buff_level: int = 2,
    is_last_hit: bool = True,
) -> SkillNode:
    skill_node = SkillNode.__new__(SkillNode)
    skill_node.skill_tag = skill_tag
    skill_node.skill = SimpleNamespace(
        trigger_buff_level=trigger_buff_level,
        labels=None,
    )
    skill_node.loading_mission = SimpleNamespace(
        is_last_hit=lambda tick: is_last_hit,
    )
    return skill_node


def _assert_buff_add_calls(
    harness: SimpleNamespace,
    expected: list[tuple[str, int | float | None]],
) -> None:
    assert [buff_index for buff_index, _ in harness.buff_add_calls] == [
        buff_index for buff_index, _ in expected
    ]
    for (buff_index, kwargs), (expected_index, specified_count) in zip(
        harness.buff_add_calls, expected, strict=True
    ):
        assert buff_index == expected_index
        assert kwargs["sim_instance"] is harness.sim_instance
        assert kwargs["benifit_list"] == ["雨果"]
        assert ("specified_count" in kwargs) is (specified_count is not None)
        if specified_count is not None:
            assert kwargs["specified_count"] == specified_count
        assert set(kwargs) <= {"benifit_list", "sim_instance", "specified_count"}


def _assert_no_raw_runtime_side_effects(harness: SimpleNamespace) -> None:
    assert harness.schedule_data.event_list == []
    assert harness.pending_queue == []
    assert harness.listener_calls == []
    write_method_names = {
        "append_active_buff",
        "remove_active_buff",
        "sync_enemy_debuff_mirror",
        "replace_buff",
        "write_buff",
    }
    assert write_method_names.isdisjoint(BuffRuntimeReadPort.__dict__)


def test_hugo_totalize_node_publishes_via_dispatch_port_before_any_raw_queue_access(
    monkeypatch: pytest.MonkeyPatch,
):
    harness = _build_hugo_harness(active_signal=2, cinema=6, enemy_stun=False)
    _patch_hugo_dependencies(monkeypatch, harness)

    harness.logic.special_hit_logic()

    assert harness.call_order == [
        harness.record.totalize_buff_index,
        harness.record.cinema_1_buff_index,
        harness.record.cinema_2_buff_index,
        harness.record.cinema_6_buff_index,
        "mission_start",
        "publish",
    ]
    _assert_buff_add_calls(
        harness,
        [
            (harness.record.totalize_buff_index, 2500.0),
            (harness.record.cinema_1_buff_index, None),
            (harness.record.cinema_2_buff_index, None),
            (harness.record.cinema_6_buff_index, None),
        ],
    )
    assert len(harness.dispatch_port.events) == 1
    published_node = harness.dispatch_port.events[0]
    assert published_node is harness.spawned_skill
    assert published_node.loading_mission is not None
    assert isinstance(published_node.loading_mission, LoadingMission)
    assert published_node.loading_mission.mission_node is published_node
    assert published_node.loading_mission.mission_active_state is True
    assert published_node.loading_mission.mission_start_tick == 88
    assert published_node.loading_mission.mission_dict[88.0] == "start"
    assert harness.publish_signal_states == [2]
    assert harness.stun_helper_calls == [harness.record.enemy]
    _assert_no_raw_runtime_side_effects(harness)
    assert harness.record.active_signal is None


def test_hugo_stun_event_publishes_via_dispatch_port_when_branch_conditions_match(
    monkeypatch: pytest.MonkeyPatch,
):
    harness = _build_hugo_harness(active_signal=2, cinema=1, enemy_stun=True)
    _patch_hugo_dependencies(monkeypatch, harness)

    harness.logic.special_hit_logic()

    assert harness.call_order == [
        harness.record.totalize_buff_index,
        harness.record.cinema_1_buff_index,
        "mission_start",
        "publish",
        "publish",
    ]
    _assert_buff_add_calls(
        harness,
        [
            (harness.record.totalize_buff_index, 2500.0),
            (harness.record.cinema_1_buff_index, None),
        ],
    )
    assert len(harness.dispatch_port.events) == 2
    assert harness.dispatch_port.events[0] is harness.spawned_skill
    published_stun_event = harness.dispatch_port.events[1]
    assert isinstance(published_stun_event, StunForcedTerminationEvent)
    assert published_stun_event.enemy is harness.record.enemy
    assert published_stun_event.feed_back_ratio == 0.25
    assert published_stun_event.execute_tick == 88
    assert harness.publish_signal_states == [2, 2]
    assert harness.stun_helper_calls == [harness.record.enemy]
    _assert_no_raw_runtime_side_effects(harness)
    assert harness.record.active_signal is None


def test_hugo_report_state_stays_before_publish_when_enabled(
    monkeypatch: pytest.MonkeyPatch,
):
    harness = _build_hugo_harness(active_signal=2, cinema=6, enemy_stun=False)
    _patch_hugo_dependencies(monkeypatch, harness)
    monkeypatch.setattr(hugo_module, "HUGO_REPORT", True)
    monkeypatch.setattr("builtins.print", lambda *args, **kwargs: None)

    harness.logic.special_hit_logic()

    assert harness.report_calls == ["change_process_state"]
    assert harness.call_order == [
        "change_process_state",
        harness.record.totalize_buff_index,
        harness.record.cinema_1_buff_index,
        harness.record.cinema_2_buff_index,
        harness.record.cinema_6_buff_index,
        "mission_start",
        "publish",
    ]
    assert harness.dispatch_port.events == [harness.spawned_skill]
    assert harness.publish_signal_states == [2]
    assert harness.stun_helper_calls == [harness.record.enemy]
    _assert_no_raw_runtime_side_effects(harness)
    assert harness.record.active_signal is None


def test_hugo_cinema_two_ultimate_keeps_stun_event_skipped_after_gateway_migration(
    monkeypatch: pytest.MonkeyPatch,
):
    harness = _build_hugo_harness(active_signal=6, cinema=2, enemy_stun=True)
    _patch_hugo_dependencies(monkeypatch, harness)

    harness.logic.special_hit_logic()

    assert harness.call_order == [
        harness.record.totalize_buff_index,
        harness.record.cinema_1_buff_index,
        harness.record.cinema_2_buff_index,
        "mission_start",
        "publish",
    ]
    _assert_buff_add_calls(
        harness,
        [
            (harness.record.totalize_buff_index, 2500.0),
            (harness.record.cinema_1_buff_index, None),
            (harness.record.cinema_2_buff_index, None),
        ],
    )
    assert len(harness.dispatch_port.events) == 1
    assert harness.dispatch_port.events[0] is harness.spawned_skill
    assert harness.publish_signal_states == [6]
    assert harness.stun_helper_calls == [harness.record.enemy]
    _assert_no_raw_runtime_side_effects(harness)
    assert harness.record.active_signal is None


def test_hugo_judge_non_cinema_six_uses_stun_helper_to_set_active_signal_without_publish(
    monkeypatch: pytest.MonkeyPatch,
):
    harness = _build_hugo_harness(active_signal=None, cinema=1, enemy_stun=True)
    _patch_hugo_dependencies(monkeypatch, harness)

    assert harness.logic.special_judge_logic(skill_node=_build_hugo_judge_skill()) is True

    assert harness.call_order == []
    assert harness.buff_add_calls == []
    assert harness.dispatch_port.events == []
    assert harness.publish_signal_states == []
    assert harness.report_calls == []
    assert harness.stun_helper_calls == [harness.record.enemy]
    _assert_no_raw_runtime_side_effects(harness)
    assert harness.record.active_signal == 2


def test_hugo_judge_non_cinema_six_requires_stun_without_publish(
    monkeypatch: pytest.MonkeyPatch,
):
    harness = _build_hugo_harness(active_signal=None, cinema=1, enemy_stun=False)
    _patch_hugo_dependencies(monkeypatch, harness)

    assert harness.logic.special_judge_logic(skill_node=_build_hugo_judge_skill()) is False

    assert harness.call_order == []
    assert harness.buff_add_calls == []
    assert harness.dispatch_port.events == []
    assert harness.publish_signal_states == []
    assert harness.report_calls == []
    assert harness.stun_helper_calls == [harness.record.enemy]
    _assert_no_raw_runtime_side_effects(harness)
    assert harness.record.active_signal is None


def test_hugo_active_signal_zero_resets_without_scheduled_publish(
    monkeypatch: pytest.MonkeyPatch,
):
    harness = _build_hugo_harness(active_signal=0, cinema=6, enemy_stun=False)
    _patch_hugo_dependencies(monkeypatch, harness)

    harness.logic.special_hit_logic()

    assert harness.call_order == [harness.record.abyss_reverb_buff_index]
    _assert_buff_add_calls(
        harness,
        [(harness.record.abyss_reverb_buff_index, None)],
    )
    assert harness.dispatch_port.events == []
    assert harness.publish_signal_states == []
    assert harness.stun_helper_calls == []
    _assert_no_raw_runtime_side_effects(harness)
    assert harness.record.active_signal is None


def test_hugo_judge_without_skill_node_does_not_force_buff_add(
    monkeypatch: pytest.MonkeyPatch,
):
    harness = _build_hugo_harness(active_signal=None, cinema=6, enemy_stun=True)
    _patch_hugo_dependencies(monkeypatch, harness)

    assert harness.logic.special_judge_logic() is False

    assert harness.call_order == []
    assert harness.buff_add_calls == []
    assert harness.dispatch_port.events == []
    assert harness.publish_signal_states == []
    assert harness.stun_helper_calls == []
    _assert_no_raw_runtime_side_effects(harness)
    assert harness.record.active_signal is None
