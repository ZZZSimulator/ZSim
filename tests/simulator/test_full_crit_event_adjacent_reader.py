from __future__ import annotations

import inspect
import sys
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any, Iterator, Sequence, SupportsIndex, cast

import pytest

import zsim.define as define_module

sys.modules.setdefault("define", define_module)

import zsim.sim_progress.Buff.BuffXLogic.CannonRotor as cannon_module
import zsim.sim_progress.Buff.BuffXLogic.MiyabiCoreSkill_IceFire as miyabi_module
import zsim.sim_progress.calculation.calculator as calculator_module
import zsim.sim_progress.data_struct.schedule_dispatch as schedule_dispatch_module
import zsim.sim_progress.ScheduledEvent as scheduled_event_module
import zsim.sim_progress.ScheduledEvent.buff_runtime as buff_runtime_module
import zsim.sim_progress.ScheduledEvent.runtime_command as runtime_command_module
from zsim.sim_progress.Buff import Buff as BuffClass
from zsim.sim_progress.Buff import JudgeTools
from zsim.sim_progress.Buff.BuffXLogic.CannonRotor import CannonRotor
from zsim.sim_progress.Buff.BuffXLogic.MiyabiCoreSkill_IceFire import (
    MiyabiCoreSkill_IceFire,
    MiyabiCoreSkillIF,
)
from zsim.sim_progress.Buff.BuffXLogic.WoodpeckerElectroSet4_CA import (
    WoodpeckerElectroSet4_CA,
)
from zsim.sim_progress.Buff.BuffXLogic.WoodpeckerElectroSet4_E_EX import (
    WoodpeckerElectroSet4_E_EX,
)
from zsim.sim_progress.Buff.BuffXLogic.WoodpeckerElectroSet4_NA import (
    WoodpeckerElectroSet4_NA,
)
from zsim.sim_progress.calculation.calculator import (
    Calculator,
    CalculatorBuffAttributeReader,
    MultiplierData,
    create_anomaly_attribute_read_context,
)
from zsim.sim_progress.Preload import SkillNode

_AggregationCall = tuple[tuple[object, ...], object | None, object, str | None]


class _FailFastEventList(list[object]):
    def append(self, item: object) -> None:
        raise AssertionError("full crit reader tests should not append raw events")

    def extend(self, items: object) -> None:
        raise AssertionError("full crit reader tests should not extend raw events")

    def insert(self, index: SupportsIndex, item: object) -> None:
        raise AssertionError("full crit reader tests should not insert raw events")


class _FailFastDispatchPort:
    def publish_scheduled(self, event: object) -> None:
        raise AssertionError("full crit reader tests should not publish scheduled events")


class _FailFastMiyabiJudgeRuntimeCommandPort:
    def __getattr__(self, name: str) -> object:
        raise AssertionError("Miyabi IceFire judge should not issue runtime commands")


class _FailFastMiyabiJudgeDotRuntimeState:
    def __getattr__(self, name: str) -> object:
        raise AssertionError("Miyabi IceFire judge should not mutate dot runtime state")

    def __setattr__(self, name: str, value: object) -> None:
        raise AssertionError("Miyabi IceFire judge should not mutate dot runtime state")


class _DebuffMirrorProbe:
    def __init__(
        self,
        call_order: list[object],
        entries: Sequence[object],
        *,
        fail_on_iter: bool = False,
    ) -> None:
        self._call_order = call_order
        self._entries = list(entries)
        self._fail_on_iter = fail_on_iter
        self.iterations = 0

    def __iter__(self) -> Iterator[object]:
        self._call_order.append("dynamic_debuff_list.iter")
        self.iterations += 1
        if self._fail_on_iter:
            raise AssertionError("Miyabi IceFire judge should not iterate debuffs here")
        return iter(self._entries)


class _DynamicDebuffMirrorReadProbe:
    def __init__(self, call_order: list[object], mirror: _DebuffMirrorProbe) -> None:
        self._call_order = call_order
        self._mirror = mirror

    @property
    def dynamic_debuff_list(self) -> _DebuffMirrorProbe:
        self._call_order.append("dynamic_debuff_list.read")
        return self._mirror


class _SkillElementReadProbe:
    def __init__(self, call_order: list[object], element_type: int) -> None:
        self._call_order = call_order
        self._element_type = element_type

    @property
    def element_type(self) -> int:
        self._call_order.append("skill_node.skill.element_type")
        return self._element_type


class _SkillNodeReadProbe:
    def __init__(self, call_order: list[object], *, char_name: str, element_type: int) -> None:
        self._call_order = call_order
        self._char_name = char_name
        self._skill = _SkillElementReadProbe(call_order, element_type)

    @property
    def char_name(self) -> str:
        self._call_order.append("skill_node.char_name")
        return self._char_name

    @property
    def skill(self) -> _SkillElementReadProbe:
        self._call_order.append("skill_node.skill")
        return self._skill


class _FakeRng:
    def __init__(self, values: Sequence[float]) -> None:
        self._values = list(values)
        self.calls: list[str] = []

    def random_float(self) -> float:
        self.calls.append("random_float")
        if not self._values:
            raise AssertionError("unexpected RNG read")
        return self._values.pop(0)


class _DynamicCountRecorder:
    def __init__(self, calls: list[tuple[Any, ...]], initial_count: float) -> None:
        self._calls = calls
        self._count = initial_count

    @property
    def count(self) -> float:
        return self._count

    @count.setter
    def count(self, value: float) -> None:
        self._calls.append(("dy.count", value))
        self._count = value


class _StateSyncBuffProbe:
    def __init__(
        self,
        *,
        index: str,
        tick: int,
        calls: list[tuple[Any, ...]],
        initial_count: float,
        maxcount: float = 999.0,
        step: float = 1.0,
    ) -> None:
        self.ft = SimpleNamespace(index=index, maxcount=maxcount, step=step)
        self.dy = _DynamicCountRecorder(calls, initial_count)
        self.sim_instance = SimpleNamespace(
            tick=tick,
            rng_instance=_FakeRng(()),
            schedule_data=SimpleNamespace(event_list=_FailFastEventList()),
        )
        self._calls = calls

    def simple_start(
        self,
        timenow: int,
        sub_exist_buff_dict: dict[str, object],
        **kwargs: object,
    ) -> None:
        no_count = bool(kwargs.get("no_count", False))
        self._calls.append(
            (
                "simple_start",
                timenow,
                no_count,
                self.dy.count,
                sub_exist_buff_dict[self.ft.index],
            )
        )
        if not no_count:
            self.dy.count = min(self.dy.count + self.ft.step, self.ft.maxcount)
            cast(Any, sub_exist_buff_dict[self.ft.index]).dy.count = self.dy.count

    def update_to_buff_0(self, buff_0: object) -> None:
        self._calls.append(("update_to_buff_0", buff_0, self.dy.count))
        cast(Any, buff_0).dy.count = self.dy.count


