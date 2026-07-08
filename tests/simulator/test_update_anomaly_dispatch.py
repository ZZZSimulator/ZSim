from __future__ import annotations

import inspect
from types import SimpleNamespace
from typing import Any, cast

import numpy as np
import pytest

import zsim.sim_progress.anomaly_bar.CopyAnomalyForOutput as copied_output_module
import zsim.sim_progress.Buff.BuffAddStrategy as buff_add_strategy_module
from zsim.models.event_enums import ListenerBroadcastSignal as LBS
from zsim.sim_progress.anomaly_bar import AnomalyBar
from zsim.sim_progress.anomaly_bar.CopyAnomalyForOutput import (
    Disorder,
    NewAnomaly,
    PolarityDisorder,
)
from zsim.sim_progress.data_struct.planned_queue import PlannedEventQueue
from zsim.sim_progress.data_struct.schedule_dispatch import create_schedule_dispatch_port
from zsim.sim_progress.Dot.BaseDot import Dot
from zsim.sim_progress.Dot.runtime_state import DotRuntimeStateAdapter
from zsim.sim_progress.Update import UpdateAnomaly as update_anomaly_module
from zsim.sim_progress.Update.UpdateAnomaly import (
    anomaly_effect_active,
    remove_dots_cause_disorder,
    spawn_output,
    update_anomaly,
)

_CallRecord = tuple[str, object]
_HelperCallRecord = tuple[object, ...]


class _FailFastEventList(list):
    def append(self, item):
        raise AssertionError("UpdateAnomaly should publish scheduled events via dispatch port")


class _RecordingEventList(list):
    def __init__(self, call_order: list[tuple[str, object]] | None = None) -> None:
        super().__init__()
        self._call_order = call_order

    def append(self, item):
        if self._call_order is not None:
            self._call_order.append(("publish", item))
        super().append(item)


class _RecordingDotRuntimeList(list):
    def __init__(
        self,
        call_order: list[tuple[str, object]],
        items: list[object] | None = None,
    ) -> None:
        super().__init__(items or [])
        self._call_order = call_order

    def append(self, item):
        self._call_order.append(("dot_append", item.ft.index))
        super().append(item)

    def remove(self, item):
        self._call_order.append(("dot_remove", item.ft.index))
        super().remove(item)


class _FailFastDotRuntimeList(list):
    def append(self, item):
        raise AssertionError("debuff-only anomaly effects should not register runtime dots")

    def remove(self, item):
        raise AssertionError("debuff-only anomaly effects should not remove runtime dots")


class _FailFastPendingBuffQueue(list):
    def append(self, item):
        raise AssertionError("anomaly effects should not write pending Buff queues")

    def extend(self, items):
        raise AssertionError("anomaly effects should not write pending Buff queues")

    def insert(self, index, item):
        raise AssertionError("anomaly effects should not write pending Buff queues")

    def clear(self):
        raise AssertionError("anomaly effects should not write pending Buff queues")


class _RecordingDotRuntimeStateAdapter(DotRuntimeStateAdapter):
    def __init__(
        self,
        dynamic_state,
        helper_calls: list[_HelperCallRecord],
    ) -> None:
        super().__init__(dynamic_state)
        self._helper_calls = helper_calls

    def replace_by_index(self, dot: Dot, timenow: int) -> tuple[Dot, ...]:
        self._helper_calls.append(("replace_by_index", dot, timenow))
        return super().replace_by_index(dot, timenow)

    def remove_all(self, dots) -> tuple[Dot, ...]:
        dots_tuple = tuple(dots)
        self._helper_calls.append(("remove_all", dots_tuple))
        return super().remove_all(dots_tuple)


def _record_dot_runtime_state_adapter(monkeypatch, helper_calls):
    def recording_from_enemy(cls, enemy):
        helper_calls.append(("from_enemy", enemy))
        return _RecordingDotRuntimeStateAdapter(enemy.dynamic, helper_calls)

    monkeypatch.setattr(
        update_anomaly_module.DotRuntimeStateAdapter,
        "from_enemy",
        classmethod(recording_from_enemy),
    )


class _RecordingDotDynamicState:
    _call_order: list[_CallRecord]
    _recording_enabled: bool

    def __init__(
        self,
        call_order: list[_CallRecord],
        *,
        effect_times: int = 0,
        ready: bool | None = True,
    ) -> None:
        object.__setattr__(self, "_call_order", call_order)
        object.__setattr__(self, "_recording_enabled", False)
        self.active = True
        self.count = 0
        self.start_ticks = 0
        self.last_effect_ticks = 0
        self.ready = ready
        self.effect_times = effect_times
        object.__setattr__(self, "_recording_enabled", True)

    def __setattr__(self, name: str, value: object) -> None:
        if getattr(self, "_recording_enabled", False) and name in {
            "ready",
            "last_effect_ticks",
            "effect_times",
        }:
            self._call_order.append((f"dy_{name}", value))
        object.__setattr__(self, name, value)


class _ForbiddenListenerManager:
    def broadcast_event(self, **kwargs):
        raise AssertionError("dot replacement should not use listener broadcast")


class _ForbiddenRuntimeCommandPort:
    def update_anomaly(self, **kwargs):
        raise AssertionError("scheduled-publish parity tests should not issue runtime commands")


class _FakeDot(Dot):
    def __init__(
        self,
        *,
        index: str,
        anomaly_data=None,
        call_order: list[tuple[str, object]] | None = None,
    ):
        super().__init__(bar=None, sim_instance=None)
        self.ft.index = index
        self.ft.max_effect_times = 30
        self.anomaly_data = anomaly_data
        self.ended_at: int | None = None
        self._call_order = call_order

    def end(self, timenow: int):
        if self._call_order is not None:
            self._call_order.append(("dot_end", self.ft.index))
        self.ended_at = timenow
        super().end(timenow)


def _build_sim_instance(
    event_list,
    call_order: list[tuple[str, object]] | None = None,
):
    def broadcast_event(**kwargs):
        if call_order is not None:
            call_order.append(("broadcast", kwargs["signal"]))

    schedule_data = SimpleNamespace(
        event_list=event_list,
        change_process_state=lambda: None,
    )
    schedule_data.planned_event_queue = PlannedEventQueue(
        get_events=lambda: schedule_data.event_list,
        set_events=lambda events: setattr(schedule_data, "event_list", events),
    )

    return SimpleNamespace(
        tick=10,
        schedule_data=schedule_data,
        listener_manager=SimpleNamespace(broadcast_event=broadcast_event),
        decibel_manager=SimpleNamespace(update=lambda **kwargs: None),
        runtime_command_port=_ForbiddenRuntimeCommandPort(),
    )


