import importlib
from types import SimpleNamespace
from typing import cast

import pytest

from zsim.sim_progress.Buff import JudgeTools
from zsim.sim_progress.data_struct.schedule_dispatch import (
    ScheduledEventEmitterProvider,
    ScheduleDispatchPort,
)
from zsim.sim_progress.data_struct.SchedulePreload import (
    SchedulePreload,
    schedule_preload_event_factory,
)
from zsim.sim_progress.Preload.PreloadEngine.ConfirmEngine import ConfirmEngine


class _FailFastEventList(list):
    def append(self, item):
        raise AssertionError("schedule_preload_event_factory should use the injected emitter")


class _RecordingDispatchPort:
    def __init__(self) -> None:
        self.events: list[object] = []

    def publish_scheduled(self, event: object) -> None:
        self.events.append(event)


def test_schedule_preload_event_factory_preserves_queue_order_without_raw_event_list_access(
    monkeypatch: pytest.MonkeyPatch,
):
    sim_instance = SimpleNamespace(
        tick=10,
        schedule_data=SimpleNamespace(event_list=_FailFastEventList()),
    )
    preload_data = object()
    dispatch_port = _RecordingDispatchPort()

    def fail_find_event_list(*args, **kwargs):
        raise AssertionError("schedule_preload_event_factory should publish via dispatch port")

    monkeypatch.setattr(JudgeTools, "find_event_list", fail_find_event_list, raising=False)

    schedule_preload_event_factory(
        preload_tick_list=[11, 13],
        skill_tag_list=["alpha", "beta"],
        preload_data=preload_data,
        sim_instance=sim_instance,
        apl_priority_list=[2, 1],
        active_generation_list=[False, True],
        scheduled_event_emitter_provider=ScheduledEventEmitterProvider(
            lambda: cast(ScheduleDispatchPort, dispatch_port)
        ),
    )

    event_list = dispatch_port.events

    assert [event.skill_tag for event in event_list] == ["alpha", "beta"]
    assert [event.execute_tick for event in event_list] == [11, 13]
    assert [event.apl_priority for event in event_list] == [2, 1]
    assert [event.active_generation for event in event_list] == [False, True]
    assert all(isinstance(event, SchedulePreload) for event in event_list)
    assert all(event.preload_data is preload_data for event in event_list)
    assert all(event.sim_instance is sim_instance for event in event_list)
    assert sim_instance.schedule_data.event_list == []


def test_schedule_preload_execute_queues_legacy_confirm_tuple() -> None:
    preload_data = SimpleNamespace(preload_action_list_before_confirm=[])
    preload_data.external_add_skill = (
        lambda external_tuple: preload_data.preload_action_list_before_confirm.append(
            external_tuple
        )
    )
    event = SchedulePreload(
        123,
        "alpha",
        preload_data=preload_data,
        apl_priority=7,
        active_generation=True,
    )

    event.execute_myself()

    assert preload_data.preload_action_list_before_confirm == [("alpha", True, 7)]


def test_confirm_engine_uses_current_confirm_tick_for_external_tuple(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict[str, object]] = []
    confirm_engine_module = importlib.import_module(
        "zsim.sim_progress.Preload.PreloadEngine.ConfirmEngine"
    )

    def fake_spawn_node(
        skill_tag,
        tick,
        skills,
        *,
        active_generation=False,
        apl_priority=0,
        apl_unit=None,
    ):
        calls.append(
            {
                "skill_tag": skill_tag,
                "tick": tick,
                "active_generation": active_generation,
                "apl_priority": apl_priority,
                "apl_unit": apl_unit,
            }
        )
        return SimpleNamespace(skill_tag=skill_tag)

    monkeypatch.setattr(confirm_engine_module, "spawn_node", fake_spawn_node)
    engine = ConfirmEngine(SimpleNamespace(skills=[]))

    node = engine.spawn_node_from_tag(350, ("alpha", True, 7, 123))

    assert node.skill_tag == "alpha"
    assert calls == [
        {
            "skill_tag": "alpha",
            "tick": 350,
            "active_generation": True,
            "apl_priority": 7,
            "apl_unit": None,
        }
    ]


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        (
            {"preload_tick_list": [11, 12], "skill_tag_list": ["alpha"]},
            "preload_tick_list和skill_tag_list的长度不一致",
        ),
        (
            {"apl_priority_list": [1, 2]},
            "apl_priority_list和skill_tag_list的长度不一致",
        ),
        (
            {"active_generation_list": [True, False]},
            "active_generation_list和skill_tag_list的长度不一致",
        ),
    ],
)
def test_schedule_preload_event_factory_keeps_length_validation(
    kwargs: dict[str, list[int] | list[str] | list[bool]],
    message: str,
):
    sim_instance = SimpleNamespace(
        tick=10,
        schedule_data=SimpleNamespace(event_list=[]),
    )
    base_kwargs = {
        "preload_tick_list": [11],
        "skill_tag_list": ["alpha"],
        "preload_data": object(),
        "sim_instance": sim_instance,
        "apl_priority_list": [0],
        "active_generation_list": [False],
    }
    base_kwargs.update(kwargs)

    with pytest.raises(ValueError, match=message):
        schedule_preload_event_factory(**base_kwargs)


def test_schedule_preload_event_factory_rejects_past_ticks():
    sim_instance = SimpleNamespace(
        tick=10,
        schedule_data=SimpleNamespace(event_list=[]),
    )

    with pytest.raises(ValueError, match="不能添加过去的Preload计划事件"):
        schedule_preload_event_factory(
            preload_tick_list=[9],
            skill_tag_list=["alpha"],
            preload_data=object(),
            sim_instance=sim_instance,
        )