@dataclass(frozen=True)
class _FullCritFixture:
    sim_instance: SimpleNamespace
    char: SimpleNamespace
    enemy: SimpleNamespace
    active_buff_view: dict[str, list[object]]
    expected_enabled_buff: tuple[object, ...]


@dataclass(frozen=True)
class _WoodpeckerVariant:
    logic_type: type[Any]
    trigger_level: int


_WOODPECKER_VARIANTS = [
    pytest.param(
        _WoodpeckerVariant(WoodpeckerElectroSet4_NA, 0),
        id="WoodpeckerElectroSet4_NA",
    ),
    pytest.param(
        _WoodpeckerVariant(WoodpeckerElectroSet4_E_EX, 2),
        id="WoodpeckerElectroSet4_E_EX",
    ),
    pytest.param(
        _WoodpeckerVariant(WoodpeckerElectroSet4_CA, 4),
        id="WoodpeckerElectroSet4_CA",
    ),
]


def _make_character(*, name: str, cid: int, crit_rate: float) -> SimpleNamespace:
    statement = SimpleNamespace(
        statement={
            "AM": 0.0,
            "AP": 0.0,
            "IMP": 0.0,
            "CRIT_rate": crit_rate,
            "CRIT_damage": 0.0,
        },
        AM=0.0,
        AP=0.0,
        IMP=0.0,
        CRIT_rate=crit_rate,
        CRIT_damage=0.0,
    )
    return SimpleNamespace(NAME=name, CID=cid, level=60, statement=statement)


def _make_full_crit_fixture(
    *,
    name: str,
    cid: int,
    crit_rate: float,
    sim_instance: SimpleNamespace | None = None,
) -> _FullCritFixture:
    char_buff = object()
    enemy_debuff = object()
    sim = sim_instance or SimpleNamespace(
        tick=45,
        rng_instance=_FakeRng(()),
        schedule_data=SimpleNamespace(event_list=_FailFastEventList()),
    )
    char = _make_character(name=name, cid=cid, crit_rate=crit_rate)
    enemy = SimpleNamespace(
        dynamic=SimpleNamespace(
            dynamic_debuff_list=[enemy_debuff],
            dynamic_dot_list=[],
            frost_frostbite=False,
        ),
        sim_instance=sim,
    )
    active_buff_view = {char.NAME: [char_buff]}
    sim.buff_runtime_state = buff_runtime_module.BuffRuntimeState(
        template_registry={},
        pending_queue={},
        active_store=active_buff_view,
        enemy_mirror=enemy.dynamic.dynamic_debuff_list,
    )
    return _FullCritFixture(
        sim_instance=sim,
        char=char,
        enemy=enemy,
        active_buff_view=active_buff_view,
        expected_enabled_buff=(char_buff, enemy_debuff),
    )


def _patch_buff_aggregation(
    monkeypatch: pytest.MonkeyPatch,
    dynamic_statement: dict[str, float],
    *,
    call_log: list[tuple[Any, ...]] | None = None,
) -> list[_AggregationCall]:
    aggregation_calls: list[_AggregationCall] = []

    def fake_cal_buff_total_bonus(
        *,
        enabled_buff: tuple[object, ...],
        judge_obj: object | None,
        sim_instance: object,
        char_name: str | None,
    ) -> dict[str, float]:
        aggregation_calls.append((enabled_buff, judge_obj, sim_instance, char_name))
        if call_log is not None:
            call_log.append(("attribute_read",))
        return dict(dynamic_statement)

    monkeypatch.setattr(
        calculator_module,
        "cal_buff_total_bonus",
        fake_cal_buff_total_bonus,
    )
    return aggregation_calls


def _install_rng_service_boundary_guards(
    monkeypatch: pytest.MonkeyPatch,
    sim_instance: SimpleNamespace,
) -> None:
    def fail_change_process_state(*args: object, **kwargs: object) -> None:
        raise AssertionError("RNG service read should not change process state")

    def fail_broadcast_event(*args: object, **kwargs: object) -> None:
        raise AssertionError("RNG service read should not broadcast listener events")

    def fail_create_runtime_command_port(*args: object, **kwargs: object) -> None:
        raise AssertionError("RNG service read should not create RuntimeCommandPort")

    def fail_create_legacy_buff_runtime_facade(*args: object, **kwargs: object) -> None:
        raise AssertionError("RNG service read should not create LegacyBuffRuntimeFacade")

    def fail_create_buff_runtime_read_port(*args: object, **kwargs: object) -> None:
        raise AssertionError("RNG service read should not create BuffRuntimeReadPort")

    def fail_create_schedule_dispatch_port(*args: object, **kwargs: object) -> None:
        raise AssertionError("RNG service read should not create ScheduleDispatchPort")

    sim_instance.schedule_data.event_list = _FailFastEventList()
    sim_instance.schedule_data.change_process_state = fail_change_process_state
    sim_instance.listener_manager = SimpleNamespace(broadcast_event=fail_broadcast_event)

    monkeypatch.setattr(
        runtime_command_module,
        "create_runtime_command_port",
        fail_create_runtime_command_port,
    )
    monkeypatch.setattr(
        scheduled_event_module,
        "create_runtime_command_port",
        fail_create_runtime_command_port,
    )
    monkeypatch.setattr(
        buff_runtime_module,
        "create_legacy_buff_runtime_facade",
        fail_create_legacy_buff_runtime_facade,
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
    )
    monkeypatch.setattr(
        schedule_dispatch_module,
        "create_schedule_dispatch_port",
        fail_create_schedule_dispatch_port,
    )
    monkeypatch.setattr(
        cannon_module,
        "create_schedule_dispatch_port",
        fail_create_schedule_dispatch_port,
        raising=False,
    )