def _build_enemy(sim_instance):
    state_attr_map = {index: f"anomaly_state_{index}" for index in range(7)}
    dynamic = SimpleNamespace(
        active_anomaly_bar_dict={index: None for index in range(7)},
        frozen=False,
        frostbite=False,
        dynamic_dot_list=[],
    )
    for attr_name in state_attr_map.values():
        setattr(dynamic, attr_name, False)
    return SimpleNamespace(
        sim_instance=sim_instance,
        dynamic=dynamic,
        anomaly_bars_dict={},
        trans_element_number_to_str={
            0: "physical",
            1: "fire",
            2: "ice",
            3: "electric",
            4: "ether",
            5: "frost",
            6: "auricink",
        },
        trans_anomaly_effect_to_str=state_attr_map,
        max_anomaly_physical=100,
        max_anomaly_fire=100,
        max_anomaly_ice=100,
        max_anomaly_electric=100,
        max_anomaly_ether=100,
        max_anomaly_frost=100,
        max_anomaly_auricink=100,
        update_max_anomaly=lambda element_type: None,
    )


def _build_anomaly_bar(sim_instance, *, element_type: int) -> AnomalyBar:
    bar = AnomalyBar(sim_instance=sim_instance, element_type=element_type)
    bar.max_anomaly = 100
    bar.current_anomaly = 100
    bar.ready = True
    bar.basic_max_duration = 60
    bar.ndarray_box = [(element_type, np.float64(100), np.ones((1, 1), dtype=np.float64))]
    return bar


def _build_spawn_output_source_bar(
    sim_instance,
    *,
    element_type: int,
    settled: bool,
) -> AnomalyBar:
    bar = _build_anomaly_bar(sim_instance, element_type=element_type)
    snapshot = np.array([[1.25, 2.5, 3.75]], dtype=np.float64)
    bar.current_anomaly = np.float64(100)
    bar.current_effective_anomaly = np.float64(100 if settled else 0)
    bar.current_ndarray = snapshot.copy()
    bar.ndarray_box = [] if settled else [(element_type, np.float64(100), snapshot)]
    bar.settled = settled
    bar.active = True
    bar.anomaly_dmg_ratio = 2.25
    bar.scaling_factor = 1.5
    bar.max_duration = 420
    bar.last_active = 120
    bar.accompany_dot = "Shock"
    bar.rename_tag = f"spawn-output-mode-{element_type}"
    return bar


def _build_skill_node(*, element_type: int, char_name: str = "alpha", skill_tag: str = "1001_TEST"):
    return SimpleNamespace(
        element_type=element_type,
        char_name=char_name,
        skill_tag=skill_tag,
        skill=SimpleNamespace(char_obj=SimpleNamespace(CID=1001)),
    )


