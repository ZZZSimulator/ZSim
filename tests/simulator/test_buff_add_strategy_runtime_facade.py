from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Iterable, SupportsIndex

from zsim.sim_progress.Buff.buff_class import Buff
from zsim.sim_progress.Buff.BuffAddStrategy import buff_add_strategy


class _BuffAddProbe(Buff):
    def __init__(
        self,
        index: str,
        *,
        operator: str = "Alice",
        add_buff_to: str = "0001",
        count: int | float = 0,
        step: int | float = 1,
        maxcount: int | float = 99,
        maxduration: int = 10,
    ) -> None:
        self.ft = SimpleNamespace(
            index=index,
            operator=operator,
            passively_updating=False,
            beneficiary=operator,
            add_buff_to=add_buff_to,
            simple_start_logic=True,
            simple_effect_logic=True,
            individual_settled=False,
            maxduration=maxduration,
            step=step,
            maxcount=maxcount,
        )
        self.dy = SimpleNamespace(
            active=False,
            ready=True,
            startticks=0,
            endticks=0,
            count=count,
            built_in_buff_box=[],
            is_changed=False,
        )
        self.history = SimpleNamespace(active_times=0)
        self.logic = SimpleNamespace(
            xstart=lambda **kwargs: None,
            xeffect=lambda: None,
        )

    def __deepcopy__(self, memo: dict[int, Any]) -> "_BuffAddProbe":
        copied = _BuffAddProbe(
            self.ft.index,
            operator=self.ft.operator,
            add_buff_to=self.ft.add_buff_to,
            count=self.dy.count,
            step=self.ft.step,
            maxcount=self.ft.maxcount,
            maxduration=self.ft.maxduration,
        )
        copied.ft.passively_updating = self.ft.passively_updating
        copied.ft.beneficiary = self.ft.beneficiary
        copied.dy.active = self.dy.active
        copied.dy.ready = self.dy.ready
        copied.dy.startticks = self.dy.startticks
        copied.dy.endticks = self.dy.endticks
        copied.dy.built_in_buff_box = list(self.dy.built_in_buff_box)
        copied.dy.is_changed = self.dy.is_changed
        copied.history.active_times = self.history.active_times
        return copied


class _FailFastPendingQueue(list[Buff]):
    def append(self, item: Buff) -> None:
        raise AssertionError("buff_add_strategy must not touch pending Buff queues")

    def extend(self, items: Iterable[Any]) -> None:
        raise AssertionError("buff_add_strategy must not touch pending Buff queues")

    def insert(self, index: SupportsIndex, item: Buff) -> None:
        raise AssertionError("buff_add_strategy must not touch pending Buff queues")

    def pop(self, index: SupportsIndex = -1) -> Buff:
        raise AssertionError("buff_add_strategy must not touch pending Buff queues")

    def clear(self) -> None:
        raise AssertionError("buff_add_strategy must not touch pending Buff queues")


class _FailFastEventList(list[object]):
    def append(self, item: object) -> None:
        raise AssertionError("buff_add_strategy must not publish scheduled events")

    def extend(self, items: Iterable[object]) -> None:
        raise AssertionError("buff_add_strategy must not publish scheduled events")

    def insert(self, index: SupportsIndex, item: object) -> None:
        raise AssertionError("buff_add_strategy must not publish scheduled events")


def _fail_listener_broadcast(*args: object, **kwargs: object) -> None:
    raise AssertionError("buff_add_strategy must not broadcast listener events")