def _install_miyabi_icefire_judge_side_effect_guards(
    monkeypatch: pytest.MonkeyPatch,
    sim_instance: SimpleNamespace,
) -> None:
    def fail_change_process_state(*args: object, **kwargs: object) -> None:
        raise AssertionError("Miyabi IceFire judge should not change process state")

    def fail_broadcast_event(*args: object, **kwargs: object) -> None:
        raise AssertionError("Miyabi IceFire judge should not broadcast listener events")

    def fail_create_runtime_command_port(*args: object, **kwargs: object) -> object:
        raise AssertionError("Miyabi IceFire judge should not create RuntimeCommandPort")

    def fail_create_legacy_buff_runtime_facade(*args: object, **kwargs: object) -> object:
        raise AssertionError("Miyabi IceFire judge should not create LegacyBuffRuntimeFacade")

    def fail_create_buff_runtime_read_port(*args: object, **kwargs: object) -> object:
        raise AssertionError("Miyabi IceFire judge should not create BuffRuntimeReadPort")

    def fail_create_schedule_dispatch_port(*args: object, **kwargs: object) -> object:
        raise AssertionError("Miyabi IceFire judge should not create ScheduleDispatchPort")

    sim_instance.schedule_data.event_list = _FailFastEventList()
    sim_instance.schedule_data.change_process_state = fail_change_process_state
    sim_instance.listener_manager = SimpleNamespace(broadcast_event=fail_broadcast_event)
    sim_instance.runtime_command_port = _FailFastMiyabiJudgeRuntimeCommandPort()
    sim_instance.dot_runtime_state = _FailFastMiyabiJudgeDotRuntimeState()

    monkeypatch.setattr(
        runtime_command_module,
        "create_runtime_command_port",
        fail_create_runtime_command_port,
    )
    monkeypatch.setattr(
        scheduled_event_module,
        "create_runtime_command_port",
        fail_create_runtime_command_port,
    )
    monkeypatch.setattr(
        buff_runtime_module,
        "create_legacy_buff_runtime_facade",
        fail_create_legacy_buff_runtime_facade,
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
    )
    monkeypatch.setattr(
        schedule_dispatch_module,
        "create_schedule_dispatch_port",
        fail_create_schedule_dispatch_port,
    )
    monkeypatch.setattr(
        miyabi_module,
        "create_schedule_dispatch_port",
        fail_create_schedule_dispatch_port,
        raising=False,
    )


def _make_miyabi_debuff(index: str) -> BuffClass:
    debuff = cast(Any, object.__new__(BuffClass))
    debuff.ft = SimpleNamespace(index=index)
    return cast(BuffClass, debuff)


def _make_miyabi_icefire_judge_logic(
    monkeypatch: pytest.MonkeyPatch,
    *,
    enemy_dynamic: object | None = None,
    dynamic_debuff_list: object | None = None,
    call_order: list[object] | None = None,
) -> tuple[_FullCritFixture, _StateSyncBuffProbe, MiyabiCoreSkill_IceFire, list[dict[str, object]]]:
    fixture = _make_full_crit_fixture(name="雅", cid=1091, crit_rate=0.3)
    if enemy_dynamic is not None:
        fixture.enemy.dynamic = enemy_dynamic
    else:
        fixture.enemy.dynamic.dynamic_debuff_list = (
            [] if dynamic_debuff_list is None else dynamic_debuff_list
        )
    active_buff = _StateSyncBuffProbe(
        index="miyabi-icefire",
        tick=72,
        calls=[],
        initial_count=12.0,
    )
    _install_miyabi_icefire_judge_side_effect_guards(monkeypatch, active_buff.sim_instance)
    logic = MiyabiCoreSkill_IceFire(active_buff)
    logic.record = SimpleNamespace(char=fixture.char, enemy=fixture.enemy)
    get_prepared_calls: list[dict[str, object]] = []

    def fake_check_record_module() -> None:
        if call_order is not None:
            call_order.append("check_record_module")

    def fake_get_prepared(**kwargs: object) -> None:
        if call_order is not None:
            call_order.append(("get_prepared", kwargs))
        get_prepared_calls.append(kwargs)

    monkeypatch.setattr(logic, "check_record_module", fake_check_record_module)
    monkeypatch.setattr(logic, "get_prepared", fake_get_prepared)
    return fixture, active_buff, logic, get_prepared_calls


def _full_crit_reader_personal_and_legacy_values(
    fixture: _FullCritFixture,
) -> tuple[float, float, float]:
    context = create_anomaly_attribute_read_context(
        enemy=cast(Any, fixture.enemy),
        active_buff_view=fixture.active_buff_view,
        character=cast(Any, fixture.char),
    )
    reader = CalculatorBuffAttributeReader()
    reader_full = reader.read_full_crit_rate(context)
    reader_personal = reader.read_personal_crit_rate(context)
    old_full = Calculator.RegularMul.cal_crit_rate(
        MultiplierData(
            cast(Any, fixture.enemy),
            fixture.active_buff_view,
            cast(Any, fixture.char),
        )
    )
    return reader_full, reader_personal, old_full


def _assert_aggregation_calls(
    aggregation_calls: list[_AggregationCall],
    fixture: _FullCritFixture,
    *,
    times: int,
) -> None:
    assert (
        aggregation_calls
        == [
            (
                fixture.expected_enabled_buff,
                None,
                fixture.sim_instance,
                fixture.char.NAME,
            )
        ]
        * times
    )


def _make_skill_node(
    *,
    char_name: str,
    cid: int,
    trigger_buff_level: int,
    preload_tick: int = 44,
    hit_offset: int = 1,
    element_type: int = 5,
) -> SkillNode:
    skill = SimpleNamespace(
        skill_tag=f"{cid}_full_crit_probe",
        char_name=char_name,
        hit_times=1,
        labels=None,
        ticks=max(hit_offset + 1, 2),
        tick_list=[hit_offset],
        heavy_attack=False,
        trigger_buff_level=trigger_buff_level,
        element_type=element_type,
    )
    return SkillNode(cast(Any, skill), preload_tick)


