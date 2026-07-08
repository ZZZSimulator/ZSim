from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from zsim.sim_progress.Character.wakeup import CharacterResourceThresholds
from zsim.sim_progress.data_struct.planned_queue import PlannedEventQueue
from zsim.simulator.simulator_class import Simulator


class _CountingInventory(dict[int, object]):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.values_calls = 0

    def values(self):  # type: ignore[override]
        self.values_calls += 1
        return super().values()


def _condition(cid: int | str, stat: str, value: float | str) -> SimpleNamespace:
    return SimpleNamespace(
        check_target=str(cid),
        check_stat=stat,
        check_value=value,
    )


def _apl_unit(
    sub_conditions: list[SimpleNamespace] | None = None,
    builtin_conditions: list[SimpleNamespace] | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        sub_conditions_unit_list=[] if sub_conditions is None else sub_conditions,
        builtin_percond_list=[] if builtin_conditions is None else builtin_conditions,
    )


def _sim_with_operator(apl_operator: object | None) -> Simulator:
    sim = Simulator()
    sim.preload = SimpleNamespace(
        strategy=SimpleNamespace(
            apl_engine=SimpleNamespace(
                apl=SimpleNamespace(apl_operator=apl_operator, operator=apl_operator)
            )
        )
    )
    return sim


def _minimal_wakeup_sim(apl_operator: object, char_obj_list: list[object]) -> Simulator:
    sim = _sim_with_operator(apl_operator)
    sim.char_data = SimpleNamespace(char_obj_list=char_obj_list)
    sim.load_data = SimpleNamespace(load_mission_dict={})
    sim.schedule_data = SimpleNamespace(
        enemy=SimpleNamespace(
            dynamic=SimpleNamespace(stun=False),
            special_state_manager=SimpleNamespace(observers={}),
        ),
        planned_event_queue=PlannedEventQueue(
            get_events=lambda: [],
            set_events=lambda new_events: None,
        ),
    )
    sim.preload.preload_data = SimpleNamespace(
        preload_action_list_before_confirm=[],
        personal_node_stack={},
        current_node_stack=[],
    )
    return sim


def test_cached_threshold_map_matches_fresh_scan_for_resource_conditions() -> None:
    inventory = _CountingInventory(
        {
            1: _apl_unit(
                [
                    _condition(1361, "energy", 60),
                    _condition(1361, "energy", "50"),
                    _condition(1361, "special_resource", 30),
                    _condition(1361, "ignored", 999),
                    _condition("not-a-cid", "energy", 70),
                ],
                [_condition(1361, "decibel", 3000)],
            ),
            2: _apl_unit([_condition(1371, "adrenaline", 120)]),
        }
    )
    sim = _sim_with_operator(SimpleNamespace(apl_unit_inventory=inventory))

    expected = Simulator._scan_apl_resource_thresholds_by_cid(inventory)

    assert sim._apl_resource_thresholds_by_cid() == expected
    assert sim._apl_resource_thresholds_by_cid() == {
        1361: CharacterResourceThresholds(
            energy=(50.0, 60.0),
            special_resource=(30.0,),
            decibel=(3000.0,),
        ),
        1371: CharacterResourceThresholds(adrenaline=(120.0,)),
    }
    assert inventory.values_calls == 2


def test_resource_threshold_cache_reuses_scan_until_operator_or_lists_change() -> None:
    sub_conditions = [_condition(1361, "energy", 60)]
    apl_unit = _apl_unit(sub_conditions)
    inventory = _CountingInventory({1: apl_unit})
    operator = SimpleNamespace(apl_unit_inventory=inventory)
    sim = _sim_with_operator(operator)

    assert sim._apl_resource_thresholds_by_cid()[1361].energy == (60.0,)
    assert sim._apl_resource_thresholds_by_cid()[1361].energy == (60.0,)
    assert inventory.values_calls == 1

    sub_conditions.append(_condition(1361, "energy", 80))

    assert sim._apl_resource_thresholds_by_cid()[1361].energy == (60.0, 80.0)
    assert inventory.values_calls == 2

    replacement_inventory = _CountingInventory(
        {1: _apl_unit([_condition(1361, "special_resource", 40)])}
    )
    sim.preload.strategy.apl_engine.apl.apl_operator = SimpleNamespace(
        apl_unit_inventory=replacement_inventory
    )

    thresholds = sim._apl_resource_thresholds_by_cid()

    assert thresholds[1361] == CharacterResourceThresholds(special_resource=(40.0,))
    assert replacement_inventory.values_calls == 1


def test_resource_threshold_cache_returns_empty_when_apl_is_uninitialized() -> None:
    inventory = _CountingInventory({1: _apl_unit([_condition(1361, "energy", 60)])})
    sim = _sim_with_operator(SimpleNamespace(apl_unit_inventory=inventory))

    assert sim._apl_resource_thresholds_by_cid()

    sim.preload = SimpleNamespace()

    assert sim._apl_resource_thresholds_by_cid() == {}
    assert sim._apl_resource_threshold_cache is None
    assert sim._apl_resource_threshold_cache_key is None

    sim = _sim_with_operator(SimpleNamespace(apl_unit_inventory=None))

    assert sim._apl_resource_thresholds_by_cid() == {}


def test_resource_threshold_cache_preserves_all_resource_wakeup_decisions() -> None:
    inventory = _CountingInventory(
        {
            1: _apl_unit([_condition(1361, "energy", 30)]),
            2: _apl_unit([_condition(1371, "special_resource", 20)]),
            3: _apl_unit([_condition(1381, "adrenaline", 40)]),
            4: _apl_unit([_condition(1391, "decibel", 10)]),
        }
    )
    seen: dict[int, CharacterResourceThresholds | None] = {}

    def _char(cid: int) -> SimpleNamespace:
        def next_resource_wakeup_tick(
            current_tick: int,
            *,
            thresholds: CharacterResourceThresholds | None = None,
        ) -> int | None:
            seen[cid] = thresholds
            if thresholds is None:
                return None
            if thresholds.energy:
                return current_tick + int(thresholds.energy[0])
            if thresholds.special_resource:
                return current_tick + int(thresholds.special_resource[0])
            if thresholds.adrenaline:
                return current_tick + int(thresholds.adrenaline[0])
            if thresholds.decibel:
                return current_tick + int(thresholds.decibel[0])
            return None

        return SimpleNamespace(
            CID=cid,
            next_resource_wakeup_tick=next_resource_wakeup_tick,
        )

    sim = _minimal_wakeup_sim(
        SimpleNamespace(apl_unit_inventory=inventory),
        [_char(1361), _char(1371), _char(1381), _char(1391)],
    )

    source = next(
        source
        for source in sim._main_loop_wakeup_sources(100, buff_runtime=None)
        if source.name == "character-resource"
    )

    assert source.next_wakeup_tick(5) == 15
    assert seen == {
        1361: CharacterResourceThresholds(energy=(30.0,)),
        1371: CharacterResourceThresholds(special_resource=(20.0,)),
        1381: CharacterResourceThresholds(adrenaline=(40.0,)),
        1391: CharacterResourceThresholds(decibel=(10.0,)),
    }
    assert sim._apl_resource_thresholds_by_cid()[1391].decibel == (10.0,)
    assert inventory.values_calls == 1