def _make_sim_instance(
    *,
    exist_buff_dict: dict[str, dict[str, Buff]],
    loading_buff_dict: dict[str, list[Buff]],
    dynamic_buff_dict: dict[str, list[Buff]],
    enemy_debuff_mirror: list[Buff],
    tick: int = 42,
) -> Any:
    from zsim.sim_progress.ScheduledEvent.buff_runtime import BuffRuntimeState

    sim_instance = SimpleNamespace(
        load_data=SimpleNamespace(
            all_name_order_box={"Alice": ["Alice"], "enemy": ["enemy"]},
            exist_buff_dict=exist_buff_dict,
            LOADING_BUFF_DICT=loading_buff_dict,
        ),
        global_stats=SimpleNamespace(DYNAMIC_BUFF_DICT=dynamic_buff_dict),
        schedule_data=SimpleNamespace(
            event_list=_FailFastEventList(),
            enemy=SimpleNamespace(dynamic=SimpleNamespace(dynamic_debuff_list=enemy_debuff_mirror)),
        ),
        listener_manager=SimpleNamespace(broadcast_event=_fail_listener_broadcast),
        tick=tick,
    )
    sim_instance.buff_runtime_state = BuffRuntimeState(
        template_registry=exist_buff_dict,
        pending_queue=loading_buff_dict,
        active_store=dynamic_buff_dict,
        enemy_mirror=enemy_debuff_mirror,
    )
    return sim_instance


def _install_recording_runtime_facade(monkeypatch: Any) -> list[tuple[str, str, object]]:
    from zsim.sim_progress.ScheduledEvent import buff_runtime

    calls: list[tuple[str, str, object]] = []

    class _RecordingDefaultBuffRuntimeFacade(buff_runtime.DefaultBuffRuntimeFacade):
        def find_active_buff_by_index(self, beneficiary: str, buff_index: str) -> Buff | None:
            calls.append(("find_active_buff_by_index", beneficiary, buff_index))
            return super().find_active_buff_by_index(beneficiary, buff_index)

        def remove_active_buff(self, beneficiary: str, buff: Buff) -> None:
            calls.append(("remove_active_buff", beneficiary, buff))
            super().remove_active_buff(beneficiary, buff)

        def append_active_buff(self, beneficiary: str, buff: Buff) -> None:
            calls.append(("append_active_buff", beneficiary, buff))
            super().append_active_buff(beneficiary, buff)

        def sync_enemy_debuff_mirror(self, buff: Buff) -> None:
            calls.append(("sync_enemy_debuff_mirror", "enemy", buff))
            super().sync_enemy_debuff_mirror(buff)

    monkeypatch.setattr(
        buff_runtime.BuffRuntimeState,
        "create_facade",
        lambda self: _RecordingDefaultBuffRuntimeFacade(runtime_state=self),
    )
    return calls


def _record_active_owner_calls(monkeypatch: Any, sim_instance: Any) -> list[tuple[str, str, str]]:
    active_owner = sim_instance.buff_runtime_state.active_store_owner()
    calls: list[tuple[str, str, str]] = []
    original_find_by_index = active_owner.find_by_index
    original_remove = active_owner.remove
    original_append = active_owner.append

    def recording_find_by_index(beneficiary: str, buff_index: str) -> Buff | None:
        calls.append(("find", beneficiary, buff_index))
        return original_find_by_index(beneficiary, buff_index)

    def recording_remove(beneficiary: str, buff: Buff) -> None:
        calls.append(("remove", beneficiary, buff.ft.index))
        original_remove(beneficiary, buff)

    def recording_append(beneficiary: str, buff: Buff) -> None:
        calls.append(("append", beneficiary, buff.ft.index))
        original_append(beneficiary, buff)

    monkeypatch.setattr(active_owner, "find_by_index", recording_find_by_index)
    monkeypatch.setattr(active_owner, "remove", recording_remove)
    monkeypatch.setattr(active_owner, "append", recording_append)
    return calls


def _install_runtime_command_creation_guard(monkeypatch: Any) -> None:
    from zsim.sim_progress.ScheduledEvent import runtime_command

    def fail_create_runtime_command_port(*args: object, **kwargs: object) -> None:
        raise AssertionError("buff_add_strategy must not create RuntimeCommandPort")

    monkeypatch.setattr(
        runtime_command,
        "create_runtime_command_port",
        fail_create_runtime_command_port,
    )


