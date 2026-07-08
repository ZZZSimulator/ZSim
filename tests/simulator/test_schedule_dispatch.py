import inspect
from types import SimpleNamespace
from typing import Any, cast

import pytest

import zsim.sim_progress.data_struct.schedule_dispatch as schedule_dispatch_module
import zsim.sim_progress.Load.LoadDamageEvent as load_damage_event_module
from zsim.sim_progress.data_struct.planned_queue import (
    ensure_planned_event_queue,
)
from zsim.sim_progress.data_struct.schedule_dispatch import (
    ScheduledEventEmitterProvider,
    ScheduleDispatchPort,
    create_schedule_dispatch_port,
)
from zsim.sim_progress.Dot.BaseDot import Dot
from zsim.sim_progress.Load.LoadDamageEvent import (
    DamageEventJudge,
    ProcessTimeUpdateDots,
)
from zsim.sim_progress.Load.loading_mission import LoadingMission
from zsim.simulator.dataclasses import ScheduleData


class _RecordingSchedulePublisher:
    def __init__(self) -> None:
        self.events: list[object] = []

    def publish_scheduled(self, event: object) -> None:
        self.events.append(event)


class _RecordingProviderDispatchPort(ScheduleDispatchPort):
    def __init__(self) -> None:
        self.events: list[object] = []

    def publish_scheduled(self, event: object) -> None:
        self.events.append(event)


class _ReadyDot(Dot):
    def __init__(
        self,
        *,
        anomaly_data: object | None,
        skill_node_data: object | None,
    ) -> None:
        super().__init__(bar=None, sim_instance=None)
        self.ft.effect_rules = 1
        self.ft.update_cd = 0
        self.ft.max_effect_times = 30
        self.ft.complex_exit_logic = False
        self.anomaly_data = anomaly_data
        self.skill_node_data = skill_node_data
        self.dy.ready = True
        self.dy.effect_times = 0


class _PlannedQueueOwnerProbe:
    def __init__(self, events: list[object] | None = None) -> None:
        self.events = [] if events is None else events
        self.enqueue_calls: list[object] = []

    def enqueue(self, event: object) -> None:
        self.enqueue_calls.append(event)
        self.events.append(event)

    def snapshot(self) -> list[object]:
        return list(self.events)


def _owner_schedule_data(
    queue: _PlannedQueueOwnerProbe | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        planned_event_queue=_PlannedQueueOwnerProbe() if queue is None else queue
    )


def _make_loading_mission(tag: str, hit_tick: int) -> LoadingMission:
    skill = SimpleNamespace(ticks=20, tick_list=[], heavy_attack=False)
    mission_node = SimpleNamespace(
        preload_tick=0,
        hit_times=2,
        skill_tag=tag,
        end_tick=99,
        char_name="Alice",
        skill=skill,
    )
    mission = LoadingMission(cast(Any, mission_node))
    mission.mission_active_state = True
    mission.mission_dict = {hit_tick: "hit"}
    return mission


def _make_schedule_data() -> ScheduleData:
    enemy = SimpleNamespace(reset_myself=lambda: None)
    return ScheduleData(enemy=cast(Any, enemy), char_obj_list=[])


def test_create_schedule_dispatch_port_uses_schedule_data_without_exposing_event_list():
    queue = _PlannedQueueOwnerProbe()
    schedule_data = _owner_schedule_data(queue)

    dispatch_port = create_schedule_dispatch_port(schedule_data=schedule_data)

    assert isinstance(dispatch_port, ScheduleDispatchPort)
    assert not hasattr(dispatch_port, "event_list")

    dispatch_port.publish_scheduled("scheduled-event")

    assert queue.snapshot() == ["scheduled-event"]


def test_ensure_planned_event_queue_requires_existing_owner():
    schedule_data = SimpleNamespace()

    with pytest.raises(
        AttributeError,
        match="planned_event_queue",
    ):
        ensure_planned_event_queue(schedule_data)

    queue = _PlannedQueueOwnerProbe()
    schedule_data.planned_event_queue = queue

    assert ensure_planned_event_queue(schedule_data) is queue


def test_create_schedule_dispatch_port_default_paths_use_owner_not_legacy_adapter():
    schedule_data = _make_schedule_data()
    sim_instance = SimpleNamespace(schedule_data=schedule_data)

    for dispatch_port in (
        create_schedule_dispatch_port(schedule_data=schedule_data),
        create_schedule_dispatch_port(sim_instance=cast(Any, sim_instance)),
    ):
        assert type(dispatch_port).__name__ == "_QueueBackedScheduleDispatchPort"
        queue_owner = dispatch_port.__dict__["_queue_owner"]
        assert type(queue_owner).__name__ == "_ScheduleDataQueueOwner"
        assert queue_owner.__dict__["_schedule_data"] is schedule_data