def test_anomaly_runtime_context_builds_explicit_layer_collaborators(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dispatch_port = object()
    dot_runtime_state = object()
    dispatch_calls: list[tuple[object, object]] = []
    dot_calls: list[object] = []

    def fake_create_schedule_dispatch_port(*, sim_instance, schedule_data=None):
        dispatch_calls.append((sim_instance, schedule_data))
        return dispatch_port

    def fake_from_enemy(cls, enemy):
        dot_calls.append(enemy)
        return dot_runtime_state

    def broadcast_event(**kwargs):
        raise AssertionError("context construction should not broadcast listener events")

    monkeypatch.setattr(
        update_anomaly_module,
        "create_schedule_dispatch_port",
        fake_create_schedule_dispatch_port,
    )
    monkeypatch.setattr(
        update_anomaly_module.DotRuntimeStateAdapter,
        "from_enemy",
        classmethod(fake_from_enemy),
    )

    schedule_data = SimpleNamespace(event_list=[])
    listener_manager = SimpleNamespace(broadcast_event=broadcast_event)
    sim_instance = SimpleNamespace(listener_manager=listener_manager)
    enemy = object()
    buff_runtime_view = object()

    context = update_anomaly_module.create_anomaly_runtime_context(
        sim_instance=cast(Any, sim_instance),
        enemy=enemy,
        buff_runtime_view=cast(Any, buff_runtime_view),
        schedule_data=schedule_data,
    )

    assert dispatch_calls == [(sim_instance, schedule_data)]
    assert dot_calls == [enemy]
    assert sim_instance.schedule_data is schedule_data
    assert context.dispatch_port is dispatch_port
    assert context.listener_broadcaster is listener_manager.broadcast_event
    assert context.dot_runtime_state is dot_runtime_state
    assert context.buff_runtime_view is buff_runtime_view
    assert context.sim_instance is sim_instance


def test_spawn_output_mode_zero_settles_without_listener_or_scheduled_publish():
    call_order: list[tuple[str, object]] = []
    broadcast_events: list[tuple[object, object]] = []
    recording_queue = _RecordingEventList(call_order)
    sim_instance = _build_sim_instance(recording_queue)
    sim_instance.load_data = SimpleNamespace(
        LOADING_BUFF_DICT={"enemy": _FailFastPendingBuffQueue()}
    )

    def record_broadcast(*, event: object, signal: object) -> None:
        call_order.append(("broadcast", signal))
        broadcast_events.append((event, signal))

    sim_instance.listener_manager = SimpleNamespace(broadcast_event=record_broadcast)
    source_bar = _build_spawn_output_source_bar(
        sim_instance,
        element_type=4,
        settled=False,
    )
    skill_node = _build_skill_node(element_type=4)

    output = spawn_output(
        source_bar,
        0,
        sim_instance=sim_instance,
        skill_node=skill_node,
    )

    assert type(output) is NewAnomaly
    assert output is not source_bar
    assert output.sim_instance is sim_instance
    assert output.activated_by is skill_node
    assert output.activate_by is skill_node
    assert output.is_disorder is False
    assert output.element_type == 4
    assert output.accompany_dot == "Shock"
    assert output.rename_tag == "spawn-output-mode-4"
    assert output.anomaly_dmg_ratio == pytest.approx(2.25)
    assert output.scaling_factor == pytest.approx(1.5)
    assert output.max_duration == 420
    assert output.last_active == 120
    assert output.current_effective_anomaly == pytest.approx(100)
    assert source_bar.settled is True
    assert output.current_ndarray is not source_bar.current_ndarray
    np.testing.assert_allclose(
        output.current_ndarray,
        np.array([[1.25, 2.5, 3.75]], dtype=np.float64),
    )
    assert output.schedule_priority == 999
    assert not hasattr(output, "execute_tick")
    assert recording_queue == []
    assert broadcast_events == []
    assert call_order == []


@pytest.mark.parametrize(
    ("mode_number", "expected_type", "kwargs", "expected_polarity_ratio"),
    [
        pytest.param(1, Disorder, {}, None, id="disorder"),
        pytest.param(
            2,
            PolarityDisorder,
            {"polarity_ratio": 1.6},
            1.6,
            id="polarity-disorder",
        ),
    ],
)
def test_spawn_output_disorder_modes_broadcast_listener_payload_without_publish(
    mode_number,
    expected_type,
    kwargs,
    expected_polarity_ratio,
):
    call_order: list[tuple[str, object]] = []
    broadcast_events: list[tuple[object, object]] = []
    recording_queue = _RecordingEventList(call_order)
    sim_instance = _build_sim_instance(recording_queue)
    sim_instance.load_data = SimpleNamespace(
        LOADING_BUFF_DICT={"enemy": _FailFastPendingBuffQueue()}
    )

    def record_broadcast(*, event: object, signal: object) -> None:
        call_order.append(("broadcast", signal))
        broadcast_events.append((event, signal))

    sim_instance.listener_manager = SimpleNamespace(broadcast_event=record_broadcast)
    source_bar = _build_spawn_output_source_bar(
        sim_instance,
        element_type=3,
        settled=True,
    )
    source_owner = _build_skill_node(
        element_type=3,
        char_name="source-owner",
        skill_tag="1001_SOURCE",
    )
    source_bar.activated_by = source_owner
    skill_node = _build_skill_node(element_type=3)

    output = spawn_output(
        source_bar,
        mode_number,
        sim_instance=sim_instance,
        skill_node=skill_node,
        **kwargs,
    )

    assert type(output) is expected_type
    assert output is not source_bar
    assert output.sim_instance is sim_instance
    assert output.activated_by is not source_owner
    assert output.activated_by.skill is source_owner.skill
    assert output.activated_by.skill_tag == source_owner.skill_tag
    assert output.activate_by is skill_node
    assert output.is_disorder is True
    assert output.settled is True
    assert output.element_type == 3
    assert output.accompany_dot == "Shock"
    assert output.rename_tag == "spawn-output-mode-3"
    assert output.anomaly_dmg_ratio == pytest.approx(2.25)
    assert output.scaling_factor == pytest.approx(1.5)
    assert output.max_duration == 420
    assert output.last_active == 120
    assert output.current_effective_anomaly == pytest.approx(100)
    assert output.current_ndarray is not source_bar.current_ndarray
    np.testing.assert_allclose(
        output.current_ndarray,
        np.array([[1.25, 2.5, 3.75]], dtype=np.float64),
    )
    if expected_polarity_ratio is None:
        assert not hasattr(output, "polarity_disorder_ratio")
        assert not hasattr(output, "additional_dmg_ap_ratio")
    else:
        assert output.polarity_disorder_ratio == pytest.approx(expected_polarity_ratio)
        assert output.additional_dmg_ap_ratio == 32
    assert output.schedule_priority == 999
    assert not hasattr(output, "execute_tick")
    assert recording_queue == []
    assert broadcast_events == [(output, LBS.DISORDER_SPAWN)]
    assert call_order == [("broadcast", LBS.DISORDER_SPAWN)]


def test_spawn_output_mode_two_requires_polarity_ratio_without_side_effects():
    call_order: list[tuple[str, object]] = []
    broadcast_events: list[tuple[object, object]] = []
    recording_queue = _RecordingEventList(call_order)
    sim_instance = _build_sim_instance(recording_queue)
    sim_instance.load_data = SimpleNamespace(
        LOADING_BUFF_DICT={"enemy": _FailFastPendingBuffQueue()}
    )

    def record_broadcast(*, event: object, signal: object) -> None:
        call_order.append(("broadcast", signal))
        broadcast_events.append((event, signal))

    sim_instance.listener_manager = SimpleNamespace(broadcast_event=record_broadcast)
    source_bar = _build_spawn_output_source_bar(
        sim_instance,
        element_type=3,
        settled=False,
    )
    source_snapshot = source_bar.current_ndarray.copy()

    with pytest.raises(ValueError, match="polarity_ratio"):
        spawn_output(
            source_bar,
            2,
            sim_instance=sim_instance,
            skill_node=_build_skill_node(element_type=3),
        )

    assert source_bar.settled is False
    assert source_bar.current_effective_anomaly == np.float64(0)
    np.testing.assert_allclose(source_bar.current_ndarray, source_snapshot)
    assert recording_queue == []
    assert broadcast_events == []
    assert call_order == []


def test_spawn_output_invalid_mode_rejects_without_side_effects(monkeypatch):
    call_order: list[tuple[str, object]] = []
    broadcast_events: list[tuple[object, object]] = []
    recording_queue = _RecordingEventList(call_order)
    sim_instance = _build_sim_instance(recording_queue)
    sim_instance.load_data = SimpleNamespace(
        LOADING_BUFF_DICT={"enemy": _FailFastPendingBuffQueue()}
    )

    def record_broadcast(*, event: object, signal: object) -> None:
        call_order.append(("broadcast", signal))
        broadcast_events.append((event, signal))

    def fail_constructor(*args, **kwargs):
        raise AssertionError("invalid spawn_output mode must not construct copied output")

    monkeypatch.setattr(update_anomaly_module, "NewAnomaly", fail_constructor)
    monkeypatch.setattr(update_anomaly_module, "Disorder", fail_constructor)
    monkeypatch.setattr(update_anomaly_module, "PolarityDisorder", fail_constructor)

    sim_instance.listener_manager = SimpleNamespace(broadcast_event=record_broadcast)
    source_bar = _build_spawn_output_source_bar(
        sim_instance,
        element_type=3,
        settled=False,
    )
    source_snapshot = source_bar.current_ndarray.copy()

    with pytest.raises(ValueError, match="spawn_output"):
        spawn_output(
            source_bar,
            99,
            sim_instance=sim_instance,
            skill_node=_build_skill_node(element_type=3),
        )

    assert source_bar.settled is False
    assert source_bar.current_effective_anomaly == np.float64(0)
    np.testing.assert_allclose(source_bar.current_ndarray, source_snapshot)
    assert recording_queue == []
    assert broadcast_events == []
    assert call_order == []


def test_update_anomaly_publishes_new_anomaly_via_dispatch_port_without_raw_queue_append():
    call_order: list[tuple[str, object]] = []
    legacy_event_list = _FailFastEventList()
    sim_instance = _build_sim_instance(legacy_event_list, call_order)
    enemy = _build_enemy(sim_instance)
    enemy.anomaly_bars_dict[1] = _build_anomaly_bar(sim_instance, element_type=1)
    skill_node = _build_skill_node(element_type=1)
    chars = [SimpleNamespace(special_resources=lambda *args, **kwargs: None)]

    recording_queue = _RecordingEventList(call_order)
    sim_instance.schedule_data.event_list = recording_queue

    update_anomaly(
        1,
        enemy,
        10,
        chars,
        sim_instance,
        skill_node,
        {"alpha": [], "enemy": []},
    )

    assert len(recording_queue) == 1
    published = recording_queue[0]
    assert call_order == [("broadcast", LBS.ANOMALY), ("publish", published)]
    assert published.element_type == 1
    assert published.activated_by is skill_node
    assert published.is_disorder is False
    assert published.schedule_priority == 999
    assert not hasattr(published, "execute_tick")


def test_update_anomaly_uses_current_schedule_queue_after_event_list_rebind():
    first_queue = _RecordingEventList()
    sim_instance = _build_sim_instance(first_queue)
    skill_node = _build_skill_node(element_type=1)
    chars = [SimpleNamespace(special_resources=lambda *args, **kwargs: None)]

    first_enemy = _build_enemy(sim_instance)
    first_enemy.anomaly_bars_dict[1] = _build_anomaly_bar(sim_instance, element_type=1)
    update_anomaly(
        1,
        first_enemy,
        10,
        chars,
        sim_instance,
        skill_node,
        {"alpha": [], "enemy": []},
    )

    second_queue = _RecordingEventList()
    sim_instance.schedule_data.event_list = second_queue
    second_enemy = _build_enemy(sim_instance)
    second_enemy.anomaly_bars_dict[1] = _build_anomaly_bar(sim_instance, element_type=1)
    update_anomaly(
        1,
        second_enemy,
        20,
        chars,
        sim_instance,
        skill_node,
        {"alpha": [], "enemy": []},
    )

    assert len(first_queue) == 1
    assert len(second_queue) == 1
    assert first_queue[0] is not second_queue[0]
    assert second_queue[0].sim_instance is sim_instance


@pytest.mark.parametrize(
    ("element_type", "should_publish_new_anomaly"),
    [
        pytest.param(1, True, id="non-ice-new-anomaly-published"),
        pytest.param(2, False, id="ice-new-anomaly-not-published"),
    ],
)
def test_update_anomaly_preserves_disorder_branch_order_state_and_optional_new_publish(
    monkeypatch,
    element_type,
    should_publish_new_anomaly,
):
    call_order: list[tuple[str, object]] = []
    broadcast_events: list[tuple[object, object]] = []
    helper_calls: list[_HelperCallRecord] = []
    legacy_event_list = _FailFastEventList()
    sim_instance = _build_sim_instance(legacy_event_list, call_order)
    sim_instance.decibel_manager.update = lambda **kwargs: call_order.append(
        ("decibel", kwargs["key"])
    )
    sim_instance.schedule_data.change_process_state = lambda: call_order.append(
        ("change_process_state", None)
    )

    def record_broadcast(*, event: object, signal: object) -> None:
        call_order.append(("broadcast", signal))
        broadcast_events.append((event, signal))

    sim_instance.listener_manager = SimpleNamespace(broadcast_event=record_broadcast)
    enemy = _build_enemy(sim_instance)
    current_bar = _build_anomaly_bar(sim_instance, element_type=element_type)
    current_bar.accompany_dot = "NewShock"
    current_bar.anomaly_dmg_ratio = 2.25
    current_bar.scaling_factor = 1.5
    current_bar.basic_max_duration = 420
    current_bar.ndarray_box = [
        (element_type, np.float64(40), np.array([[2.0, 4.0]], dtype=np.float64)),
        (element_type, np.float64(60), np.array([[6.0, 8.0]], dtype=np.float64)),
    ]
    previous_bar = _build_anomaly_bar(sim_instance, element_type=3)
    previous_bar.active = True
    previous_bar.settled = True
    previous_bar.current_effective_anomaly = np.float64(100)
    previous_bar.current_ndarray = np.array([[9.0, 11.0]], dtype=np.float64)
    previous_bar.ndarray_box = []
    previous_bar.max_duration = 315
    previous_bar.last_active = 5
    previous_bar.accompany_dot = "OldShock"
    previous_owner = _build_skill_node(
        element_type=3,
        char_name="previous-owner",
        skill_tag="1001_PREVIOUS",
    )
    previous_bar.activated_by = previous_owner
    enemy.anomaly_bars_dict[element_type] = current_bar
    enemy.anomaly_bars_dict[3] = previous_bar
    enemy.dynamic.active_anomaly_bar_dict[3] = previous_bar
    setattr(enemy.dynamic, enemy.trans_anomaly_effect_to_str[3], True)
    old_dot = _FakeDot(index="OldShock", call_order=call_order)
    enemy.dynamic.dynamic_dot_list = _RecordingDotRuntimeList(call_order, [old_dot])
    skill_node = _build_skill_node(element_type=element_type)
    chars = [
        SimpleNamespace(
            special_resources=lambda anomaly: call_order.append(("special_resources", anomaly))
        )
    ]
    new_dot = _FakeDot(index="NewShock", call_order=call_order)
    spawn_calls: list[tuple[object, int, object, object]] = []

    def fake_spawn_anomaly_dot(element_type, timenow, *, bar, sim_instance):
        spawn_calls.append((element_type, timenow, bar, sim_instance))
        return new_dot

    monkeypatch.setattr(
        update_anomaly_module,
        "spawn_anomaly_dot",
        fake_spawn_anomaly_dot,
    )
    _record_dot_runtime_state_adapter(monkeypatch, helper_calls)

    recording_queue = _RecordingEventList(call_order)
    sim_instance.schedule_data.event_list = recording_queue

    update_anomaly(
        element_type,
        enemy,
        10,
        chars,
        sim_instance,
        skill_node,
        {"alpha": [], "enemy": []},
    )

    assert len(spawn_calls) == 1
    new_anomaly = spawn_calls[0][2]
    disorder = recording_queue[-1]
    expected_order = [
        ("decibel", "anomaly"),
        ("broadcast", LBS.ANOMALY),
        ("broadcast", LBS.DISORDER_SPAWN),
        ("dot_end", "OldShock"),
        ("dot_remove", "OldShock"),
        ("change_process_state", None),
        ("dot_append", "NewShock"),
    ]
    if should_publish_new_anomaly:
        expected_order.append(("publish", new_anomaly))
    expected_order.extend(
        [
            ("special_resources", disorder),
            ("publish", disorder),
            ("decibel", "disorder"),
            ("change_process_state", None),
        ]
    )
    assert call_order == expected_order
    if should_publish_new_anomaly:
        assert recording_queue == [new_anomaly, disorder]
    else:
        assert recording_queue == [disorder]
    assert broadcast_events == [
        (enemy.dynamic.active_anomaly_bar_dict[element_type], LBS.ANOMALY),
        (disorder, LBS.DISORDER_SPAWN),
    ]
    assert helper_calls == [
        ("from_enemy", enemy),
        ("remove_all", (old_dot,)),
        ("replace_by_index", new_dot, 10),
    ]

    assert enemy.dynamic.active_anomaly_bar_dict[3] is None
    assert previous_bar.active is False
    assert getattr(enemy.dynamic, enemy.trans_anomaly_effect_to_str[3]) is False
    assert getattr(enemy.dynamic, enemy.trans_anomaly_effect_to_str[element_type]) is True
    assert enemy.dynamic.frozen is (element_type == 2)
    assert old_dot.ended_at == 10
    assert enemy.dynamic.dynamic_dot_list == [new_dot]

    active_bar = enemy.dynamic.active_anomaly_bar_dict[element_type]
    assert active_bar is not current_bar
    assert active_bar.active is True
    assert active_bar.settled is True
    assert current_bar.current_anomaly == np.float64(0)
    assert current_bar.current_effective_anomaly == np.float64(0)
    assert current_bar.ndarray_box == []
    np.testing.assert_array_equal(
        current_bar.current_ndarray,
        np.zeros((1, 1), dtype=np.float64),
    )

    assert spawn_calls == [(element_type, 10, new_anomaly, sim_instance)]
    assert new_anomaly.element_type == element_type
    assert new_anomaly.activated_by is skill_node
    assert new_anomaly.activate_by is skill_node
    assert new_anomaly.is_disorder is False
    assert new_anomaly.accompany_dot == "NewShock"
    assert new_anomaly.schedule_priority == 999
    assert not hasattr(new_anomaly, "execute_tick")
    assert new_anomaly.current_effective_anomaly == np.float64(100)
    np.testing.assert_allclose(
        new_anomaly.current_ndarray,
        np.array([[4.4, 6.4]], dtype=np.float64),
    )

    assert disorder.element_type == 3
    assert disorder.activated_by is not previous_owner
    assert disorder.activated_by.skill is previous_owner.skill
    assert disorder.activated_by.skill_tag == previous_owner.skill_tag
    assert disorder.activate_by is skill_node
    assert disorder.is_disorder is True
    assert disorder.settled is True
    assert disorder.current_effective_anomaly == np.float64(100)
    np.testing.assert_allclose(
        disorder.current_ndarray,
        np.array([[9.0, 11.0]], dtype=np.float64),
    )
    assert disorder.remaining_tick() == pytest.approx(310)
    assert disorder.accompany_dot == "OldShock"
    assert disorder.schedule_priority == 999
    assert not hasattr(disorder, "execute_tick")


def test_update_anomaly_records_new_anomaly_field_matrix_with_runtime_dot(
    monkeypatch,
):
    call_order: list[tuple[str, object]] = []
    helper_calls: list[_HelperCallRecord] = []
    legacy_event_list = _FailFastEventList()
    sim_instance = _build_sim_instance(legacy_event_list, call_order)
    enemy = _build_enemy(sim_instance)
    source_bar = _build_anomaly_bar(sim_instance, element_type=3)
    source_bar.accompany_dot = "Shock"
    source_bar.anomaly_dmg_ratio = 2.25
    source_bar.scaling_factor = 1.5
    source_bar.basic_max_duration = 420
    source_bar.ndarray_box = [
        (3, np.float64(40), np.array([[2.0, 4.0]], dtype=np.float64)),
        (3, np.float64(60), np.array([[6.0, 8.0]], dtype=np.float64)),
    ]
    enemy.anomaly_bars_dict[3] = source_bar
    enemy.dynamic.dynamic_dot_list = _RecordingDotRuntimeList(call_order)
    skill_node = _build_skill_node(element_type=3)
    chars = [
        SimpleNamespace(
            special_resources=lambda anomaly: call_order.append(("special_resources", anomaly))
        )
    ]
    new_dot = _FakeDot(index="Shock", call_order=call_order)
    spawn_calls: list[tuple[object, int, object, object]] = []

    def fake_spawn_anomaly_dot(element_type, timenow, *, bar, sim_instance):
        spawn_calls.append((element_type, timenow, bar, sim_instance))
        return new_dot

    monkeypatch.setattr(
        update_anomaly_module,
        "spawn_anomaly_dot",
        fake_spawn_anomaly_dot,
    )
    _record_dot_runtime_state_adapter(monkeypatch, helper_calls)
    recording_queue = _RecordingEventList(call_order)
    sim_instance.schedule_data.event_list = recording_queue

    update_anomaly(
        3,
        enemy,
        14,
        chars,
        sim_instance,
        skill_node,
        {"alpha": [], "enemy": []},
    )

    assert len(recording_queue) == 1
    published = recording_queue[0]
    active_bar = enemy.dynamic.active_anomaly_bar_dict[3]
    assert active_bar is not source_bar
    assert enemy.dynamic.anomaly_state_3 is True
    assert active_bar.active is True
    assert active_bar.settled is True
    assert source_bar.current_anomaly == np.float64(0)
    assert source_bar.current_effective_anomaly == np.float64(0)
    assert source_bar.ndarray_box == []
    np.testing.assert_array_equal(
        source_bar.current_ndarray,
        np.zeros((1, 1), dtype=np.float64),
    )

    assert published.element_type == 3
    assert published.activated_by is skill_node
    assert published.activate_by is skill_node
    assert published.is_disorder is False
    assert published.sim_instance is sim_instance
    assert published.current_effective_anomaly == np.float64(100)
    np.testing.assert_allclose(
        published.current_ndarray,
        np.array([[4.4, 6.4]], dtype=np.float64),
    )
    assert published.schedule_priority == 999
    assert not hasattr(published, "execute_tick")
    assert published.anomaly_dmg_ratio == pytest.approx(2.25)
    assert published.scaling_factor == pytest.approx(1.5)
    assert published.basic_max_duration == 420
    assert published.max_duration == 420
    assert published.last_active == 14
    assert published.duration_buff_list is None
    assert published.duration_buff_key_list is None
    assert published.accompany_dot == "Shock"
    assert spawn_calls == [(3, 14, published, sim_instance)]
    assert helper_calls == [
        ("from_enemy", enemy),
        ("replace_by_index", new_dot, 14),
    ]
    assert enemy.dynamic.dynamic_dot_list == [new_dot]
    assert call_order == [
        ("broadcast", LBS.ANOMALY),
        ("special_resources", published),
        ("dot_append", "Shock"),
        ("publish", published),
    ]


@pytest.mark.parametrize("element_type", [2, 5])
@pytest.mark.parametrize(
    ("initial_frozen", "should_publish"),
    [(False, False), (True, True)],
)
def test_update_anomaly_ice_frost_mode_zero_publishes_only_when_currently_frozen(
    element_type,
    initial_frozen,
    should_publish,
):
    call_order: list[tuple[str, object]] = []
    legacy_event_list = _FailFastEventList()
    sim_instance = _build_sim_instance(legacy_event_list, call_order)
    enemy = _build_enemy(sim_instance)
    enemy.dynamic.frozen = initial_frozen
    enemy.anomaly_bars_dict[element_type] = _build_anomaly_bar(
        sim_instance,
        element_type=element_type,
    )
    skill_node = _build_skill_node(element_type=element_type)
    chars = [
        SimpleNamespace(
            special_resources=lambda anomaly: call_order.append(("special_resources", anomaly))
        )
    ]
    recording_queue = _RecordingEventList(call_order)
    sim_instance.schedule_data.event_list = recording_queue

    update_anomaly(
        element_type,
        enemy,
        18,
        chars,
        sim_instance,
        skill_node,
        {"alpha": [], "enemy": []},
    )

    special_payloads = [payload for action, payload in call_order if action == "special_resources"]
    assert len(special_payloads) == 1
    new_anomaly = special_payloads[0]
    assert enemy.dynamic.frozen is True
    assert enemy.dynamic.active_anomaly_bar_dict[element_type].element_type == element_type
    if should_publish:
        assert recording_queue == [new_anomaly]
        assert call_order == [
            ("broadcast", LBS.ANOMALY),
            ("special_resources", new_anomaly),
            ("publish", new_anomaly),
        ]
    else:
        assert recording_queue == []
        assert call_order == [
            ("broadcast", LBS.ANOMALY),
            ("special_resources", new_anomaly),
        ]


def test_update_anomaly_runtime_layers_are_split_into_helpers():
    signature = inspect.signature(update_anomaly)
    assert "event_list" not in signature.parameters

    update_source = inspect.getsource(update_anomaly_module.update_anomaly)
    helper_names = {
        "_record_decibel_update",
        "_activate_anomaly_state",
        "_broadcast_active_anomaly",
        "_process_new_or_replaced_anomaly",
        "_process_disorder_anomaly",
        "_collect_disorder_dots_to_remove",
        "_publish_freeze_follow_up_for_removed_dot",
        "_remove_disorder_dot_from_runtime",
        "_record_disorder_dot_removal_process",
    }
    update_helper_names = {
        "_record_decibel_update",
        "_activate_anomaly_state",
        "_broadcast_active_anomaly",
        "_process_new_or_replaced_anomaly",
        "_process_disorder_anomaly",
    }
    for helper_name in update_helper_names:
        assert f"{helper_name}(" in update_source

    inline_forbidden_terms = {
        "decibel_manager.update",
        "listener_manager.broadcast_event",
        "publish_scheduled",
        "spawn_anomaly_dot",
        "event_list",
    }
    for term in inline_forbidden_terms:
        assert term not in update_source

    helper_sources = {
        helper_name: inspect.getsource(getattr(update_anomaly_module, helper_name))
        for helper_name in helper_names
    }
    assert "change_info_cause_active" in helper_sources["_activate_anomaly_state"]
    assert "buff_runtime_view=buff_runtime_view" in helper_sources["_activate_anomaly_state"]
    assert (
        "listener_broadcaster(event=active_bar, signal=LBS.ANOMALY)"
        in helper_sources["_broadcast_active_anomaly"]
    )
    assert "_publish_scheduled_event" in inspect.getsource(
        update_anomaly_module._publish_new_anomaly_if_required
    )
    assert "anomaly_effect_active" in helper_sources["_process_new_or_replaced_anomaly"]
    assert "anomaly_effect_active" in helper_sources["_process_disorder_anomaly"]
    assert "remove_dots_cause_disorder" in helper_sources["_process_disorder_anomaly"]
    assert (
        '_record_decibel_update(sim_instance, skill_node, "disorder")'
        in helper_sources["_process_disorder_anomaly"]
    )
    assert "dot_runtime_state.snapshot()" in helper_sources["_collect_disorder_dots_to_remove"]
    assert "_publish_scheduled_event" in helper_sources["_publish_freeze_follow_up_for_removed_dot"]
    assert "dot_runtime_state.remove_all" in helper_sources["_remove_disorder_dot_from_runtime"]
    assert "change_process_state" in helper_sources["_record_disorder_dot_removal_process"]


def test_remove_dots_cause_disorder_keeps_publish_and_runtime_removal_helpers_distinct():
    remove_source = inspect.getsource(update_anomaly_module.remove_dots_cause_disorder)
    publish_helper_source = inspect.getsource(
        update_anomaly_module._publish_freeze_follow_up_for_removed_dot
    )
    runtime_remove_helper_source = inspect.getsource(
        update_anomaly_module._remove_disorder_dot_from_runtime
    )
    collect_helper_source = inspect.getsource(
        update_anomaly_module._collect_disorder_dots_to_remove
    )

    for helper_name in {
        "_collect_disorder_dots_to_remove",
        "_publish_freeze_follow_up_for_removed_dot",
        "_mark_freeze_dot_removed_by_disorder",
        "_remove_disorder_dot_from_runtime",
        "_clear_freeze_runtime_flags",
        "_record_disorder_dot_removal_process",
    }:
        assert helper_name in remove_source

    inline_forbidden_terms = {
        "_publish_scheduled_event",
        "dot_runtime_state.remove_all",
        "listener_broadcaster",
        "broadcast_event",
        "buff_add_strategy",
    }
    for term in inline_forbidden_terms:
        assert term not in remove_source

    assert "_publish_scheduled_event" in publish_helper_source
    for term in {
        "dot_runtime_state",
        "remove_all",
        "listener_broadcaster",
        "broadcast_event",
        "buff_add_strategy",
    }:
        assert term not in publish_helper_source

    assert "dot.end(time_now)" in runtime_remove_helper_source
    assert "dot_runtime_state.remove_all([dot])" in runtime_remove_helper_source
    for term in {
        "_publish_scheduled_event",
        "listener_broadcaster",
        "broadcast_event",
        "buff_add_strategy",
    }:
        assert term not in runtime_remove_helper_source

    assert "dot_runtime_state.snapshot()" in collect_helper_source
    assert "_validate_disorder_dot_can_be_removed" in collect_helper_source
    for term in {
        "_publish_scheduled_event",
        "remove_all",
        "listener_broadcaster",
        "broadcast_event",
        "buff_add_strategy",
    }:
        assert term not in collect_helper_source


def test_anomaly_effect_active_replaces_same_index_dot_without_scheduled_publish(
    monkeypatch,
):
    call_order: list[tuple[str, object]] = []
    helper_calls: list[_HelperCallRecord] = []
    sim_instance = _build_sim_instance(_FailFastEventList())
    pending_queue = _FailFastPendingBuffQueue()
    sim_instance.load_data = SimpleNamespace(LOADING_BUFF_DICT={"enemy": pending_queue})
    sim_instance.listener_manager = _ForbiddenListenerManager()
    enemy = _build_enemy(sim_instance)
    old_dot = _FakeDot(index="Shock", call_order=call_order)
    unrelated_dot = _FakeDot(index="Ignite", call_order=call_order)
    new_dot = _FakeDot(index="Shock", call_order=call_order)
    enemy.dynamic.dynamic_dot_list = _RecordingDotRuntimeList(
        call_order,
        [unrelated_dot, old_dot],
    )
    new_anomaly = SimpleNamespace(marker="new-shock-anomaly")
    spawn_calls: list[tuple[object, int, object, object]] = []

    def fake_spawn_anomaly_dot(element_type, timenow, *, bar, sim_instance):
        spawn_calls.append((element_type, timenow, bar, sim_instance))
        return new_dot

    monkeypatch.setattr(
        update_anomaly_module,
        "spawn_anomaly_dot",
        fake_spawn_anomaly_dot,
    )
    monkeypatch.setattr(
        update_anomaly_module,
        "buff_add_strategy",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("dot-only anomaly effects should not call buff_add_strategy")
        ),
    )
    _record_dot_runtime_state_adapter(monkeypatch, helper_calls)

    anomaly_effect_active(
        SimpleNamespace(accompany_debuff=None, accompany_dot="Shock"),
        77,
        enemy,
        new_anomaly,
        3,
        sim_instance,
    )

    assert spawn_calls == [(3, 77, new_anomaly, sim_instance)]
    assert helper_calls == [
        ("from_enemy", enemy),
        ("replace_by_index", new_dot, 77),
    ]
    assert old_dot.ended_at == 77
    assert enemy.dynamic.dynamic_dot_list == [unrelated_dot, new_dot]
    assert enemy.dynamic.dynamic_dot_list.count(new_dot) == 1
    assert pending_queue == []
    assert call_order == [
        ("dot_end", "Shock"),
        ("dot_remove", "Shock"),
        ("dot_append", "Shock"),
    ]