@pytest.mark.parametrize(
    ("name", "cid"),
    [
        pytest.param("Cannon User", 1101, id="CannonRotor.py"),
        pytest.param("雅", 1091, id="MiyabiCoreSkill_IceFire.py"),
        pytest.param("啄木鸟普通攻击", 1301, id="WoodpeckerElectroSet4_NA.py"),
        pytest.param("啄木鸟特殊技", 1302, id="WoodpeckerElectroSet4_E_EX.py"),
        pytest.param("啄木鸟连携技", 1303, id="WoodpeckerElectroSet4_CA.py"),
    ],
)
def test_event_adjacent_full_crit_reader_matches_legacy_oracle_per_candidate(
    monkeypatch: pytest.MonkeyPatch,
    name: str,
    cid: int,
) -> None:
    MultiplierData.mul_data_cache.clear()
    fixture = _make_full_crit_fixture(name=name, cid=cid, crit_rate=0.2)
    aggregation_calls = _patch_buff_aggregation(
        monkeypatch,
        {
            "固定暴击率": 0.1,
            "局内暴击率": 0.05,
            "被暴击几率增加": 0.25,
        },
    )

    reader_full, reader_personal, old_full = _full_crit_reader_personal_and_legacy_values(fixture)

    assert reader_full == pytest.approx(old_full)
    assert reader_full == pytest.approx(0.6)
    assert reader_personal == pytest.approx(0.35)
    assert reader_full - reader_personal == pytest.approx(0.25)
    _assert_aggregation_calls(aggregation_calls, fixture, times=3)


@pytest.mark.parametrize(
    ("rng_value", "expected"),
    [
        pytest.param(0.45, True, id="full-crit-success"),
        pytest.param(0.55, False, id="rng-fail"),
    ],
)
def test_cannon_rotor_full_crit_gate_includes_received_bonus_without_publish(
    monkeypatch: pytest.MonkeyPatch,
    rng_value: float,
    expected: bool,
) -> None:
    MultiplierData.mul_data_cache.clear()
    fixture = _make_full_crit_fixture(name="Cannon User", cid=1101, crit_rate=0.2)
    aggregation_calls = _patch_buff_aggregation(
        monkeypatch,
        {
            "固定暴击率": 0.05,
            "局内暴击率": 0.05,
            "被暴击几率增加": 0.2,
        },
    )
    reader_full, reader_personal, old_full = _full_crit_reader_personal_and_legacy_values(fixture)
    assert reader_full == pytest.approx(old_full)
    assert reader_full == pytest.approx(0.5)
    assert reader_personal == pytest.approx(0.3)
    _assert_aggregation_calls(aggregation_calls, fixture, times=3)

    MultiplierData.mul_data_cache.clear()
    aggregation_calls.clear()
    rng = _FakeRng([rng_value])
    fixture.sim_instance.rng_instance = rng
    _install_rng_service_boundary_guards(monkeypatch, fixture.sim_instance)

    def fail_simple_start(*args: object, **kwargs: object) -> None:
        raise AssertionError("CannonRotor judge should not start buff state")

    buff_instance = SimpleNamespace(
        ft=SimpleNamespace(index="cannon-rotor"),
        sim_instance=fixture.sim_instance,
        simple_start=fail_simple_start,
    )
    logic = CannonRotor(buff_instance)
    logic.record = SimpleNamespace(
        char=fixture.char,
        enemy=fixture.enemy,
        dynamic_buff_list=fixture.active_buff_view,
        sub_exist_buff_dict={"cannon-rotor": object()},
    )
    get_prepared_calls: list[dict[str, object]] = []
    monkeypatch.setattr(logic, "check_record_module", lambda: None)
    monkeypatch.setattr(
        logic,
        "get_prepared",
        lambda **kwargs: get_prepared_calls.append(kwargs),
    )
    monkeypatch.setattr(
        "zsim.sim_progress.Buff.BuffXLogic.CannonRotor.find_tick",
        lambda *, sim_instance: sim_instance.tick,
    )

    result = logic.special_judge_logic(
        skill_node=_make_skill_node(
            char_name=fixture.char.NAME,
            cid=fixture.char.CID,
            trigger_buff_level=0,
        )
    )

    assert result is expected
    assert rng.calls == ["random_float"]
    assert get_prepared_calls == [{"equipper": "加农转子", "enemy": 1, "sub_exist_buff_dict": 1}]
    _assert_aggregation_calls(aggregation_calls, fixture, times=1)
    assert fixture.sim_instance.schedule_data.event_list == []


def test_cannon_rotor_full_crit_gate_uses_reader_seam_source() -> None:
    source = inspect.getsource(CannonRotor.special_judge_logic)

    assert "MultiplierData" not in source
    assert "RegularMul" not in source
    assert "cal_crit_rate" not in source
    assert "create_calculator_runtime_read_context_from_sim_instance" in source
    assert "get_calculator_buff_attribute_reader_service" in source
    assert "active_buff_view=self.record.dynamic_buff_list" not in source
    assert "read_full_crit_rate" in source


def test_miyabi_icefire_full_crit_read_keeps_old_count_adjustment_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[Any, ...]] = []
    active_buff = _StateSyncBuffProbe(
        index="miyabi-icefire",
        tick=72,
        calls=calls,
        initial_count=12.0,
        step=3.0,
        maxcount=90.0,
    )
    fixture = _make_full_crit_fixture(
        name="雅",
        cid=1091,
        crit_rate=0.3,
        sim_instance=active_buff.sim_instance,
    )
    aggregation_calls = _patch_buff_aggregation(
        monkeypatch,
        {
            "固定暴击率": 0.1,
            "局内暴击率": 0.05,
            "被暴击几率增加": 0.2,
        },
        call_log=calls,
    )
    reader_full, reader_personal, old_full = _full_crit_reader_personal_and_legacy_values(fixture)
    assert reader_full == pytest.approx(old_full)
    assert reader_full == pytest.approx(0.65)
    assert reader_personal == pytest.approx(0.45)
    _assert_aggregation_calls(aggregation_calls, fixture, times=3)

    MultiplierData.mul_data_cache.clear()
    aggregation_calls.clear()
    calls.clear()
    buff_0 = SimpleNamespace(
        dy=SimpleNamespace(count=12.0),
        ft=SimpleNamespace(maxcount=90.0, step=3.0),
    )
    sub_exist_buff_dict = {active_buff.ft.index: buff_0}
    logic = MiyabiCoreSkill_IceFire(active_buff)
    logic.record = SimpleNamespace(
        char=fixture.char,
        enemy=fixture.enemy,
        dynamic_buff_list=fixture.active_buff_view,
        sub_exist_buff_dict=sub_exist_buff_dict,
    )
    logic.buff_0 = buff_0
    get_prepared_calls: list[dict[str, object]] = []
    monkeypatch.setattr(logic, "check_record_module", lambda: None)
    monkeypatch.setattr(
        logic,
        "get_prepared",
        lambda **kwargs: get_prepared_calls.append(kwargs),
    )
    monkeypatch.setattr(
        JudgeTools,
        "find_tick",
        lambda *, sim_instance: sim_instance.tick,
    )
    monkeypatch.setattr(
        miyabi_module,
        "create_schedule_dispatch_port",
        lambda *, sim_instance: _FailFastDispatchPort(),
        raising=False,
    )

    logic.special_hit_logic()

    assert get_prepared_calls == [{"char_CID": 1091, "enemy": 1, "sub_exist_buff_dict": 1}]
    assert calls == [
        ("simple_start", 72, False, 12.0, buff_0),
        ("dy.count", 15.0),
        ("dy.count", 12.0),
        ("attribute_read",),
        ("dy.count", 65.0),
        ("update_to_buff_0", buff_0, 65.0),
    ]
    _assert_aggregation_calls(aggregation_calls, fixture, times=1)
    assert active_buff.dy.count == pytest.approx(65.0)
    assert buff_0.dy.count == pytest.approx(65.0)
    assert active_buff.sim_instance.schedule_data.event_list == []