def test_create_schedule_dispatch_port_uses_planned_event_queue_owner_for_schedule_data(
    monkeypatch: pytest.MonkeyPatch,
):
    schedule_data = _make_schedule_data()
    enqueued_events: list[object] = []
    original_enqueue = schedule_data.planned_event_queue.enqueue

    def recording_enqueue(event: object) -> None:
        enqueued_events.append(event)
        original_enqueue(event)

    monkeypatch.setattr(schedule_data.planned_event_queue, "enqueue", recording_enqueue)

    dispatch_port = create_schedule_dispatch_port(schedule_data=schedule_data)
    dispatch_port.publish_scheduled("owner-event")

    assert enqueued_events == ["owner-event"]
    assert schedule_data.planned_event_queue.snapshot() == ["owner-event"]


def test_schedule_data_planned_event_queue_preserves_order_and_owner_operations():
    schedule_data = _make_schedule_data()
    queue = schedule_data.planned_event_queue

    queue.enqueue("first")
    queue.enqueue_batch(["second", "third"])

    assert "_planned_events" in schedule_data.__dict__
    assert "event_list" not in schedule_data.__dict__
    assert queue.snapshot() == ["first", "second", "third"]
    assert list(queue) == ["first", "second", "third"]
    assert queue.has_events()

    queue.remove("second")

    assert queue.snapshot() == ["first", "third"]


def test_schedule_data_owner_operations_do_not_use_event_list_property(
    monkeypatch: pytest.MonkeyPatch,
):
    schedule_data = _make_schedule_data()
    queue = schedule_data.planned_event_queue

    def fail_getter(self: ScheduleData) -> list[object]:
        raise AssertionError("owner operations must not read event_list compatibility")

    def fail_setter(self: ScheduleData, events: list[object]) -> None:
        raise AssertionError("owner operations must not write event_list compatibility")

    monkeypatch.setattr(
        ScheduleData,
        "event_list",
        property(fail_getter, fail_setter),
        raising=False,
    )

    queue.enqueue("first")
    queue.enqueue_batch(["second", "third"])
    assert queue.snapshot() == ["first", "second", "third"]

    queue.remove("second")
    assert queue.snapshot() == ["first", "third"]

    queue.replace(["replacement"])
    assert queue.snapshot() == ["replacement"]

    queue.reset()
    assert queue.snapshot() == []


def test_schedule_data_does_not_expose_event_list_public_attribute():
    schedule_data = _make_schedule_data()
    queue = schedule_data.planned_event_queue

    assert "event_list" not in schedule_data.__dict__
    assert "event_list" not in vars(ScheduleData)
    assert not hasattr(schedule_data, "event_list")

    queue.replace(["replacement"])
    queue.enqueue("queued")

    assert schedule_data.__dict__["_planned_events"] == ["replacement", "queued"]
    assert queue.snapshot() == ["replacement", "queued"]


def test_schedule_data_constructor_rejects_event_list_seeding():
    initial_events = ["seed"]

    with pytest.raises(TypeError, match="event_list"):
        ScheduleData(
            enemy=cast(Any, SimpleNamespace(reset_myself=lambda: None)),
            char_obj_list=[],
            event_list=initial_events,
        )


def test_schedule_data_owner_replace_seeds_planned_events_after_construction():
    initial_events = ["seed"]
    schedule_data = _make_schedule_data()
    schedule_data.planned_event_queue.replace(initial_events)

    assert schedule_data.planned_event_queue.snapshot() == ["seed"]

    schedule_data.planned_event_queue.replace(["replaced"])

    assert schedule_data.planned_event_queue.snapshot() == ["replaced"]
    assert initial_events == ["seed"]


def test_schedule_data_planned_event_queue_replace_and_reset_preserve_owner_contract():
    schedule_data = _make_schedule_data()
    queue = schedule_data.planned_event_queue
    queue.enqueue_batch(["other", "buff"])
    original_snapshot = queue.snapshot()

    queue.replace(["buff", "other"])

    assert original_snapshot == ["other", "buff"]
    assert queue.snapshot() == ["buff", "other"]

    schedule_data.reset_myself()

    assert queue.snapshot() == []
    assert not queue.has_events()


def test_create_schedule_dispatch_port_for_schedule_data_uses_current_owner_storage():
    schedule_data = _make_schedule_data()
    queue = schedule_data.planned_event_queue
    dispatch_port = create_schedule_dispatch_port(schedule_data=schedule_data)

    queue.replace(["stale"])
    queue.replace([])
    dispatch_port.publish_scheduled("current")

    assert queue.snapshot() == ["current"]