def test_anomaly_effect_active_spawn_false_leaves_runtime_dot_list_unchanged(
    monkeypatch,
):
    call_order: list[tuple[str, object]] = []
    sim_instance = _build_sim_instance(_FailFastEventList())
    pending_queue = _FailFastPendingBuffQueue()
    sim_instance.load_data = SimpleNamespace(LOADING_BUFF_DICT={"enemy": pending_queue})
    sim_instance.listener_manager = _ForbiddenListenerManager()
    enemy = _build_enemy(sim_instance)
    existing_dot = _FakeDot(index="Shock", call_order=call_order)
    enemy.dynamic.dynamic_dot_list = _RecordingDotRuntimeList(
        call_order,
        [existing_dot],
    )

    monkeypatch.setattr(
        update_anomaly_module,
        "spawn_anomaly_dot",
        lambda *args, **kwargs: False,
    )
    monkeypatch.setattr(
        update_anomaly_module,
        "buff_add_strategy",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("dot-only anomaly effects should not call buff_add_strategy")
        ),
    )
    monkeypatch.setattr(
        update_anomaly_module.DotRuntimeStateAdapter,
        "from_enemy",
        classmethod(
            lambda *args, **kwargs: (_ for _ in ()).throw(
                AssertionError("spawn-false anomaly effects should not create dot helper")
            )
        ),
    )

    anomaly_effect_active(
        SimpleNamespace(accompany_debuff=None, accompany_dot="Shock"),
        88,
        enemy,
        SimpleNamespace(marker="new-shock-anomaly"),
        3,
        sim_instance,
    )

    assert existing_dot.ended_at is None
    assert enemy.dynamic.dynamic_dot_list == [existing_dot]
    assert pending_queue == []
    assert call_order == []


