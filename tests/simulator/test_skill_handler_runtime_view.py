from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Mapping, Sequence, cast

import pytest

from zsim.sim_progress.ScheduledEvent.buff_runtime import BuffRuntimeReadPort
from zsim.sim_progress.ScheduledEvent.event_handlers.context import EventContext
from zsim.sim_progress.ScheduledEvent.event_handlers.handlers import skill as skill_module
from zsim.sim_progress.ScheduledEvent.event_handlers.handlers.skill import SkillEventHandler


class _RuntimeViewProbe(BuffRuntimeReadPort):
    def __init__(self) -> None:
        self.active_buff_view = {"alpha": (object(),)}
        self.active_view_calls = 0

    def get_active_buffs(self, beneficiary: str) -> Sequence[Any]:
        return self.active_buff_view.get(beneficiary, ())

    def get_active_buff_view(self) -> Mapping[str, Sequence[Any]]:
        self.active_view_calls += 1
        return self.active_buff_view

    def get_exist_buff_snapshot(self, beneficiary: str) -> Mapping[str, Any]:
        return {}

    def get_exist_buff_snapshot_view(self) -> Mapping[str, Mapping[str, Any]]:
        return {}


class _RuntimeCommandProbe:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, object]]] = []

    def update_anomaly(self, **kwargs: object) -> None:
        self.calls.append(("update_anomaly", kwargs))

    def settle_buffs(self, **kwargs: object) -> None:
        self.calls.append(("settle_buffs", kwargs))


def _build_skill_node() -> SimpleNamespace:
    skill = SimpleNamespace(
        char_name="alpha",
        anomaly_update_rule=-1,
        follow_by=False,
        heavy_attack=False,
    )
    return SimpleNamespace(
        preload_tick=10,
        skill=skill,
        skill_tag="1001_TEST",
        char_name="alpha",
        active_generation=False,
        hit_times=1,
        element_type=1,
        UUID="skill-node",
        loading_mission=None,
        mission_node=SimpleNamespace(active_generation=False),
    )


def test_skill_handler_reads_runtime_view_and_routes_writes_through_runtime_command(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime_view = _RuntimeViewProbe()
    runtime_command_port = _RuntimeCommandProbe()
    character = SimpleNamespace(NAME="alpha")
    enemy = SimpleNamespace(
        dynamic=SimpleNamespace(dynamic_dot_list=[], get_status=lambda: {}),
        hit_received=lambda *args, **kwargs: None,
    )
    context = EventContext(
        data=SimpleNamespace(char_obj_list=[character]),
        tick=10,
        enemy=enemy,
        buff_runtime_view=runtime_view,
        runtime_command_port=cast(Any, runtime_command_port),
        action_stack=SimpleNamespace(),
        sim_instance=cast(
            Any,
            SimpleNamespace(
                tick=10,
                char_data=SimpleNamespace(char_obj_list=[character]),
                listener_manager=SimpleNamespace(broadcast_event=lambda **kwargs: None),
            ),
        ),
    )
    call_order: list[str] = []
    captured: dict[str, object] = {}

    class _FakeCalculator:
        def __init__(self, *, dynamic_buff, **kwargs) -> None:
            call_order.append("calculate_damage")
            captured["calculator_dynamic_buff"] = dynamic_buff
            self.regular_multipliers = SimpleNamespace(crit_rate=0.1, crit_dmg=0.5)

        def cal_snapshot(self):
            return (1, 2.5, [1, 2, 3])

        def cal_stun(self):
            return 3.5

        def cal_dmg_expect(self):
            return 4.5

        def cal_dmg_crit(self):
            return 5.5

    handler = SkillEventHandler()
    monkeypatch.setattr(skill_module, "Calculator", _FakeCalculator)
    monkeypatch.setattr(
        handler,
        "_update_damage_effects",
        lambda *args, **kwargs: call_order.append("update_damage_effects"),
    )
    monkeypatch.setattr(skill_module.Report, "report_dmg_result", lambda **kwargs: None)
    monkeypatch.setattr(handler, "_validate_event", lambda *args, **kwargs: None)
    monkeypatch.setattr(handler, "_get_execute_tick", lambda *args, **kwargs: 10)
    monkeypatch.setattr(handler, "_find_character", lambda *args, **kwargs: character)

    event = _build_skill_node()
    handler.handle(event, context)

    assert captured["calculator_dynamic_buff"] is runtime_view.active_buff_view
    assert runtime_view.active_view_calls == 1
    assert call_order[:2] == ["calculate_damage", "update_damage_effects"]
    assert runtime_command_port.calls == [
        (
            "update_anomaly",
            {
                "element_type": event.element_type,
                "enemy": enemy,
                "tick": 10,
                "skill_node": event,
            },
        ),
        (
            "settle_buffs",
            {
                "tick": 10,
                "enemy": enemy,
                "skill_node": event,
            },
        ),
    ]