@pytest.mark.parametrize(
    ("skill_node", "debuff_indexes", "expected"),
    [
        pytest.param(None, [], False, id="no-skill-node"),
        pytest.param(
            {"element_type": 3},
            [],
            False,
            id="wrong-element",
        ),
        pytest.param(
            {"element_type": 5},
            [],
            True,
            id="no-frostburn-debuff",
        ),
        pytest.param(
            {"element_type": 5},
            ["Buff-角色-雅-核心被动-霜灼"],
            False,
            id="exact-frostburn-debuff",
        ),
        pytest.param(
            {"element_type": 5},
            ["Buff-角色-雅-核心被动-霜灼-近似"],
            True,
            id="near-miss-frostburn-index",
        ),
        pytest.param(
            {"element_type": 5},
            ["Buff-角色-雅-核心被动-霜寒", "Buff-角色-雅-核心被动-霜灼"],
            False,
            id="exact-frostburn-after-nonmatching-buff",
        ),
    ],
)
def test_miyabi_icefire_judge_gates_skill_element_and_debuff(
    monkeypatch: pytest.MonkeyPatch,
    skill_node: dict[str, int] | None,
    debuff_indexes: list[str],
    expected: bool,
) -> None:
    dynamic_debuff_list = [_make_miyabi_debuff(index) for index in debuff_indexes]
    fixture, active_buff, logic, get_prepared_calls = _make_miyabi_icefire_judge_logic(
        monkeypatch,
        dynamic_debuff_list=dynamic_debuff_list,
    )
    node = (
        None
        if skill_node is None
        else _make_skill_node(
            char_name=fixture.char.NAME,
            cid=fixture.char.CID,
            trigger_buff_level=0,
            element_type=skill_node["element_type"],
        )
    )

    assert logic.special_judge_logic(skill_node=node) is expected
    assert get_prepared_calls == [{"char_CID": 1091, "enemy": 1, "action_stack": 1}]
    assert active_buff.sim_instance.schedule_data.event_list == []


def test_miyabi_icefire_judge_pins_current_read_and_iteration_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    call_order: list[object] = []
    mirror = _DebuffMirrorProbe(
        call_order,
        [_make_miyabi_debuff("Buff-角色-雅-核心被动-霜寒")],
    )
    dynamic = _DynamicDebuffMirrorReadProbe(call_order, mirror)
    fixture, active_buff, logic, get_prepared_calls = _make_miyabi_icefire_judge_logic(
        monkeypatch,
        enemy_dynamic=dynamic,
        call_order=call_order,
    )
    node = _SkillNodeReadProbe(
        call_order,
        char_name=fixture.char.NAME,
        element_type=5,
    )

    result = logic.special_judge_logic(skill_node=node)

    assert result is True
    assert get_prepared_calls == [{"char_CID": 1091, "enemy": 1, "action_stack": 1}]
    assert call_order == [
        "check_record_module",
        ("get_prepared", {"char_CID": 1091, "enemy": 1, "action_stack": 1}),
        "dynamic_debuff_list.read",
        "skill_node.char_name",
        "skill_node.skill",
        "skill_node.skill.element_type",
        "dynamic_debuff_list.iter",
    ]
    assert mirror.iterations == 1
    assert active_buff.sim_instance.schedule_data.event_list == []


@pytest.mark.parametrize(
    ("char_name", "element_type"),
    [
        pytest.param("不是雅", 5, id="wrong-character"),
        pytest.param("雅", 3, id="wrong-element"),
    ],
)
def test_miyabi_icefire_judge_wrong_character_or_element_does_not_scan_debuffs(
    monkeypatch: pytest.MonkeyPatch,
    char_name: str,
    element_type: int,
) -> None:
    call_order: list[object] = []
    mirror = _DebuffMirrorProbe(call_order, ["not-a-buff"], fail_on_iter=True)
    dynamic = _DynamicDebuffMirrorReadProbe(call_order, mirror)
    fixture, active_buff, logic, get_prepared_calls = _make_miyabi_icefire_judge_logic(
        monkeypatch,
        enemy_dynamic=dynamic,
        call_order=call_order,
    )
    node = _SkillNodeReadProbe(
        call_order,
        char_name=char_name,
        element_type=element_type,
    )

    result = logic.special_judge_logic(skill_node=node)

    assert result is False
    assert get_prepared_calls == [{"char_CID": 1091, "enemy": 1, "action_stack": 1}]
    assert mirror.iterations == 0
    assert "dynamic_debuff_list.iter" not in call_order
    if char_name != fixture.char.NAME:
        assert "skill_node.skill" not in call_order
    assert active_buff.sim_instance.schedule_data.event_list == []