def test_create_schedule_dispatch_port_supports_sim_instance():
    queue = _PlannedQueueOwnerProbe()
    schedule_data = _owner_schedule_data(queue)
    sim_instance = SimpleNamespace(schedule_data=schedule_data)

    dispatch_port = create_schedule_dispatch_port(sim_instance=sim_instance)
    dispatch_port.publish_scheduled_batch(["alpha", "beta"])

    assert queue.snapshot() == ["alpha", "beta"]


def test_create_schedule_dispatch_port_follows_rebound_planned_event_queue_owner():
    original_queue = _PlannedQueueOwnerProbe()
    rebound_queue = _PlannedQueueOwnerProbe()
    schedule_data = _owner_schedule_data(original_queue)
    dispatch_port = create_schedule_dispatch_port(schedule_data=schedule_data)
    dispatch_port.publish_scheduled("old-event")

    schedule_data.planned_event_queue = rebound_queue
    dispatch_port.publish_scheduled("new-event")

    assert original_queue.snapshot() == ["old-event"]
    assert rebound_queue.snapshot() == ["new-event"]


def test_scheduled_event_provider_from_sim_instance_creates_fresh_dispatch_port_each_emitter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sim_instance = SimpleNamespace(schedule_data=_owner_schedule_data())
    created_ports: list[_RecordingProviderDispatchPort] = []

    def create_recording_dispatch_port(
        *,
        sim_instance: object | None = None,
        schedule_data: object | None = None,
    ) -> _RecordingProviderDispatchPort:
        assert sim_instance is sim_instance_arg
        assert schedule_data is None
        port = _RecordingProviderDispatchPort()
        created_ports.append(port)
        return port

    sim_instance_arg = sim_instance
    monkeypatch.setattr(
        schedule_dispatch_module,
        "create_schedule_dispatch_port",
        create_recording_dispatch_port,
    )

    provider = ScheduledEventEmitterProvider.from_sim_instance(cast(Any, sim_instance))
    first_emitter = provider.create_emitter()
    second_emitter = provider.create_emitter()

    first_emitter.emit_scheduled("first")
    second_emitter.emit_scheduled("second")

    assert len(created_ports) == 2
    assert created_ports[0].events == ["first"]
    assert created_ports[1].events == ["second"]


def test_scheduled_event_provider_from_sim_instance_getter_uses_current_simulator_each_emitter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first_sim = SimpleNamespace(schedule_data=_owner_schedule_data())
    second_sim = SimpleNamespace(schedule_data=_owner_schedule_data())
    current = {"sim_instance": first_sim}
    requested_sim_instances: list[object | None] = []
    created_ports: list[_RecordingProviderDispatchPort] = []

    def create_recording_dispatch_port(
        *,
        sim_instance: object | None = None,
        schedule_data: object | None = None,
    ) -> _RecordingProviderDispatchPort:
        assert schedule_data is None
        requested_sim_instances.append(sim_instance)
        port = _RecordingProviderDispatchPort()
        created_ports.append(port)
        return port

    monkeypatch.setattr(
        schedule_dispatch_module,
        "create_schedule_dispatch_port",
        create_recording_dispatch_port,
    )

    provider = ScheduledEventEmitterProvider.from_sim_instance_getter(
        lambda: cast(Any, current["sim_instance"])
    )
    first_emitter = provider.create_emitter()
    current["sim_instance"] = second_sim
    second_emitter = provider.create_emitter()

    first_emitter.emit_scheduled("first")
    second_emitter.emit_scheduled("second")

    assert requested_sim_instances == [first_sim, second_sim]
    assert len(created_ports) == 2
    assert created_ports[0].events == ["first"]
    assert created_ports[1].events == ["second"]


def test_scheduled_event_provider_from_schedule_data_creates_fresh_dispatch_port_each_emitter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    schedule_data = _owner_schedule_data()
    created_ports: list[_RecordingProviderDispatchPort] = []

    def create_recording_dispatch_port(
        *,
        sim_instance: object | None = None,
        schedule_data: object | None = None,
    ) -> _RecordingProviderDispatchPort:
        assert sim_instance is None
        assert schedule_data is schedule_data_arg
        port = _RecordingProviderDispatchPort()
        created_ports.append(port)
        return port

    schedule_data_arg = schedule_data
    monkeypatch.setattr(
        schedule_dispatch_module,
        "create_schedule_dispatch_port",
        create_recording_dispatch_port,
    )

    provider = ScheduledEventEmitterProvider.from_schedule_data(cast(Any, schedule_data))
    first_emitter = provider.create_emitter()
    second_emitter = provider.create_emitter()

    first_emitter.emit_scheduled("first")
    second_emitter.emit_scheduled("second")

    assert len(created_ports) == 2
    assert created_ports[0].events == ["first"]
    assert created_ports[1].events == ["second"]