def _assert_pending_queues_untouched(
    sim_instance: Any, pending_queues: dict[str, list[Buff]]
) -> None:
    for name, pending_queue in pending_queues.items():
        assert sim_instance.load_data.LOADING_BUFF_DICT[name] is pending_queue
        assert pending_queue == []


def test_buff_add_strategy_forced_add_template_lookup_uses_runtime_owner(
    monkeypatch: Any,
) -> None:
    from zsim.sim_progress.ScheduledEvent import buff_runtime

    _install_runtime_command_creation_guard(monkeypatch)
    owner_template = _BuffAddProbe("owner-buff", count=2, step=1)
    raw_shadow_template = _BuffAddProbe("owner-buff", count=40, step=1)
    active_store: list[Buff] = []
    sim_instance = _make_sim_instance(
        exist_buff_dict={"Alice": {"owner-buff": owner_template}},
        loading_buff_dict={"Alice": _FailFastPendingQueue()},
        dynamic_buff_dict={"Alice": active_store},
        enemy_debuff_mirror=[],
    )
    sim_instance.load_data.exist_buff_dict = {"Alice": {"owner-buff": raw_shadow_template}}
    template_owner = sim_instance.buff_runtime_state.template_registry_owner()
    owner_calls: list[tuple[str, str]] = []
    original_items = template_owner.items
    original_for_owner = template_owner.for_owner

    def recording_items() -> Any:
        owner_calls.append(("items", "*"))
        return original_items()

    def recording_for_owner(beneficiary: str) -> dict[str, Buff]:
        owner_calls.append(("for_owner", beneficiary))
        return original_for_owner(beneficiary)

    def fail_compat_access() -> dict[str, dict[str, Buff]]:
        raise AssertionError("forced add must not read the compatibility registry")

    class _OwnerOnlyForcedAddFacade(buff_runtime.DefaultBuffRuntimeFacade):
        def create_forced_add_buff(
            self,
            beneficiary: str,
            buff_index: str,
            *,
            tick: int,
            specified_count: int | float | None = None,
        ) -> Buff:
            raise AssertionError("buff_add_strategy should clone through BuffTemplateRegistry")

    monkeypatch.setattr(template_owner, "items", recording_items)
    monkeypatch.setattr(template_owner, "for_owner", recording_for_owner)
    monkeypatch.setattr(
        sim_instance.buff_runtime_state,
        "template_registry_for_compat",
        fail_compat_access,
        raising=False,
    )
    monkeypatch.setattr(
        buff_runtime.BuffRuntimeState,
        "create_facade",
        lambda self: _OwnerOnlyForcedAddFacade(runtime_state=self),
    )

    buff_add_strategy("owner-buff", benifit_list=["Alice"], sim_instance=sim_instance)

    assert owner_calls == [("items", "*"), ("for_owner", "Alice")]
    assert len(active_store) == 1
    new_active_buff = active_store[0]
    assert new_active_buff is not owner_template
    assert new_active_buff.dy.count == 3
    assert owner_template.dy.count == 3
    assert owner_template.history.active_times == 1
    assert raw_shadow_template.dy.count == 40
    assert raw_shadow_template.history.active_times == 0
    assert sim_instance.load_data.LOADING_BUFF_DICT["Alice"] == []