def test_anomaly_effect_active_debuff_branch_uses_existing_buff_add_path(
    monkeypatch,
):
    sim_instance = _build_sim_instance(_FailFastEventList())
    sim_instance.listener_manager = _ForbiddenListenerManager()
    enemy = _build_enemy(sim_instance)
    enemy.dynamic.dynamic_dot_list = _FailFastDotRuntimeList()
    buff_calls: list[tuple[str, object]] = []

    def fake_buff_add_strategy(buff_index, **kwargs):
        buff_calls.append((buff_index, kwargs["sim_instance"]))

    monkeypatch.setattr(
        update_anomaly_module,
        "buff_add_strategy",
        fake_buff_add_strategy,
    )
    monkeypatch.setattr(
        update_anomaly_module,
        "spawn_anomaly_dot",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("debuff-only anomaly effects should not spawn runtime dots")
        ),
    )
    monkeypatch.setattr(
        update_anomaly_module.DotRuntimeStateAdapter,
        "from_enemy",
        classmethod(
            lambda *args, **kwargs: (_ for _ in ()).throw(
                AssertionError("debuff-only anomaly effects should not create dot helper")
            )
        ),
    )

    anomaly_effect_active(
        SimpleNamespace(
            accompany_debuff=["Buff-异常-畏缩", "Buff-异常-霜寒"],
            accompany_dot=None,
        ),
        90,
        enemy,
        SimpleNamespace(marker="new-anomaly"),
        1,
        sim_instance,
    )

    assert buff_calls == [
        ("Buff-异常-畏缩", sim_instance),
        ("Buff-异常-霜寒", sim_instance),
    ]
    assert enemy.dynamic.dynamic_dot_list == []


