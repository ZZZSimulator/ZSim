from __future__ import annotations

from types import SimpleNamespace

from zsim.sim_progress.Buff.BuffXLogic.dot_runtime_state_read import DotRuntimeStateReadPort
from zsim.sim_progress.Dot.BaseDot import Dot
from zsim.sim_progress.Dot.runtime_state import DotRuntimeStateAdapter


class _RecordingDotList(list[Dot]):
    def __init__(
        self,
        call_order: list[tuple[str, str]],
        items: list[Dot] | None = None,
    ) -> None:
        super().__init__(items or [])
        self._call_order = call_order

    def append(self, item: Dot) -> None:
        self._call_order.append(("append", getattr(item, "label")))
        super().append(item)

    def remove(self, item: Dot) -> None:
        self._call_order.append(("remove", getattr(item, "label")))
        super().remove(item)


class _ForbiddenLayer:
    def __getattr__(self, name: str) -> object:
        raise AssertionError(f"dot runtime-state adapter touched forbidden layer: {name}")

    def publish_scheduled(self, event: object) -> None:
        raise AssertionError("dot runtime-state adapter should not publish scheduled events")

    def broadcast_event(self, **kwargs: object) -> None:
        raise AssertionError("dot runtime-state adapter should not broadcast listeners")

    def update_anomaly(self, **kwargs: object) -> None:
        raise AssertionError("dot runtime-state adapter should not issue runtime commands")


class _FakeDot(Dot):
    def __init__(
        self,
        *,
        index: str,
        label: str,
        call_order: list[tuple[str, str]] | None = None,
    ) -> None:
        super().__init__(bar=None, sim_instance=None)
        self.ft.index = index
        self.ft.max_duration = 60
        self.label = label
        self.ended_at: int | None = None
        self._call_order = call_order

    def end(self, timenow: int) -> None:
        if self._call_order is not None:
            self._call_order.append(("end", self.label))
        self.ended_at = timenow
        super().end(timenow)


def test_dot_runtime_state_adapter_finds_registers_and_prevents_duplicates() -> None:
    call_order: list[tuple[str, str]] = []
    existing_dot = _FakeDot(index="Shock", label="existing")
    dynamic_state = SimpleNamespace(dynamic_dot_list=_RecordingDotList(call_order, [existing_dot]))
    adapter = DotRuntimeStateAdapter(dynamic_state)
    snapshot = adapter.snapshot()

    assert snapshot == (existing_dot,)
    assert adapter.find_by_index("Shock") is existing_dot
    assert adapter.find_active_by_index("Shock") is None
    assert adapter.find_by_index("Ignite") is None
    assert adapter.find_active_by_index("Ignite") is None

    existing_dot.dy.active = True
    assert adapter.find_active_by_index("Shock") is existing_dot

    duplicate_dot = _FakeDot(index="Shock", label="duplicate")
    assert adapter.register_if_absent(duplicate_dot) is False
    assert dynamic_state.dynamic_dot_list == [existing_dot]
    assert call_order == []

    new_dot = _FakeDot(index="Ignite", label="new")
    assert adapter.register_if_absent(new_dot) is True

    assert dynamic_state.dynamic_dot_list == [existing_dot, new_dot]
    assert snapshot == (existing_dot,)
    assert call_order == [("append", "new")]


def test_dot_runtime_state_read_port_finds_without_mutating_runtime_state() -> None:
    call_order: list[tuple[str, str]] = []
    inactive_dot = _FakeDot(index="ViviansProphecy", label="inactive")
    active_dot = _FakeDot(index="ViviansProphecy", label="active")
    other_dot = _FakeDot(index="Shock", label="shock")
    inactive_dot.dy.active = False
    active_dot.dy.active = True
    dynamic_state = SimpleNamespace(
        dynamic_dot_list=_RecordingDotList(
            call_order,
            [inactive_dot, active_dot, other_dot],
        )
    )
    enemy = SimpleNamespace(
        dynamic=dynamic_state,
        schedule_data=_ForbiddenLayer(),
        listener_manager=_ForbiddenLayer(),
        runtime_command_port=_ForbiddenLayer(),
    )

    read_port = DotRuntimeStateReadPort(enemy)

    assert read_port.snapshot() == (inactive_dot, active_dot, other_dot)
    assert read_port.find_by_index("ViviansProphecy") is inactive_dot
    assert read_port.find_active_by_index("ViviansProphecy") is active_dot
    assert read_port.find_by_index("Missing") is None
    assert read_port.find_active_by_index("Missing") is None
    assert not hasattr(read_port, "register")
    assert not hasattr(read_port, "replace_by_index")
    assert not hasattr(read_port, "remove_all")
    assert dynamic_state.dynamic_dot_list == [inactive_dot, active_dot, other_dot]
    assert call_order == []