def test_buff_add_strategy_replaces_active_store_through_runtime_facade(
    monkeypatch: Any,
) -> None:
    facade_calls = _install_recording_runtime_facade(monkeypatch)
    _install_runtime_command_creation_guard(monkeypatch)
    template_buff = _BuffAddProbe("forced-buff", count=1)
    old_active_buff = _BuffAddProbe("forced-buff", count=9)
    unrelated_active_buff = _BuffAddProbe("other-buff", count=2)
    other_target_active_buff = _BuffAddProbe("forced-buff", count=5)
    active_store = [old_active_buff, unrelated_active_buff]
    other_target_active_store = [other_target_active_buff]
    pending_queue: list[Buff] = _FailFastPendingQueue()
    sim_instance = _make_sim_instance(
        exist_buff_dict={"Alice": {"forced-buff": template_buff}},
        loading_buff_dict={"Alice": pending_queue, "Bob": _FailFastPendingQueue()},
        dynamic_buff_dict={"Alice": active_store, "Bob": other_target_active_store},
        enemy_debuff_mirror=[],
    )
    active_owner_calls = _record_active_owner_calls(monkeypatch, sim_instance)

    buff_add_strategy(
        "forced-buff",
        benifit_list=["Alice"],
        specified_count=3,
        sim_instance=sim_instance,
    )

    assert sim_instance.global_stats.DYNAMIC_BUFF_DICT["Alice"] is active_store
    assert active_store[0] is unrelated_active_buff
    assert len(active_store) == 2
    new_active_buff = active_store[1]
    assert new_active_buff is not old_active_buff
    assert new_active_buff is not template_buff
    assert old_active_buff not in active_store
    assert other_target_active_store == [other_target_active_buff]
    assert new_active_buff.ft.index == "forced-buff"
    assert new_active_buff.dy.count == 3
    assert new_active_buff.dy.startticks == 42
    assert new_active_buff.dy.endticks == 52
    assert pending_queue == []
    assert template_buff.history.active_times == 1
    assert facade_calls == [
        ("find_active_buff_by_index", "Alice", "forced-buff"),
        ("remove_active_buff", "Alice", old_active_buff),
        ("append_active_buff", "Alice", new_active_buff),
    ]
    assert active_owner_calls == [
        ("find", "Alice", "forced-buff"),
        ("remove", "Alice", "forced-buff"),
        ("append", "Alice", "forced-buff"),
    ]


def test_buff_add_strategy_auto_fanout_replaces_each_selected_target(
    monkeypatch: Any,
) -> None:
    facade_calls = _install_recording_runtime_facade(monkeypatch)
    _install_runtime_command_creation_guard(monkeypatch)
    alice_template = _BuffAddProbe("fanout-buff", add_buff_to="1100", count=2, step=2)
    bob_template = _BuffAddProbe("fanout-buff", add_buff_to="1100", count=5)
    corin_template = _BuffAddProbe("fanout-buff", add_buff_to="1100", count=8)
    alice_old = _BuffAddProbe("fanout-buff", count=12)
    bob_old = _BuffAddProbe("fanout-buff", count=13)
    alice_unrelated = _BuffAddProbe("other-buff", count=1)
    bob_unrelated = _BuffAddProbe("other-buff", count=2)
    corin_active = _BuffAddProbe("fanout-buff", count=14)
    alice_store = [alice_old, alice_unrelated]
    bob_store = [bob_old, bob_unrelated]
    corin_store = [corin_active]
    pending_queues: dict[str, list[Buff]] = {
        "Alice": _FailFastPendingQueue(),
        "Bob": _FailFastPendingQueue(),
        "Corin": _FailFastPendingQueue(),
    }
    sim_instance = _make_sim_instance(
        exist_buff_dict={
            "Alice": {"fanout-buff": alice_template},
            "Bob": {"fanout-buff": bob_template},
            "Corin": {"fanout-buff": corin_template},
        },
        loading_buff_dict=pending_queues,
        dynamic_buff_dict={
            "Alice": alice_store,
            "Bob": bob_store,
            "Corin": corin_store,
        },
        enemy_debuff_mirror=[],
    )
    sim_instance.load_data.all_name_order_box = {
        "Alice": ["Alice", "Bob", "Corin", "Daisy"],
        "enemy": ["enemy"],
    }

    buff_add_strategy("fanout-buff", sim_instance=sim_instance)

    alice_replacements = [buff for buff in alice_store if buff.ft.index == "fanout-buff"]
    bob_replacements = [buff for buff in bob_store if buff.ft.index == "fanout-buff"]
    assert len(alice_replacements) == 1
    assert len(bob_replacements) == 1
    alice_new = alice_replacements[0]
    bob_new = bob_replacements[0]
    assert alice_new is not alice_old
    assert alice_new is not alice_template
    assert bob_new is not bob_old
    assert bob_new is not bob_template
    assert alice_store == [alice_unrelated, alice_new]
    assert bob_store == [bob_unrelated, bob_new]
    assert corin_store == [corin_active]
    assert alice_new.dy.count == 4
    assert bob_new.dy.count == 6
    assert alice_new.dy.startticks == 42
    assert bob_new.dy.startticks == 42
    assert alice_new.dy.endticks == 52
    assert bob_new.dy.endticks == 52
    assert alice_template.dy.count == 4
    assert bob_template.dy.count == 6
    assert alice_template.dy.startticks == 42
    assert bob_template.dy.startticks == 42
    assert alice_template.dy.endticks == 52
    assert bob_template.dy.endticks == 52
    assert alice_template.history.active_times == 1
    assert bob_template.history.active_times == 1
    assert corin_template.dy.count == 8
    assert corin_template.history.active_times == 0
    _assert_pending_queues_untouched(sim_instance, pending_queues)
    assert facade_calls == [
        ("find_active_buff_by_index", "Alice", "fanout-buff"),
        ("remove_active_buff", "Alice", alice_old),
        ("append_active_buff", "Alice", alice_new),
        ("find_active_buff_by_index", "Bob", "fanout-buff"),
        ("remove_active_buff", "Bob", bob_old),
        ("append_active_buff", "Bob", bob_new),
    ]


