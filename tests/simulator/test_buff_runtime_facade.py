from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast

import pytest

from zsim.sim_progress.Buff.buff_class import Buff
from zsim.sim_progress.ScheduledEvent.buff_runtime import (
    BuffRuntimeState,
    DefaultBuffRuntimeFacade,
    DefaultBuffRuntimeReadAdapter,
)


class _BuffProbe(Buff):
    def __init__(
        self,
        index: str,
        *,
        active: bool = True,
        startticks: int = 1,
        endticks: int = 10,
        count: int = 1,
        alltime: bool = False,
        is_debuff: bool = False,
    ) -> None:
        self.ft = SimpleNamespace(
            index=index,
            alltime=alltime,
            simple_exit_logic=True,
            individual_settled=False,
            is_debuff=is_debuff,
            simple_start_logic=True,
            simple_effect_logic=True,
            operator="alpha",
            passively_updating=False,
            beneficiary="alpha",
        )
        self.dy = SimpleNamespace(
            active=active,
            startticks=startticks,
            endticks=endticks,
            count=count,
            built_in_buff_box=[],
            is_changed=False,
        )
        self.history = SimpleNamespace()
        self.logic = SimpleNamespace(xexit=lambda **_: False)
        self.end_calls: list[tuple[int, dict[str, Any]]] = []
        self.simple_start_calls: list[tuple[int, dict[str, Any]]] = []

    def end(self, timenow: int, template_registry: dict[str, Any]) -> None:
        self.end_calls.append((timenow, template_registry))
        self.dy.active = False
        self.dy.count = 0

    def simple_start(self, timenow: int, template_registry: dict[str, Any], **_: Any) -> None:
        self.simple_start_calls.append((timenow, template_registry))
        self.dy.active = True


def _runtime_state_for_test(
    *,
    registry: dict[str, dict[str, Any]] | None = None,
    pending: dict[str, list[Any]] | None = None,
    active: dict[str, list[Any]] | None = None,
    enemy_mirror: list[Any] | None = None,
) -> BuffRuntimeState:
    return BuffRuntimeState(
        template_registry={} if registry is None else registry,
        pending_queue={} if pending is None else pending,
        active_store={} if active is None else active,
        enemy_mirror=[] if enemy_mirror is None else enemy_mirror,
    )


def test_runtime_state_exposes_owner_apis_without_compat_methods() -> None:
    runtime_state = _runtime_state_for_test(
        registry={"alpha": {}},
        pending={"alpha": []},
        active={"alpha": []},
    )

    assert runtime_state.template_registry_owner().mutable_registry() == {"alpha": {}}
    assert runtime_state.pending_queue_owner().mutable_queues() == {"alpha": []}
    assert runtime_state.active_store_owner().mutable_stores() == {"alpha": [], "enemy": []}

    for old_name in (
        "template_registry_for_compat",
        "pending_queue_for_compat",
        "active_store_for_compat",
        "enemy_mirror_for_compat",
    ):
        assert not hasattr(runtime_state, old_name)


def test_read_adapter_returns_snapshots_not_mutable_runtime_maps() -> None:
    active_buff = _BuffProbe("active")
    template_buff = _BuffProbe("template")
    runtime_state = _runtime_state_for_test(
        registry={"alpha": {"template": template_buff}},
        active={"alpha": [active_buff]},
    )
    read_port = DefaultBuffRuntimeReadAdapter(runtime_state=runtime_state)

    active_snapshot = read_port.get_active_buffs("alpha")
    registry_snapshot = read_port.get_exist_buff_snapshot("alpha")
    runtime_state.active_store_owner().append("alpha", _BuffProbe("new-active"))
    runtime_state.template_registry_owner().for_owner("alpha")["new-template"] = _BuffProbe(
        "new-template"
    )

    assert active_snapshot == (active_buff,)
    assert dict(registry_snapshot) == {"template": template_buff}


def test_facade_activates_pending_buffs_through_runtime_owners() -> None:
    pending_buff = _BuffProbe("pending")
    enemy_debuff = _BuffProbe("enemy-debuff", is_debuff=True)
    enemy_mirror: list[Any] = []
    runtime_state = _runtime_state_for_test(
        registry={"alpha": {}, "enemy": {}},
        pending={"alpha": [pending_buff], "enemy": [enemy_debuff]},
        active={"alpha": [], "enemy": []},
        enemy_mirror=enemy_mirror,
    )
    facade = DefaultBuffRuntimeFacade(runtime_state=runtime_state)

    result = facade.activate_pending_buffs(timenow=10)

    assert result["alpha"] == [pending_buff]
    assert result["enemy"] == [enemy_debuff]
    assert enemy_mirror == [enemy_debuff]
    assert runtime_state.pending_queue_owner().count() == 0


def test_facade_wakes_one_tick_after_pending_activation_for_reporting(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pending_buff = _BuffProbe("pending", endticks=100)
    runtime_state = _runtime_state_for_test(
        registry={"alpha": {}},
        pending={"alpha": [pending_buff]},
        active={"alpha": []},
    )
    facade = DefaultBuffRuntimeFacade(runtime_state=runtime_state)

    from zsim.sim_progress.Update import Update_Buff

    monkeypatch.setattr(Update_Buff, "next_dot_or_anomaly_wakeup_tick", lambda *_: None)

    facade.activate_pending_buffs(timenow=10)

    assert facade.next_time_related_wakeup_tick(current_tick=10, enemy=SimpleNamespace()) == 11
    assert facade.next_time_related_wakeup_tick(current_tick=11, enemy=SimpleNamespace()) == 101


def test_facade_sweep_active_buffs_uses_template_owner_for_expiry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expired = _BuffProbe("expired", endticks=3)
    active = {"alpha": [expired]}
    registry = {"alpha": {"expired": expired}}
    runtime_state = _runtime_state_for_test(registry=registry, active=active)
    facade = DefaultBuffRuntimeFacade(runtime_state=runtime_state)

    from zsim.sim_progress.Update import Update_Buff

    monkeypatch.setattr(Update_Buff, "CheckBuff", lambda *_: None)
    monkeypatch.setattr(Update_Buff, "report_buff_to_queue", lambda *_, **__: None)

    result = facade.sweep_active_buffs(tick=4)

    assert result is runtime_state.active_store_owner().mutable_stores()
    assert active["alpha"] == []
    assert expired.end_calls == [(4, registry["alpha"])]


def test_create_buff_runtime_read_port_requires_runtime_state() -> None:
    from zsim.sim_progress.ScheduledEvent.buff_runtime import create_buff_runtime_read_port

    runtime_state = _runtime_state_for_test()
    factory = cast(Any, create_buff_runtime_read_port)

    assert create_buff_runtime_read_port(runtime_state=runtime_state) is not None
    with pytest.raises(TypeError):
        factory()