def test_dot_runtime_state_adapter_replace_same_index_ends_removes_then_appends() -> None:
    call_order: list[tuple[str, str]] = []
    unrelated_dot = _FakeDot(index="Ignite", label="unrelated", call_order=call_order)
    old_dot_a = _FakeDot(index="Shock", label="old-a", call_order=call_order)
    old_dot_b = _FakeDot(index="Shock", label="old-b", call_order=call_order)
    replacement_dot = _FakeDot(index="Shock", label="replacement", call_order=call_order)
    dynamic_state = SimpleNamespace(
        dynamic_dot_list=_RecordingDotList(
            call_order,
            [unrelated_dot, old_dot_a, old_dot_b],
        )
    )
    adapter = DotRuntimeStateAdapter(dynamic_state)

    replaced = adapter.replace_by_index(replacement_dot, 77)

    assert replaced == (old_dot_a, old_dot_b)
    assert old_dot_a.ended_at == 77
    assert old_dot_b.ended_at == 77
    assert unrelated_dot.ended_at is None
    assert dynamic_state.dynamic_dot_list == [unrelated_dot, replacement_dot]
    assert call_order == [
        ("end", "old-a"),
        ("remove", "old-a"),
        ("end", "old-b"),
        ("remove", "old-b"),
        ("append", "replacement"),
    ]


def test_dot_runtime_state_adapter_removes_by_predicate_and_explicit_collection() -> None:
    call_order: list[tuple[str, str]] = []
    shock_dot = _FakeDot(index="Shock", label="shock", call_order=call_order)
    ignite_dot = _FakeDot(index="Ignite", label="ignite", call_order=call_order)
    ether_dot = _FakeDot(index="Corruption", label="ether", call_order=call_order)
    dynamic_state = SimpleNamespace(
        dynamic_dot_list=_RecordingDotList(
            call_order,
            [shock_dot, ignite_dot, ether_dot],
        )
    )
    adapter = DotRuntimeStateAdapter(dynamic_state)

    predicate_removed = adapter.remove_matching(lambda dot: dot.ft.index == "Shock")
    explicit_removed = adapter.remove_all([ether_dot, ignite_dot])

    assert predicate_removed == (shock_dot,)
    assert explicit_removed == (ether_dot, ignite_dot)
    assert dynamic_state.dynamic_dot_list == []
    assert shock_dot.ended_at is None
    assert ignite_dot.ended_at is None
    assert ether_dot.ended_at is None
    assert call_order == [
        ("remove", "shock"),
        ("remove", "ether"),
        ("remove", "ignite"),
    ]


def test_dot_runtime_state_adapter_does_not_touch_other_runtime_layers() -> None:
    old_dot = _FakeDot(index="Shock", label="old")
    ignite_dot = _FakeDot(index="Ignite", label="ignite")
    replacement_dot = _FakeDot(index="Shock", label="replacement")
    dynamic_state = SimpleNamespace(dynamic_dot_list=[old_dot])
    enemy = SimpleNamespace(
        dynamic=dynamic_state,
        schedule_data=_ForbiddenLayer(),
        listener_manager=_ForbiddenLayer(),
        runtime_command_port=_ForbiddenLayer(),
    )
    adapter = DotRuntimeStateAdapter.from_enemy(enemy)

    assert adapter.find_by_index("Shock") is old_dot
    duplicate_dot = _FakeDot(index="Shock", label="duplicate")
    assert adapter.register_if_absent(duplicate_dot) is False
    adapter.register(ignite_dot)
    assert adapter.replace_by_index(replacement_dot, 33) == (old_dot,)
    assert adapter.remove_all([replacement_dot]) == (replacement_dot,)

    assert dynamic_state.dynamic_dot_list == [ignite_dot]