@pytest.mark.parametrize(
    "provider_factory",
    [
        lambda schedule_data: ScheduledEventEmitterProvider.from_sim_instance(
            cast(Any, SimpleNamespace(schedule_data=schedule_data))
        ),
        lambda schedule_data: ScheduledEventEmitterProvider.from_sim_instance_getter(
            lambda: cast(Any, SimpleNamespace(schedule_data=schedule_data))
        ),
        lambda schedule_data: ScheduledEventEmitterProvider.from_schedule_data(
            cast(Any, schedule_data)
        ),
    ],
)
def test_scheduled_event_provider_emit_follows_rebound_planned_event_queue_owner(
    provider_factory: Any,
) -> None:
    original_queue = _PlannedQueueOwnerProbe()
    rebound_queue = _PlannedQueueOwnerProbe()
    schedule_data = _owner_schedule_data(original_queue)
    provider = provider_factory(schedule_data)
    emitter = provider.create_emitter()

    schedule_data.planned_event_queue = rebound_queue
    emitter.emit_scheduled("rebound-event")

    assert original_queue.snapshot() == []
    assert rebound_queue.snapshot() == ["rebound-event"]


def test_scheduled_event_provider_retains_callable_factory_only() -> None:
    schedule_data = _owner_schedule_data()
    provider = ScheduledEventEmitterProvider.from_schedule_data(cast(Any, schedule_data))
    before_create = dict(provider.__dict__)

    provider.create_emitter()

    assert set(provider.__dict__) == {"_dispatch_port_factory"}
    assert provider.__dict__ == before_create
    assert callable(provider.__dict__["_dispatch_port_factory"])


def test_legacy_event_list_adapter_is_not_public_schedule_dispatch_api():
    import zsim.sim_progress.data_struct as data_struct_module

    expected_public_api = {"publish_scheduled", "publish_scheduled_batch"}
    raw_queue_api = {
        "append",
        "clear",
        "event_list",
        "event_queue",
        "extend",
        "insert",
        "pop",
        "queue",
        "remove",
    }

    assert {
        name
        for name in dir(ScheduleDispatchPort)
        if not name.startswith("_") and callable(getattr(ScheduleDispatchPort, name))
    } == expected_public_api
    assert not hasattr(schedule_dispatch_module, "LegacyEventListScheduleDispatchAdapter")
    assert "LegacyEventListScheduleDispatchAdapter" not in schedule_dispatch_module.__all__
    assert not hasattr(data_struct_module, "LegacyEventListScheduleDispatchAdapter")
    assert "LegacyEventListScheduleDispatchAdapter" not in data_struct_module.__all__
    for raw_name in raw_queue_api:
        assert not hasattr(ScheduleDispatchPort, raw_name)


def test_schedule_dispatch_module_remains_queue_only_boundary():
    source = inspect.getsource(schedule_dispatch_module)

    assert "self._queue_owner.enqueue(event)" in source
    assert "self._event_queue.append(event)" not in source
    assert "_MutableScheduleQueueOwner" not in source
    assert "ensure_planned_event_queue(self._schedule_data).enqueue(event)" in source
    assert "_fallback_planned_queue" not in source
    assert "def _replace_events" not in source
    for forbidden_token in (
        "listener_manager",
        "broadcast_event",
        "RuntimeCommandPort",
        "runtime_command",
        "create_runtime_command_port",
        "run_update_anomaly",
        "dot_runtime",
    ):
        assert forbidden_token not in source


def test_damage_event_judge_publishes_loading_missions_in_current_order():
    first_mission = _make_loading_mission("1001_First", hit_tick=5)
    second_mission = _make_loading_mission("1001_Second", hit_tick=5)
    publisher = _RecordingSchedulePublisher()
    enemy = SimpleNamespace(dynamic=SimpleNamespace(dynamic_dot_list=[]))

    DamageEventJudge(
        5,
        {"first": first_mission, "second": second_mission},
        cast(Any, enemy),
        publisher,
        [],
    )

    assert publisher.events == [first_mission, second_mission]
    assert first_mission.hitted_count == 1
    assert second_mission.hitted_count == 1