@pytest.mark.parametrize(
    ("skill_node", "missing_attribute"),
    [
        pytest.param(object(), "char_name", id="missing-char-name"),
        pytest.param(SimpleNamespace(char_name="雅"), "skill", id="missing-skill"),
    ],
)
def test_miyabi_icefire_judge_preserves_incompatible_skill_node_attribute_error(
    monkeypatch: pytest.MonkeyPatch,
    skill_node: object,
    missing_attribute: str,
) -> None:
    call_order: list[object] = []
    mirror = _DebuffMirrorProbe(call_order, ["not-a-buff"], fail_on_iter=True)
    dynamic = _DynamicDebuffMirrorReadProbe(call_order, mirror)
    _, active_buff, logic, get_prepared_calls = _make_miyabi_icefire_judge_logic(
        monkeypatch,
        enemy_dynamic=dynamic,
        call_order=call_order,
    )

    with pytest.raises(AttributeError, match=missing_attribute):
        logic.special_judge_logic(skill_node=skill_node)

    assert get_prepared_calls == [{"char_CID": 1091, "enemy": 1, "action_stack": 1}]
    assert mirror.iterations == 0
    assert "dynamic_debuff_list.iter" not in call_order
    assert active_buff.sim_instance.schedule_data.event_list == []


def test_miyabi_icefire_check_record_module_preserves_old_buff_and_record_identity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    active_buff = _StateSyncBuffProbe(
        index="miyabi-icefire",
        tick=72,
        calls=[],
        initial_count=12.0,
    )
    logic = MiyabiCoreSkill_IceFire(active_buff)
    buff_0 = SimpleNamespace(history=SimpleNamespace(record=None))

    class _PreparationContext:
        def find_sub_exist_buff_dict(self, owner_name: str) -> dict[str, object]:
            assert owner_name == "雅"
            return {active_buff.ft.index: buff_0}

    monkeypatch.setattr(
        miyabi_module,
        "build_preparation_context_from_buff",
        lambda buff_instance: _PreparationContext(),
    )

    logic.check_record_module()

    assert logic.buff_0 is buff_0
    assert logic.record is buff_0.history.record
    assert isinstance(logic.record, MiyabiCoreSkillIF)
    first_record = logic.record

    logic.check_record_module()

    assert logic.buff_0 is buff_0
    assert logic.record is first_record
    assert buff_0.history.record is first_record
    assert active_buff.sim_instance.schedule_data.event_list == []