def test_anomaly_effect_active_does_not_introduce_runtime_write_ports():
    from zsim.sim_progress.ScheduledEvent.buff_runtime import (
        BuffRuntimeReadPort,
        DefaultBuffRuntimeFacade,
    )
    from zsim.sim_progress.ScheduledEvent.runtime_command import (
        DefaultRuntimeCommandAdapter,
        RuntimeCommandPort,
    )

    anomaly_source = inspect.getsource(update_anomaly_module.anomaly_effect_active)
    remove_source = inspect.getsource(update_anomaly_module.remove_dots_cause_disorder)
    buff_add_source = inspect.getsource(buff_add_strategy_module)
    facade_source = inspect.getsource(DefaultBuffRuntimeFacade)
    runtime_update_source = inspect.getsource(DefaultRuntimeCommandAdapter.update_anomaly)

    anomaly_forbidden_terms = {
        "ScheduleDispatchPort",
        "create_schedule_dispatch_port",
        "publish_scheduled",
        "_publish_scheduled_event",
        "RuntimeCommandPort",
        "LegacyRuntimeCommandAdapter",
        "create_runtime_command_port",
        "BuffRuntimeReadPort",
        "LegacyBuffRuntimeFacade",
        "create_legacy_buff_runtime_facade",
        "listener_manager",
        "broadcast_event",
        "global_stats",
        "DYNAMIC_BUFF_DICT",
        "LOADING_BUFF_DICT",
        "dynamic_debuff_list",
    }
    for term in anomaly_forbidden_terms:
        assert term not in anomaly_source
    assert "buff_add_strategy" in anomaly_source
    assert "spawn_anomaly_dot" in anomaly_source
    assert "DotRuntimeStateAdapter.from_enemy" in anomaly_source
    assert "replace_by_index" in anomaly_source

    remove_forbidden_terms = {
        "buff_add_strategy",
        "RuntimeCommandPort",
        "LegacyRuntimeCommandAdapter",
        "create_runtime_command_port",
        "BuffRuntimeReadPort",
        "LegacyBuffRuntimeFacade",
        "create_legacy_buff_runtime_facade",
        "listener_manager",
        "broadcast_event",
        "global_stats",
        "DYNAMIC_BUFF_DICT",
        "LOADING_BUFF_DICT",
        "dynamic_debuff_list",
    }
    for term in remove_forbidden_terms:
        assert term not in remove_source
    assert "_publish_freeze_follow_up_for_removed_dot" in remove_source
    assert "_remove_disorder_dot_from_runtime" in remove_source
    assert "_record_disorder_dot_removal_process" in remove_source
    assert "DotRuntimeStateAdapter.from_enemy" in remove_source

    buff_add_forbidden_terms = {
        "ScheduleDispatchPort",
        "create_schedule_dispatch_port",
        "publish_scheduled",
        "RuntimeCommandPort",
        "create_runtime_command_port",
        "BuffRuntimeReadPort",
        "listener_manager",
        "broadcast_event",
        "create_legacy_buff_runtime_facade",
        "global_stats",
        "DYNAMIC_BUFF_DICT",
        "LOADING_BUFF_DICT",
        "dynamic_debuff_list",
        "exist_buff_dict",
    }
    for term in buff_add_forbidden_terms:
        assert term not in buff_add_source
    assert "buff_runtime_state.create_facade" in buff_add_source
    assert "create_forced_add_buff" in buff_add_source
    assert "find_registered_buff_source" in buff_add_source

    assert RuntimeCommandPort is not DefaultRuntimeCommandAdapter
    assert "publish_scheduled" not in inspect.getsource(RuntimeCommandPort)
    assert "broadcast_event" not in inspect.getsource(RuntimeCommandPort)
    assert "publish_scheduled" not in inspect.getsource(DefaultRuntimeCommandAdapter)
    assert "broadcast_event" not in inspect.getsource(DefaultRuntimeCommandAdapter)
    assert "publish_scheduled" not in facade_source
    assert "event_list" not in runtime_update_source
    assert "legacy_update_anomaly" not in runtime_update_source
    assert "runtime_context" in runtime_update_source
    assert "create_anomaly_runtime_context" in runtime_update_source

    write_method_names = {
        "enqueue_pending_buff",
        "clear_pending_buffs",
        "remove_active_buff",
        "append_active_buff",
        "sync_enemy_debuff_mirror",
    }
    assert write_method_names.isdisjoint(BuffRuntimeReadPort.__dict__)
    for method_name in write_method_names:
        assert hasattr(DefaultBuffRuntimeFacade, method_name)