def test_damage_event_judge_dispatch_port_path_does_not_construct_legacy_adapter():
    mission = _make_loading_mission("1001_First", hit_tick=5)
    enemy = SimpleNamespace(dynamic=SimpleNamespace(dynamic_dot_list=[]))
    schedule_data = _make_schedule_data()
    dispatch_port = create_schedule_dispatch_port(schedule_data=schedule_data)
    source = inspect.getsource(load_damage_event_module)

    assert "LegacyEventListScheduleDispatchAdapter" not in source

    DamageEventJudge(
        5,
        {"first": mission},
        cast(Any, enemy),
        dispatch_port,
        [],
    )

    assert schedule_data.planned_event_queue.snapshot() == [mission]
    assert mission.hitted_count == 1


def test_damage_event_judge_rejects_raw_event_list_schedule_publisher():
    mission = _make_loading_mission("1001_First", hit_tick=5)
    enemy = SimpleNamespace(dynamic=SimpleNamespace(dynamic_dot_list=[]))
    raw_event_list: list[object] = []

    with pytest.raises(TypeError, match="原始 event_list 交接已经移除"):
        DamageEventJudge(
            5,
            {"first": mission},
            cast(Any, enemy),
            raw_event_list,
            [],
        )

    assert raw_event_list == []
    assert mission.hitted_count == 0


def test_damage_event_judge_rejects_legacy_event_list_keyword():
    mission = _make_loading_mission("1001_First", hit_tick=5)
    enemy = SimpleNamespace(dynamic=SimpleNamespace(dynamic_dot_list=[]))
    raw_event_list: list[object] = []

    with pytest.raises(TypeError, match="event_list= 形式的计划队列交接已经移除"):
        DamageEventJudge(
            5,
            {"first": mission},
            cast(Any, enemy),
            char_obj_list=[],
            event_list=raw_event_list,
        )

    assert raw_event_list == []
    assert mission.hitted_count == 0


def test_damage_event_judge_dispatch_port_follows_rebound_queue_order():
    first_mission = _make_loading_mission("1001_First", hit_tick=5)
    second_mission = _make_loading_mission("1001_Second", hit_tick=5)
    anomaly_payload = object()
    hidden_skill_payload = object()
    skill_payload = object()
    anomaly_dot = _ReadyDot(
        anomaly_data=anomaly_payload,
        skill_node_data=hidden_skill_payload,
    )
    skill_dot = _ReadyDot(anomaly_data=None, skill_node_data=skill_payload)
    enemy = SimpleNamespace(dynamic=SimpleNamespace(dynamic_dot_list=[anomaly_dot, skill_dot]))
    original_queue = _PlannedQueueOwnerProbe()
    rebound_queue = _PlannedQueueOwnerProbe()
    schedule_data = _owner_schedule_data(original_queue)
    dispatch_port = create_schedule_dispatch_port(schedule_data=schedule_data)

    schedule_data.planned_event_queue = rebound_queue
    DamageEventJudge(
        5,
        {"first": first_mission, "second": second_mission},
        cast(Any, enemy),
        dispatch_port,
        [],
    )

    assert original_queue.snapshot() == []
    assert rebound_queue.snapshot() == [
        first_mission,
        second_mission,
        anomaly_payload,
        skill_payload,
    ]
    assert first_mission.hitted_count == 1
    assert second_mission.hitted_count == 1
    assert anomaly_dot.dy.effect_times == 1
    assert skill_dot.dy.effect_times == 1


def test_process_time_update_dots_publishes_anomaly_then_skill_node_payloads():
    anomaly_payload = object()
    hidden_skill_payload = object()
    skill_payload = object()
    anomaly_dot = _ReadyDot(
        anomaly_data=anomaly_payload,
        skill_node_data=hidden_skill_payload,
    )
    skill_dot = _ReadyDot(anomaly_data=None, skill_node_data=skill_payload)
    publisher = _RecordingSchedulePublisher()

    ProcessTimeUpdateDots(12, [anomaly_dot, skill_dot], publisher)

    assert publisher.events == [anomaly_payload, skill_payload]
    assert anomaly_dot.dy.effect_times == 1
    assert skill_dot.dy.effect_times == 1


def test_process_time_update_dots_rejects_raw_event_list_schedule_publisher():
    payload = object()
    dot = _ReadyDot(anomaly_data=None, skill_node_data=payload)
    raw_event_list: list[object] = []

    with pytest.raises(TypeError, match="原始 event_list 交接已经移除"):
        ProcessTimeUpdateDots(12, [dot], raw_event_list)

    assert raw_event_list == []


def test_create_schedule_dispatch_port_requires_context():
    with pytest.raises(ValueError, match="sim_instance"):
        create_schedule_dispatch_port()