def test_miyabi_icefire_judge_rejects_wrong_character_before_debuff_scan(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture, active_buff, logic, get_prepared_calls = _make_miyabi_icefire_judge_logic(
        monkeypatch,
        dynamic_debuff_list=["not-a-buff"],
    )

    result = logic.special_judge_logic(
        skill_node=_make_skill_node(
            char_name="不是雅",
            cid=1091,
            trigger_buff_level=0,
            element_type=5,
        )
    )

    assert result is False
    assert get_prepared_calls == [{"char_CID": 1091, "enemy": 1, "action_stack": 1}]
    assert active_buff.sim_instance.schedule_data.event_list == []


def test_miyabi_icefire_judge_raises_for_non_buff_debuff(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture, active_buff, logic, get_prepared_calls = _make_miyabi_icefire_judge_logic(
        monkeypatch,
        dynamic_debuff_list=["not-a-buff"],
    )

    with pytest.raises(TypeError, match="不是Buff类"):
        logic.special_judge_logic(
            skill_node=_make_skill_node(
                char_name=fixture.char.NAME,
                cid=fixture.char.CID,
                trigger_buff_level=0,
                element_type=5,
            )
        )

    assert get_prepared_calls == [{"char_CID": 1091, "enemy": 1, "action_stack": 1}]
    assert active_buff.sim_instance.schedule_data.event_list == []


def test_miyabi_icefire_full_crit_count_caps_at_buff_maxcount(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[Any, ...]] = []
    active_buff = _StateSyncBuffProbe(
        index="miyabi-icefire",
        tick=73,
        calls=calls,
        initial_count=12.0,
        step=3.0,
        maxcount=70.0,
    )
    fixture = _make_full_crit_fixture(
        name="雅",
        cid=1091,
        crit_rate=0.35,
        sim_instance=active_buff.sim_instance,
    )
    aggregation_calls = _patch_buff_aggregation(
        monkeypatch,
        {
            "固定暴击率": 0.2,
            "局内暴击率": 0.15,
            "被暴击几率增加": 0.4,
        },
        call_log=calls,
    )
    reader_full, reader_personal, old_full = _full_crit_reader_personal_and_legacy_values(fixture)
    assert reader_full == pytest.approx(old_full)
    assert reader_full == pytest.approx(1.1)
    assert reader_personal == pytest.approx(0.7)
    _assert_aggregation_calls(aggregation_calls, fixture, times=3)

    MultiplierData.mul_data_cache.clear()
    aggregation_calls.clear()
    calls.clear()
    buff_0 = SimpleNamespace(
        dy=SimpleNamespace(count=12.0),
        ft=SimpleNamespace(maxcount=70.0, step=3.0),
    )
    logic = MiyabiCoreSkill_IceFire(active_buff)
    logic.record = SimpleNamespace(
        char=fixture.char,
        enemy=fixture.enemy,
        dynamic_buff_list=fixture.active_buff_view,
        sub_exist_buff_dict={active_buff.ft.index: buff_0},
    )
    logic.buff_0 = buff_0
    monkeypatch.setattr(logic, "check_record_module", lambda: None)
    monkeypatch.setattr(logic, "get_prepared", lambda **kwargs: None)
    monkeypatch.setattr(
        JudgeTools,
        "find_tick",
        lambda *, sim_instance: sim_instance.tick,
    )

    logic.special_hit_logic()

    assert calls == [
        ("simple_start", 73, False, 12.0, buff_0),
        ("dy.count", 15.0),
        ("dy.count", 12.0),
        ("attribute_read",),
        ("dy.count", 70.0),
        ("update_to_buff_0", buff_0, 70.0),
    ]
    _assert_aggregation_calls(aggregation_calls, fixture, times=1)
    assert active_buff.dy.count == pytest.approx(70.0)
    assert buff_0.dy.count == pytest.approx(70.0)
    assert active_buff.sim_instance.schedule_data.event_list == []


def test_miyabi_icefire_full_crit_hit_uses_reader_seam_source() -> None:
    source = inspect.getsource(MiyabiCoreSkill_IceFire.special_hit_logic)

    assert "MultiplierData" not in source
    assert "RegularMul" not in source
    assert "cal_crit_rate" not in source
    assert "create_calculator_runtime_read_context_from_sim_instance" in source
    assert "get_calculator_buff_attribute_reader_service" in source
    assert "active_buff_view=self.record.dynamic_buff_list" not in source
    assert "read_full_crit_rate" in source


@pytest.mark.parametrize("variant", _WOODPECKER_VARIANTS)
@pytest.mark.parametrize(
    ("rng_value", "expected"),
    [
        pytest.param(0.45, True, id="full-crit-success"),
        pytest.param(0.55, False, id="rng-fail"),
    ],
)
def test_woodpecker_full_crit_gate_pins_rng_and_trigger_level(
    monkeypatch: pytest.MonkeyPatch,
    variant: _WoodpeckerVariant,
    rng_value: float,
    expected: bool,
) -> None:
    MultiplierData.mul_data_cache.clear()
    fixture = _make_full_crit_fixture(name="啄木鸟测试", cid=1301, crit_rate=0.2)
    aggregation_calls = _patch_buff_aggregation(
        monkeypatch,
        {
            "固定暴击率": 0.05,
            "局内暴击率": 0.05,
            "被暴击几率增加": 0.2,
        },
    )
    reader_full, reader_personal, old_full = _full_crit_reader_personal_and_legacy_values(fixture)
    assert reader_full == pytest.approx(old_full)
    assert reader_full == pytest.approx(0.5)
    assert reader_personal == pytest.approx(0.3)
    _assert_aggregation_calls(aggregation_calls, fixture, times=3)

    MultiplierData.mul_data_cache.clear()
    aggregation_calls.clear()
    rng = _FakeRng([rng_value])
    fixture.sim_instance.rng_instance = rng
    _install_rng_service_boundary_guards(monkeypatch, fixture.sim_instance)

    def fail_simple_start(*args: object, **kwargs: object) -> None:
        raise AssertionError("Woodpecker full crit gate should not start buff state")

    buff_instance = SimpleNamespace(
        ft=SimpleNamespace(index="woodpecker-electro"),
        sim_instance=fixture.sim_instance,
        simple_start=fail_simple_start,
    )
    logic = variant.logic_type(buff_instance)
    logic.record = SimpleNamespace(
        char=fixture.char,
        enemy=fixture.enemy,
        dynamic_buff_list=fixture.active_buff_view,
        action_stack=[],
    )
    get_prepared_calls: list[dict[str, object]] = []
    monkeypatch.setattr(logic, "check_record_module", lambda: None)
    monkeypatch.setattr(
        logic,
        "get_prepared",
        lambda **kwargs: get_prepared_calls.append(kwargs),
    )

    result = logic.special_judge_logic(
        skill_node=_make_skill_node(
            char_name=fixture.char.NAME,
            cid=fixture.char.CID,
            trigger_buff_level=variant.trigger_level,
        )
    )

    assert result is expected
    assert rng.calls == ["random_float"]
    assert get_prepared_calls == [{"equipper": "啄木鸟电音", "enemy": 1, "action_stack": 1}]
    _assert_aggregation_calls(aggregation_calls, fixture, times=1)
    assert fixture.sim_instance.schedule_data.event_list == []


def test_woodpecker_ca_full_crit_gate_reads_before_rng(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    MultiplierData.mul_data_cache.clear()
    fixture = _make_full_crit_fixture(name="啄木鸟测试", cid=1301, crit_rate=0.2)
    calls: list[tuple[Any, ...]] = []
    aggregation_calls = _patch_buff_aggregation(
        monkeypatch,
        {
            "固定暴击率": 0.05,
            "局内暴击率": 0.05,
            "被暴击几率增加": 0.2,
        },
        call_log=calls,
    )

    def random_float() -> float:
        calls.append(("random_float",))
        return 0.45

    def fail_simple_start(*args: object, **kwargs: object) -> None:
        raise AssertionError("Woodpecker CA full crit gate should not start state")

    fixture.sim_instance.rng_instance = SimpleNamespace(random_float=random_float)
    _install_rng_service_boundary_guards(monkeypatch, fixture.sim_instance)
    buff_instance = SimpleNamespace(
        ft=SimpleNamespace(index="woodpecker-electro"),
        sim_instance=fixture.sim_instance,
        simple_start=fail_simple_start,
    )
    logic = WoodpeckerElectroSet4_CA(buff_instance)
    logic.record = SimpleNamespace(
        char=fixture.char,
        enemy=fixture.enemy,
        dynamic_buff_list=fixture.active_buff_view,
        action_stack=[],
    )
    monkeypatch.setattr(logic, "check_record_module", lambda: None)
    monkeypatch.setattr(logic, "get_prepared", lambda **kwargs: None)

    result = logic.special_judge_logic(
        skill_node=_make_skill_node(
            char_name=fixture.char.NAME,
            cid=fixture.char.CID,
            trigger_buff_level=4,
        )
    )

    assert result is True
    assert calls == [("attribute_read",), ("random_float",)]
    _assert_aggregation_calls(aggregation_calls, fixture, times=1)
    assert fixture.sim_instance.schedule_data.event_list == []


@pytest.mark.parametrize("variant", _WOODPECKER_VARIANTS)
def test_woodpecker_full_crit_gate_skips_rng_and_state_sync_on_wrong_actor(
    monkeypatch: pytest.MonkeyPatch,
    variant: _WoodpeckerVariant,
) -> None:
    MultiplierData.mul_data_cache.clear()
    fixture = _make_full_crit_fixture(name="啄木鸟测试", cid=1301, crit_rate=0.2)
    aggregation_calls = _patch_buff_aggregation(
        monkeypatch,
        {
            "固定暴击率": 0.05,
            "局内暴击率": 0.05,
            "被暴击几率增加": 0.2,
        },
    )
    rng = _FakeRng([0.0])
    fixture.sim_instance.rng_instance = rng

    def fail_simple_start(*args: object, **kwargs: object) -> None:
        raise AssertionError("Woodpecker wrong actor branch should not start state")

    buff_instance = SimpleNamespace(
        ft=SimpleNamespace(index="woodpecker-electro"),
        sim_instance=fixture.sim_instance,
        simple_start=fail_simple_start,
    )
    logic = variant.logic_type(buff_instance)
    logic.record = SimpleNamespace(
        char=fixture.char,
        enemy=fixture.enemy,
        dynamic_buff_list=fixture.active_buff_view,
        action_stack=[],
    )
    get_prepared_calls: list[dict[str, object]] = []
    monkeypatch.setattr(logic, "check_record_module", lambda: None)
    monkeypatch.setattr(
        logic,
        "get_prepared",
        lambda **kwargs: get_prepared_calls.append(kwargs),
    )

    result = logic.special_judge_logic(
        skill_node=_make_skill_node(
            char_name=fixture.char.NAME,
            cid=9999,
            trigger_buff_level=variant.trigger_level,
        )
    )

    assert result is False
    assert rng.calls == []
    assert aggregation_calls == []
    assert get_prepared_calls == [{"equipper": "啄木鸟电音", "enemy": 1, "action_stack": 1}]
    assert fixture.sim_instance.schedule_data.event_list == []


@pytest.mark.parametrize(
    ("logic_type", "variant_name"),
    [
        pytest.param(
            WoodpeckerElectroSet4_NA,
            "NA",
            id="WoodpeckerElectroSet4_NA",
        ),
        pytest.param(
            WoodpeckerElectroSet4_E_EX,
            "E_EX",
            id="WoodpeckerElectroSet4_E_EX",
        ),
        pytest.param(
            WoodpeckerElectroSet4_CA,
            "CA",
            id="WoodpeckerElectroSet4_CA",
        ),
    ],
)
def test_migrated_woodpecker_full_crit_gate_skips_rng_and_state_sync_without_skill_node(
    monkeypatch: pytest.MonkeyPatch,
    logic_type: type[Any],
    variant_name: str,
) -> None:
    MultiplierData.mul_data_cache.clear()
    fixture = _make_full_crit_fixture(name="啄木鸟测试", cid=1301, crit_rate=0.2)
    aggregation_calls = _patch_buff_aggregation(
        monkeypatch,
        {
            "固定暴击率": 0.05,
            "局内暴击率": 0.05,
            "被暴击几率增加": 0.2,
        },
    )
    rng = _FakeRng([0.0])
    fixture.sim_instance.rng_instance = rng

    def fail_simple_start(*args: object, **kwargs: object) -> None:
        raise AssertionError(
            f"Woodpecker {variant_name} no SkillNode branch should not start state"
        )

    buff_instance = SimpleNamespace(
        ft=SimpleNamespace(index="woodpecker-electro"),
        sim_instance=fixture.sim_instance,
        simple_start=fail_simple_start,
    )
    logic = logic_type(buff_instance)
    logic.record = SimpleNamespace(
        char=fixture.char,
        enemy=fixture.enemy,
        dynamic_buff_list=fixture.active_buff_view,
        action_stack=[],
    )
    get_prepared_calls: list[dict[str, object]] = []
    monkeypatch.setattr(logic, "check_record_module", lambda: None)
    monkeypatch.setattr(
        logic,
        "get_prepared",
        lambda **kwargs: get_prepared_calls.append(kwargs),
    )

    result = logic.special_judge_logic(skill_node=None)

    assert result is False
    assert rng.calls == []
    assert aggregation_calls == []
    assert get_prepared_calls == [{"equipper": "啄木鸟电音", "enemy": 1, "action_stack": 1}]
    assert fixture.sim_instance.schedule_data.event_list == []


def test_woodpecker_na_full_crit_gate_uses_reader_seam_source() -> None:
    module_source = inspect.getsource(sys.modules[WoodpeckerElectroSet4_NA.__module__])
    method_source = inspect.getsource(WoodpeckerElectroSet4_NA.special_judge_logic)

    assert "MultiplierData" not in module_source
    assert "RegularMul" not in module_source
    assert "cal_crit_rate" not in module_source
    assert "create_calculator_runtime_read_context_from_sim_instance" in method_source
    assert "get_calculator_buff_attribute_reader_service" in method_source
    assert "active_buff_view=self.record.dynamic_buff_list" not in method_source
    assert "read_full_crit_rate" in method_source


def test_woodpecker_e_ex_full_crit_gate_uses_reader_seam_source() -> None:
    module_source = inspect.getsource(sys.modules[WoodpeckerElectroSet4_E_EX.__module__])
    method_source = inspect.getsource(WoodpeckerElectroSet4_E_EX.special_judge_logic)

    assert "MultiplierData" not in module_source
    assert "RegularMul" not in module_source
    assert "cal_crit_rate" not in module_source
    assert "create_calculator_runtime_read_context_from_sim_instance" in method_source
    assert "get_calculator_buff_attribute_reader_service" in method_source
    assert "active_buff_view=self.record.dynamic_buff_list" not in method_source
    assert "read_full_crit_rate" in method_source


def test_woodpecker_ca_full_crit_gate_uses_reader_seam_source() -> None:
    module_source = inspect.getsource(sys.modules[WoodpeckerElectroSet4_CA.__module__])
    method_source = inspect.getsource(WoodpeckerElectroSet4_CA.special_judge_logic)

    assert "MultiplierData" not in module_source
    assert "RegularMul" not in module_source
    assert "cal_crit_rate" not in module_source
    assert "create_calculator_runtime_read_context_from_sim_instance" in method_source
    assert "get_calculator_buff_attribute_reader_service" in method_source
    assert "active_buff_view=self.record.dynamic_buff_list" not in method_source
    assert "read_full_crit_rate" in method_source


@pytest.mark.parametrize(
    "logic_type",
    [
        pytest.param(CannonRotor, id="CannonRotor"),
        pytest.param(WoodpeckerElectroSet4_NA, id="WoodpeckerElectroSet4_NA"),
        pytest.param(WoodpeckerElectroSet4_E_EX, id="WoodpeckerElectroSet4_E_EX"),
        pytest.param(WoodpeckerElectroSet4_CA, id="WoodpeckerElectroSet4_CA"),
    ],
)
def test_rng_service_full_crit_gate_source_stays_read_only(
    logic_type: type[Any],
) -> None:
    source = inspect.getsource(logic_type.special_judge_logic)

    assert "create_schedule_dispatch_port" not in source
    assert "publish_scheduled" not in source
    assert "event_list" not in source
    assert "broadcast_event" not in source
    assert "change_process_state" not in source
    assert "RuntimeCommandPort" not in source
    assert "create_runtime_command_port" not in source
    assert "LegacyBuffRuntimeFacade" not in source
    assert "create_legacy_buff_runtime_facade" not in source
    assert "BuffRuntimeReadPort" not in source
    assert "create_buff_runtime_read_port" not in source