def test_copied_output_constructors_keep_publish_dot_and_debuff_layers_external():
    source = inspect.getsource(copied_output_module)
    forbidden_terms = {
        "ScheduleDispatchPort",
        "create_schedule_dispatch_port",
        "publish_scheduled",
        "_publish_scheduled_event",
        "DotRuntimeStateAdapter",
        "spawn_anomaly_dot",
        "buff_add_strategy",
        "RuntimeCommandPort",
        "create_runtime_command_port",
        "settle_buffs",
        "report_dmg_result",
    }

    for term in forbidden_terms:
        assert term not in source
    assert "_copy_source_payload" in source
    assert "_install_copied_payload" in source
    assert "_apply_explicit_overrides" in source


@pytest.mark.parametrize("dot_index", ["Freez", "Freezdot"])
def test_remove_dots_cause_disorder_publishes_freeze_follow_up_via_dispatch_port(
    dot_index,
    monkeypatch,
):
    call_order: list[tuple[str, object]] = []
    helper_calls: list[_HelperCallRecord] = []
    recording_queue = _RecordingEventList(call_order)
    sim_instance = _build_sim_instance(recording_queue)
    enemy = _build_enemy(sim_instance)
    anomaly_event = SimpleNamespace(marker="freeze-follow-up")
    freeze_dot = _FakeDot(
        index=dot_index,
        anomaly_data=anomaly_event,
        call_order=call_order,
    )
    freeze_dot.dy = _RecordingDotDynamicState(call_order, effect_times=1)
    enemy.dynamic.dynamic_dot_list = _RecordingDotRuntimeList(call_order, [freeze_dot])
    enemy.dynamic.frozen = True
    enemy.dynamic.frostbite = True
    sim_instance.schedule_data.change_process_state = lambda: call_order.append(
        ("change_process_state", None)
    )
    disorder = SimpleNamespace(accompany_dot="Shock")
    _record_dot_runtime_state_adapter(monkeypatch, helper_calls)

    remove_dots_cause_disorder(
        disorder,
        enemy,
        create_schedule_dispatch_port(sim_instance=sim_instance),
        10,
    )

    assert recording_queue == [anomaly_event]
    assert helper_calls == [
        ("from_enemy", enemy),
        ("remove_all", (freeze_dot,)),
    ]
    assert call_order == [
        ("publish", anomaly_event),
        ("dy_ready", False),
        ("dy_last_effect_ticks", 10),
        ("dy_effect_times", 2),
        ("dot_end", dot_index),
        ("dot_remove", dot_index),
        ("change_process_state", None),
    ]
    assert freeze_dot.dy.ready is False
    assert freeze_dot.dy.last_effect_ticks == 10
    assert freeze_dot.dy.effect_times == 2
    assert freeze_dot.ended_at == 10
    assert enemy.dynamic.dynamic_dot_list == []
    assert enemy.dynamic.frozen is False
    assert enemy.dynamic.frostbite is False