def test_buff_add_strategy_explicit_targets_override_auto_selection(
    monkeypatch: Any,
) -> None:
    facade_calls = _install_recording_runtime_facade(monkeypatch)
    _install_runtime_command_creation_guard(monkeypatch)
    alice_template = _BuffAddProbe("override-buff", add_buff_to="1100", count=1)
    bob_template = _BuffAddProbe("override-buff", add_buff_to="1100", count=6)
    corin_template = _BuffAddProbe("override-buff", add_buff_to="1100", count=2)
    alice_active = _BuffAddProbe("override-buff", count=9)
    bob_active = _BuffAddProbe("override-buff", count=10)
    corin_old = _BuffAddProbe("override-buff", count=11)
    alice_store = [alice_active]
    bob_store = [bob_active]
    corin_store = [corin_old]
    pending_queues: dict[str, list[Buff]] = {
        "Alice": _FailFastPendingQueue(),
        "Bob": _FailFastPendingQueue(),
        "Corin": _FailFastPendingQueue(),
    }
    sim_instance = _make_sim_instance(
        exist_buff_dict={
            "Alice": {"override-buff": alice_template},
            "Bob": {"override-buff": bob_template},
            "Corin": {"override-buff": corin_template},
        },
        loading_buff_dict=pending_queues,
        dynamic_buff_dict={
            "Alice": alice_store,
            "Bob": bob_store,
            "Corin": corin_store,
        },
        enemy_debuff_mirror=[],
    )
    sim_instance.load_data.all_name_order_box = {
        "Alice": ["Alice", "Bob", "Corin", "Daisy"],
        "enemy": ["enemy"],
    }

    buff_add_strategy(
        "override-buff",
        benifit_list=["Corin"],
        specified_count=7,
        sim_instance=sim_instance,
    )

    assert alice_store == [alice_active]
    assert bob_store == [bob_active]
    assert len(corin_store) == 1
    corin_new = corin_store[0]
    assert corin_new is not corin_old
    assert corin_new is not corin_template
    assert corin_old not in corin_store
    assert corin_new.dy.count == 7
    assert corin_new.dy.startticks == 42
    assert corin_new.dy.endticks == 52
    assert corin_template.dy.count == 7
    assert corin_template.dy.startticks == 42
    assert corin_template.dy.endticks == 52
    assert corin_template.history.active_times == 1
    assert alice_template.dy.count == 1
    assert bob_template.dy.count == 6
    assert alice_template.history.active_times == 0
    assert bob_template.history.active_times == 0
    _assert_pending_queues_untouched(sim_instance, pending_queues)
    assert facade_calls == [
        ("find_active_buff_by_index", "Corin", "override-buff"),
        ("remove_active_buff", "Corin", corin_old),
        ("append_active_buff", "Corin", corin_new),
    ]