def test_remove_dots_cause_disorder_removes_matching_non_freeze_dot_without_publish(
    monkeypatch,
):
    call_order: list[tuple[str, object]] = []
    helper_calls: list[_HelperCallRecord] = []
    sim_instance = _build_sim_instance(_FailFastEventList())
    sim_instance.schedule_data.change_process_state = lambda: call_order.append(
        ("change_process_state", None)
    )
    enemy = _build_enemy(sim_instance)
    unrelated_dot = _FakeDot(index="Ignite", call_order=call_order)
    removed_dot = _FakeDot(index="Shock", call_order=call_order)
    enemy.dynamic.dynamic_dot_list = _RecordingDotRuntimeList(
        call_order,
        [unrelated_dot, removed_dot],
    )
    disorder = SimpleNamespace(accompany_dot="Shock")
    _record_dot_runtime_state_adapter(monkeypatch, helper_calls)

    remove_dots_cause_disorder(
        disorder,
        enemy,
        create_schedule_dispatch_port(sim_instance=sim_instance),
        23,
    )

    assert removed_dot.ended_at == 23
    assert helper_calls == [
        ("from_enemy", enemy),
        ("remove_all", (removed_dot,)),
    ]
    assert unrelated_dot.ended_at is None
    assert enemy.dynamic.dynamic_dot_list == [unrelated_dot]
    assert call_order == [
        ("dot_end", "Shock"),
        ("dot_remove", "Shock"),
        ("change_process_state", None),
    ]


def test_remove_dots_cause_disorder_rejects_invalid_runtime_dot_entry():
    sim_instance = _build_sim_instance(_FailFastEventList())
    sim_instance.schedule_data.change_process_state = lambda: (_ for _ in ()).throw(
        AssertionError("invalid dot entries should not update process state")
    )
    enemy = _build_enemy(sim_instance)
    enemy.dynamic.dynamic_dot_list = [object()]
    disorder = SimpleNamespace(accompany_dot="Shock")

    with pytest.raises(TypeError, match="不是DOT类"):
        remove_dots_cause_disorder(
            disorder,
            enemy,
            create_schedule_dispatch_port(sim_instance=sim_instance),
            23,
        )