def test_buff_add_strategy_syncs_enemy_debuff_mirror_through_runtime_facade(
    monkeypatch: Any,
) -> None:
    facade_calls = _install_recording_runtime_facade(monkeypatch)
    _install_runtime_command_creation_guard(monkeypatch)
    template_debuff = _BuffAddProbe(
        "forced-debuff",
        operator="enemy",
        add_buff_to="0001",
        count=0,
    )
    old_active_debuff = _BuffAddProbe("forced-debuff", operator="enemy")
    unrelated_active_debuff = _BuffAddProbe("other-debuff", operator="enemy")
    old_mirror_debuff = _BuffAddProbe("forced-debuff", operator="enemy")
    other_mirror_debuff = _BuffAddProbe("other-debuff", operator="enemy")
    active_store = [old_active_debuff, unrelated_active_debuff]
    enemy_debuff_mirror = [old_mirror_debuff, other_mirror_debuff]
    sim_instance = _make_sim_instance(
        exist_buff_dict={"enemy": {"forced-debuff": template_debuff}},
        loading_buff_dict={"enemy": _FailFastPendingQueue()},
        dynamic_buff_dict={"enemy": active_store},
        enemy_debuff_mirror=enemy_debuff_mirror,
    )
    runtime_enemy_store = sim_instance.global_stats.DYNAMIC_BUFF_DICT["enemy"]
    assert runtime_enemy_store is enemy_debuff_mirror

    buff_add_strategy(
        "forced-debuff",
        benifit_list=["enemy"],
        sim_instance=sim_instance,
    )

    assert active_store == [old_active_debuff, unrelated_active_debuff]
    assert runtime_enemy_store[0] is unrelated_active_debuff
    assert len(runtime_enemy_store) == 2
    new_debuff = runtime_enemy_store[1]
    assert new_debuff.ft.index == "forced-debuff"
    assert new_debuff is not old_active_debuff
    assert old_active_debuff not in runtime_enemy_store
    assert enemy_debuff_mirror == [unrelated_active_debuff, new_debuff]
    assert old_mirror_debuff not in runtime_enemy_store
    assert other_mirror_debuff not in runtime_enemy_store
    assert enemy_debuff_mirror[1] is new_debuff
    assert sim_instance.load_data.LOADING_BUFF_DICT["enemy"] == []
    assert facade_calls == [
        ("find_active_buff_by_index", "enemy", "forced-debuff"),
        ("remove_active_buff", "enemy", old_active_debuff),
        ("append_active_buff", "enemy", new_debuff),
        ("sync_enemy_debuff_mirror", "enemy", new_debuff),
    ]


def test_buff_runtime_read_port_stays_read_only_for_buff_add_strategy() -> None:
    from zsim.sim_progress.ScheduledEvent.buff_runtime import BuffRuntimeReadPort

    write_method_names = {
        "append_active_buff",
        "remove_active_buff",
        "sync_enemy_debuff_mirror",
        "enqueue_pending_buff",
        "drain_pending_buffs",
        "clear_pending_buffs",
        "activate_pending_buffs",
    }

    assert write_method_names.isdisjoint(BuffRuntimeReadPort.__dict__)
