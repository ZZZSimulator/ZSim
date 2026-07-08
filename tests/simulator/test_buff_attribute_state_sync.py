from __future__ import annotations

from dataclasses import dataclass
from math import floor
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Sequence, cast

import pytest

import zsim.sim_progress.calculation.calculator as calculator_module
from zsim.sim_progress.Buff.BuffXLogic import (
    LighterAdditionalAbility_IceFireBonus as lighter_module,
)
from zsim.sim_progress.Buff.BuffXLogic import (
    QingYiAdditionalAbilityStunConvertToATK as qingyi_module,
)
from zsim.sim_progress.Buff.BuffXLogic import (
    Soldier0AnbyCoreSkillCritDMGBonus as soldier0_anby_module,
)
from zsim.sim_progress.Buff.BuffXLogic import TriggerAdditionalAbilityStunBonus as trigger_module
from zsim.sim_progress.Buff.BuffXLogic import (
    YuzuhaAdditionalAbilityAnomalyDmgBonus as yuzuha_dmg_module,
)
from zsim.sim_progress.Buff.BuffXLogic.AliceAdditionalAbilityApBonus import (
    AliceAdditionalAbilityApBonus,
)
from zsim.sim_progress.Buff.BuffXLogic.JaneCinema1APTransToDmgBonus import (
    JaneCinema1APTransToDmgBonus,
)
from zsim.sim_progress.Buff.BuffXLogic.JaneCoreSkillStrikeCritRateBonus import (
    JaneCoreSkillStrikeCritRateBonus,
)
from zsim.sim_progress.Buff.BuffXLogic.JanePassionStateAPTransToATK import (
    JanePassionStateAPTransToATK,
)
from zsim.sim_progress.Buff.BuffXLogic.LighterAdditionalAbility_IceFireBonus import (
    LighterExtraSkill_IceFireBonus,
)
from zsim.sim_progress.Buff.BuffXLogic.QingYiAdditionalAbilityStunConvertToATK import (
    QingYiAdditionalAbilityStunConvertToATK,
)
from zsim.sim_progress.Buff.BuffXLogic.Soldier0AnbyCoreSkillCritDMGBonus import (
    Soldier0AnbyCoreSkillCritDMGBonus,
)
from zsim.sim_progress.Buff.BuffXLogic.TriggerAdditionalAbilityStunBonus import (
    TriggerAdditionalAbilityStunBonus,
)
from zsim.sim_progress.Buff.BuffXLogic.YuzuhaAdditionalAbilityAnomalyBuildupBonus import (
    YuzuhaAdditionalAbilityAnomalyBuildupBonus,
)
from zsim.sim_progress.Buff.BuffXLogic.YuzuhaAdditionalAbilityAnomalyDmgBonus import (
    YuzuhaAdditionalAbilityAnomalyDmgBonus,
)
from zsim.sim_progress.calculation.calculator import Calculator, MultiplierData
from zsim.sim_progress.ScheduledEvent.buff_runtime import BuffRuntimeState

_AggregationCall = tuple[tuple[object, ...], object | None, object, str | None]


class _DynamicCountRecorder:
    def __init__(
        self,
        calls: list[tuple[Any, ...]],
        initial_count: float,
        *,
        label: str = "dy.count",
    ) -> None:
        self._calls = calls
        self._count = initial_count
        self._label = label

    @property
    def count(self) -> float:
        return self._count

    @count.setter
    def count(self, value: float) -> None:
        self._calls.append((self._label, value))
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
        self._calls = calls
        self.sim_instance = SimpleNamespace(
            tick=tick,
            schedule_data=SimpleNamespace(change_process_state=self._change_process_state),
        )

    def _change_process_state(self) -> None:
        self._calls.append(("change_process_state",))

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


def _assert_final_count_writeback_order(
    calls: Sequence[tuple[Any, ...]],
    *,
    buff_0: object,
    expected_count: float,
) -> None:
    final_count_indexes = [
        index
        for index, call in enumerate(calls)
        if len(call) == 2 and call[0] == "dy.count" and call[1] == pytest.approx(expected_count)
    ]
    update_indexes = [index for index, call in enumerate(calls) if call[0] == "update_to_buff_0"]

    assert final_count_indexes
    assert update_indexes == [final_count_indexes[-1] + 1]
    update_call = calls[update_indexes[0]]
    assert update_call[1] is buff_0
    assert update_call[2] == pytest.approx(expected_count)


@dataclass(frozen=True)
class _AliceStateSyncCase:
    logic: Any
    active_buff: _StateSyncBuffProbe
    buff_0: Any
    calls: list[tuple[Any, ...]]
    get_prepared_calls: list[dict[str, object]]
    aggregation_calls: list[_AggregationCall]
    expected_enabled_buff: tuple[object, ...]
    expected_old_count: float | None


@dataclass(frozen=True)
class _YuzuhaStateSyncCase:
    logic: Any
    active_buff: _StateSyncBuffProbe
    buff_0: Any
    calls: list[tuple[Any, ...]]
    get_prepared_calls: list[dict[str, object]]
    aggregation_calls: list[_AggregationCall]
    expected_enabled_buff: tuple[object, ...]
    expected_old_count: float | None
    expected_cinema_1_ratio: float


@dataclass(frozen=True)
class _JaneCinema1StateSyncCase:
    logic: Any
    active_buff: _StateSyncBuffProbe
    buff_0: Any
    calls: list[tuple[Any, ...]]
    get_prepared_calls: list[dict[str, object]]
    aggregation_calls: list[_AggregationCall]
    expected_enabled_buff: tuple[object, ...]
    expected_old_count: float
    initial_count: float


@dataclass(frozen=True)
class _JaneCoreSkillCritRateStateSyncCase:
    logic: Any
    active_buff: _StateSyncBuffProbe
    buff_0: Any
    calls: list[tuple[Any, ...]]
    get_prepared_calls: list[dict[str, object]]
    aggregation_calls: list[_AggregationCall]
    expected_enabled_buff: tuple[object, ...]
    expected_old_count: float
    initial_count: float


@dataclass(frozen=True)
class _JanePassionStateSyncCase:
    logic: Any
    active_buff: _StateSyncBuffProbe
    buff_0: Any
    calls: list[tuple[Any, ...]]
    get_prepared_calls: list[dict[str, object]]
    aggregation_calls: list[_AggregationCall]
    expected_enabled_buff: tuple[object, ...]
    expected_old_count: float
    initial_count: float


@dataclass(frozen=True)
class _P2BStateSyncCase:
    logic: Any
    active_buff: _StateSyncBuffProbe
    buff_0: Any
    calls: list[tuple[Any, ...]]
    get_prepared_calls: list[dict[str, object]]
    aggregation_calls: list[_AggregationCall]
    expected_enabled_buff: tuple[object, ...]
    expected_old_count: float
    initial_count: float
    expected_real_count: float | None = None


def _make_alice_character(*, am: float) -> SimpleNamespace:
    statement = SimpleNamespace(statement={"AM": am}, AM=am)
    return SimpleNamespace(NAME="Alice", CID=1401, level=60, statement=statement)


def _make_yuzuha_character(*, am: float, cinema: int) -> SimpleNamespace:
    statement = SimpleNamespace(statement={"AM": am}, AM=am)
    return SimpleNamespace(NAME="Yuzuha", CID=1411, cinema=cinema, level=60, statement=statement)


def _make_jane_character(*, ap: float) -> SimpleNamespace:
    statement = SimpleNamespace(statement={"AP": ap}, AP=ap)
    return SimpleNamespace(NAME="Jane", CID=1261, level=60, statement=statement)


def _make_p2b_character(
    *,
    name: str,
    cid: int,
    imp: float = 0.0,
    crit_rate: float = 0.0,
    crit_damage: float = 0.0,
) -> SimpleNamespace:
    statement_values = {
        "AM": 0.0,
        "AP": 0.0,
        "IMP": imp,
        "CRIT_rate": crit_rate,
        "CRIT_damage": crit_damage,
    }
    statement = SimpleNamespace(statement=statement_values)
    for attr_name, value in statement_values.items():
        setattr(statement, attr_name, value)
    return SimpleNamespace(NAME=name, CID=cid, level=60, statement=statement)


def _make_enemy(
    *,
    sim_instance: object,
    enemy_debuffs: Sequence[object],
) -> SimpleNamespace:
    return SimpleNamespace(
        dynamic=SimpleNamespace(
            dynamic_debuff_list=list(enemy_debuffs),
            dynamic_dot_list=[],
        ),
        sim_instance=sim_instance,
    )


def _attach_buff_runtime_state(
    *,
    sim_instance: object,
    dynamic_buff_list: dict[str, list[object]],
    enemy: SimpleNamespace,
) -> None:
    cast(Any, sim_instance).buff_runtime_state = BuffRuntimeState(
        template_registry={},
        pending_queue={},
        active_store=dynamic_buff_list,
        enemy_mirror=enemy.dynamic.dynamic_debuff_list,
    )


def _patch_buff_aggregation(
    monkeypatch: pytest.MonkeyPatch,
    dynamic_statement: dict[str, float],
    *,
    call_log: list[tuple[Any, ...]] | None = None,
    call_label: str = "attribute_read",
) -> list[_AggregationCall]:
    aggregation_calls: list[_AggregationCall] = []

    def fake_cal_buff_total_bonus(
        *,
        enabled_buff: tuple[object, ...],
        judge_obj: object | None,
        sim_instance: object,
        char_name: str | None,
    ) -> dict[str, float]:
        if call_log is not None:
            call_log.append((call_label,))
        aggregation_calls.append((enabled_buff, judge_obj, sim_instance, char_name))
        return dict(dynamic_statement)

    monkeypatch.setattr(
        calculator_module,
        "cal_buff_total_bonus",
        fake_cal_buff_total_bonus,
    )
    return aggregation_calls


def _old_alice_count(
    *,
    enemy: SimpleNamespace,
    dynamic_buff_list: dict[str, list[object]],
    char: SimpleNamespace,
    trans_ratio: float,
) -> float | None:
    MultiplierData.mul_data_cache.clear()
    mul_data = MultiplierData(
        cast(Any, enemy),
        dynamic_buff_list,
        cast(Any, char),
    )
    am = Calculator.AnomalyMul.cal_am(mul_data)
    if am < 140:
        return None
    return float((am - 140) * trans_ratio)


def _old_yuzuha_additional_ability_count(
    *,
    enemy: SimpleNamespace,
    dynamic_buff_list: dict[str, list[object]],
    char: SimpleNamespace,
    cinema_1_ratio: float,
) -> float | None:
    MultiplierData.mul_data_cache.clear()
    mul_data = MultiplierData(
        cast(Any, enemy),
        dynamic_buff_list,
        cast(Any, char),
    )
    am = Calculator.AnomalyMul.cal_am(mul_data)
    if am < 100:
        return None
    return float(min(am - 100, 100) * cinema_1_ratio)


def _old_jane_cinema1_damage_count(
    *,
    enemy: SimpleNamespace,
    dynamic_buff_list: dict[str, list[object]],
    char: SimpleNamespace,
    maxcount: float,
) -> float:
    MultiplierData.mul_data_cache.clear()
    mul_data = MultiplierData(
        cast(Any, enemy),
        dynamic_buff_list,
        cast(Any, char),
    )
    ap = Calculator.AnomalyMul.cal_ap(mul_data)
    return float(min(ap * 0.1, maxcount))


def _old_jane_core_skill_crit_rate_count(
    *,
    enemy: SimpleNamespace,
    dynamic_buff_list: dict[str, list[object]],
    char: SimpleNamespace,
) -> float:
    MultiplierData.mul_data_cache.clear()
    mul_data = MultiplierData(
        cast(Any, enemy),
        dynamic_buff_list,
        cast(Any, char),
    )
    ap = Calculator.AnomalyMul.cal_ap(mul_data)
    return float(min(40 + ap * 0.16, 100))


def _old_jane_passion_state_atk_count(
    *,
    enemy: SimpleNamespace,
    dynamic_buff_list: dict[str, list[object]],
    char: SimpleNamespace,
) -> float:
    MultiplierData.mul_data_cache.clear()
    mul_data = MultiplierData(
        cast(Any, enemy),
        dynamic_buff_list,
        cast(Any, char),
    )
    ap = Calculator.AnomalyMul.cal_ap(mul_data)
    return float(floor(max(ap - 120, 0)))


def _old_impact_value(
    *,
    enemy: SimpleNamespace,
    dynamic_buff_list: dict[str, list[object]],
    char: SimpleNamespace,
) -> float:
    MultiplierData.mul_data_cache.clear()
    mul_data = MultiplierData(
        cast(Any, enemy),
        dynamic_buff_list,
        cast(Any, char),
    )
    return float(Calculator.StunMul.cal_imp(mul_data))


def _old_personal_crit_rate_value(
    *,
    enemy: SimpleNamespace,
    dynamic_buff_list: dict[str, list[object]],
    char: SimpleNamespace,
) -> float:
    MultiplierData.mul_data_cache.clear()
    mul_data = MultiplierData(
        cast(Any, enemy),
        dynamic_buff_list,
        cast(Any, char),
    )
    return float(Calculator.RegularMul.cal_personal_crit_rate(mul_data))


def _old_personal_crit_damage_value(
    *,
    enemy: SimpleNamespace,
    dynamic_buff_list: dict[str, list[object]],
    char: SimpleNamespace,
) -> float:
    MultiplierData.mul_data_cache.clear()
    mul_data = MultiplierData(
        cast(Any, enemy),
        dynamic_buff_list,
        cast(Any, char),
    )
    return float(Calculator.RegularMul.cal_personal_crit_dmg(mul_data))


def _old_lighter_count(
    *,
    enemy: SimpleNamespace,
    dynamic_buff_list: dict[str, list[object]],
    char: SimpleNamespace,
    initial_real_count: float,
    step: float,
) -> tuple[float, float]:
    real_count = min(initial_real_count + step, 100)
    stun_value = _old_impact_value(
        enemy=enemy,
        dynamic_buff_list=dynamic_buff_list,
        char=char,
    )
    fake_count_delta = max((stun_value - 170) / 10, 0)
    count = min(real_count + real_count / 5 * fake_count_delta, 300)
    return float(count), float(real_count)


def _old_qingyi_count(
    *,
    enemy: SimpleNamespace,
    dynamic_buff_list: dict[str, list[object]],
    char: SimpleNamespace,
    maxcount: float,
) -> float:
    stun_value = _old_impact_value(
        enemy=enemy,
        dynamic_buff_list=dynamic_buff_list,
        char=char,
    )
    return float(min((stun_value - 120) * 6, maxcount))


def _old_trigger_personal_crit_rate_count(
    *,
    enemy: SimpleNamespace,
    dynamic_buff_list: dict[str, list[object]],
    char: SimpleNamespace,
) -> float:
    crit_rate = _old_personal_crit_rate_value(
        enemy=enemy,
        dynamic_buff_list=dynamic_buff_list,
        char=char,
    )
    return float(min(max(crit_rate - 0.4, 0) / 0.01 * 1.5, 75))


def _old_soldier0_anby_personal_crit_damage_count(
    *,
    enemy: SimpleNamespace,
    dynamic_buff_list: dict[str, list[object]],
    char: SimpleNamespace,
) -> float:
    crit_damage = _old_personal_crit_damage_value(
        enemy=enemy,
        dynamic_buff_list=dynamic_buff_list,
        char=char,
    )
    return float(crit_damage * 0.3 * 100)


def _make_alice_state_sync_case(
    monkeypatch: pytest.MonkeyPatch,
    *,
    static_am: float,
    field_am: float = 0.0,
    flat_am: float = 0.0,
    initial_count: float = 123.0,
    maxcount: float = 999.0,
) -> _AliceStateSyncCase:
    calls: list[tuple[Any, ...]] = []
    active_buff = _StateSyncBuffProbe(
        index="alice-additional-ability-ap",
        tick=600,
        calls=calls,
        initial_count=initial_count,
        maxcount=maxcount,
    )
    char_buff = object()
    enemy_debuff = object()
    char = _make_alice_character(am=static_am)
    enemy = _make_enemy(
        sim_instance=active_buff.sim_instance,
        enemy_debuffs=(enemy_debuff,),
    )
    dynamic_buff_list = {char.NAME: [char_buff]}
    _attach_buff_runtime_state(
        sim_instance=active_buff.sim_instance,
        dynamic_buff_list=dynamic_buff_list,
        enemy=enemy,
    )
    aggregation_calls = _patch_buff_aggregation(
        monkeypatch,
        {
            "局内异常掌控": field_am,
            "固定异常掌控": flat_am,
        },
    )
    buff_0 = SimpleNamespace(dy=SimpleNamespace(count=initial_count))
    sub_exist_buff_dict = {active_buff.ft.index: buff_0}
    trans_ratio = 1.6

    logic = cast(
        Any,
        AliceAdditionalAbilityApBonus.__new__(AliceAdditionalAbilityApBonus),
    )
    logic.buff_instance = active_buff
    logic.buff_0 = buff_0
    logic.record = SimpleNamespace(
        enemy=enemy,
        dynamic_buff_list=dynamic_buff_list,
        char=char,
        sub_exist_buff_dict=sub_exist_buff_dict,
        trans_ratio=trans_ratio,
    )
    logic.check_record_module = lambda: None

    get_prepared_calls: list[dict[str, object]] = []
    logic.get_prepared = lambda **kwargs: get_prepared_calls.append(kwargs)
    expected_old_count = _old_alice_count(
        enemy=enemy,
        dynamic_buff_list=dynamic_buff_list,
        char=char,
        trans_ratio=trans_ratio,
    )
    return _AliceStateSyncCase(
        logic=logic,
        active_buff=active_buff,
        buff_0=buff_0,
        calls=calls,
        get_prepared_calls=get_prepared_calls,
        aggregation_calls=aggregation_calls,
        expected_enabled_buff=(char_buff, enemy_debuff),
        expected_old_count=expected_old_count,
    )


def _make_yuzuha_state_sync_case(
    monkeypatch: pytest.MonkeyPatch,
    *,
    static_am: float,
    cinema: int,
    logic_cls: type[Any] = YuzuhaAdditionalAbilityAnomalyBuildupBonus,
    buff_index: str = "yuzuha-additional-ability-anomaly-buildup",
    report_enabled: bool | None = None,
    field_am: float = 0.0,
    flat_am: float = 0.0,
    initial_count: float = 88.0,
) -> _YuzuhaStateSyncCase:
    calls: list[tuple[Any, ...]] = []
    active_buff = _StateSyncBuffProbe(
        index=buff_index,
        tick=700,
        calls=calls,
        initial_count=initial_count,
    )
    char_buff = object()
    enemy_debuff = object()
    char = _make_yuzuha_character(am=static_am, cinema=cinema)
    enemy = _make_enemy(
        sim_instance=active_buff.sim_instance,
        enemy_debuffs=(enemy_debuff,),
    )
    dynamic_buff_list = {char.NAME: [char_buff]}
    _attach_buff_runtime_state(
        sim_instance=active_buff.sim_instance,
        dynamic_buff_list=dynamic_buff_list,
        enemy=enemy,
    )
    aggregation_calls = _patch_buff_aggregation(
        monkeypatch,
        {
            "局内异常掌控": field_am,
            "固定异常掌控": flat_am,
        },
    )
    buff_0 = SimpleNamespace(dy=SimpleNamespace(count=initial_count))
    sub_exist_buff_dict = {active_buff.ft.index: buff_0}
    expected_cinema_1_ratio = 1.0 if cinema < 1 else 1.3
    if report_enabled is not None:
        monkeypatch.setattr(yuzuha_dmg_module, "YUZUHA_REPORT", report_enabled)

    logic = cast(Any, object.__new__(logic_cls))
    logic.buff_instance = active_buff
    logic.buff_0 = buff_0
    logic.record = SimpleNamespace(
        enemy=enemy,
        dynamic_buff_list=dynamic_buff_list,
        char=char,
        sub_exist_buff_dict=sub_exist_buff_dict,
        cinema_1_ratio=None,
    )
    logic.check_record_module = lambda: None

    get_prepared_calls: list[dict[str, object]] = []
    logic.get_prepared = lambda **kwargs: get_prepared_calls.append(kwargs)
    expected_old_count = _old_yuzuha_additional_ability_count(
        enemy=enemy,
        dynamic_buff_list=dynamic_buff_list,
        char=char,
        cinema_1_ratio=expected_cinema_1_ratio,
    )
    return _YuzuhaStateSyncCase(
        logic=logic,
        active_buff=active_buff,
        buff_0=buff_0,
        calls=calls,
        get_prepared_calls=get_prepared_calls,
        aggregation_calls=aggregation_calls,
        expected_enabled_buff=(char_buff, enemy_debuff),
        expected_old_count=expected_old_count,
        expected_cinema_1_ratio=expected_cinema_1_ratio,
    )


def _make_jane_cinema1_state_sync_case(
    monkeypatch: pytest.MonkeyPatch,
    *,
    static_ap: float,
    trigger_active: bool = True,
    field_ap: float = 0.0,
    flat_ap: float = 0.0,
    initial_count: float = 77.0,
    maxcount: float = 999.0,
) -> _JaneCinema1StateSyncCase:
    calls: list[tuple[Any, ...]] = []
    active_buff = _StateSyncBuffProbe(
        index="jane-cinema1-ap-trans-dmg",
        tick=800,
        calls=calls,
        initial_count=initial_count,
        maxcount=maxcount,
    )
    char_buff = object()
    enemy_debuff = object()
    char = _make_jane_character(ap=static_ap)
    enemy = _make_enemy(
        sim_instance=active_buff.sim_instance,
        enemy_debuffs=(enemy_debuff,),
    )
    dynamic_buff_list = {char.NAME: [char_buff]}
    _attach_buff_runtime_state(
        sim_instance=active_buff.sim_instance,
        dynamic_buff_list=dynamic_buff_list,
        enemy=enemy,
    )
    aggregation_calls = _patch_buff_aggregation(
        monkeypatch,
        {
            "局内异常精通": field_ap,
            "固定异常精通": flat_ap,
        },
    )
    buff_0 = SimpleNamespace(dy=SimpleNamespace(count=initial_count))
    trigger_buff_0 = SimpleNamespace(dy=SimpleNamespace(active=trigger_active))
    sub_exist_buff_dict = {active_buff.ft.index: buff_0}

    logic = cast(Any, object.__new__(JaneCinema1APTransToDmgBonus))
    logic.buff_instance = active_buff
    logic.buff_0 = buff_0
    logic.record = SimpleNamespace(
        enemy=enemy,
        dynamic_buff_list=dynamic_buff_list,
        char=char,
        trigger_buff_0=trigger_buff_0,
        sub_exist_buff_dict=sub_exist_buff_dict,
    )
    logic.check_record_module = lambda: None

    get_prepared_calls: list[dict[str, object]] = []
    logic.get_prepared = lambda **kwargs: get_prepared_calls.append(kwargs)
    expected_old_count = _old_jane_cinema1_damage_count(
        enemy=enemy,
        dynamic_buff_list=dynamic_buff_list,
        char=char,
        maxcount=maxcount,
    )
    return _JaneCinema1StateSyncCase(
        logic=logic,
        active_buff=active_buff,
        buff_0=buff_0,
        calls=calls,
        get_prepared_calls=get_prepared_calls,
        aggregation_calls=aggregation_calls,
        expected_enabled_buff=(char_buff, enemy_debuff),
        expected_old_count=expected_old_count,
        initial_count=initial_count,
    )


def _make_jane_core_skill_crit_rate_state_sync_case(
    monkeypatch: pytest.MonkeyPatch,
    *,
    static_ap: float,
    trigger_active: bool = True,
    field_ap: float = 0.0,
    flat_ap: float = 0.0,
    initial_count: float = 55.0,
) -> _JaneCoreSkillCritRateStateSyncCase:
    calls: list[tuple[Any, ...]] = []
    active_buff = _StateSyncBuffProbe(
        index="jane-core-skill-strike-crit-rate",
        tick=820,
        calls=calls,
        initial_count=initial_count,
    )
    char_buff = object()
    enemy_debuff = object()
    char = _make_jane_character(ap=static_ap)
    enemy = _make_enemy(
        sim_instance=active_buff.sim_instance,
        enemy_debuffs=(enemy_debuff,),
    )
    dynamic_buff_list = {char.NAME: [char_buff]}
    _attach_buff_runtime_state(
        sim_instance=active_buff.sim_instance,
        dynamic_buff_list=dynamic_buff_list,
        enemy=enemy,
    )
    aggregation_calls = _patch_buff_aggregation(
        monkeypatch,
        {
            "局内异常精通": field_ap,
            "固定异常精通": flat_ap,
        },
    )
    buff_0 = SimpleNamespace(dy=SimpleNamespace(count=initial_count))
    trigger_buff_0 = SimpleNamespace(dy=SimpleNamespace(active=trigger_active))
    sub_exist_buff_dict = {active_buff.ft.index: buff_0}

    logic = cast(Any, object.__new__(JaneCoreSkillStrikeCritRateBonus))
    logic.buff_instance = active_buff
    logic.buff_0 = buff_0
    logic.record = SimpleNamespace(
        enemy=enemy,
        dynamic_buff_list=dynamic_buff_list,
        char=char,
        trigger_buff_0=trigger_buff_0,
        sub_exist_buff_dict=sub_exist_buff_dict,
    )
    logic.check_record_module = lambda: None

    get_prepared_calls: list[dict[str, object]] = []
    logic.get_prepared = lambda **kwargs: get_prepared_calls.append(kwargs)
    expected_old_count = _old_jane_core_skill_crit_rate_count(
        enemy=enemy,
        dynamic_buff_list=dynamic_buff_list,
        char=char,
    )
    return _JaneCoreSkillCritRateStateSyncCase(
        logic=logic,
        active_buff=active_buff,
        buff_0=buff_0,
        calls=calls,
        get_prepared_calls=get_prepared_calls,
        aggregation_calls=aggregation_calls,
        expected_enabled_buff=(char_buff, enemy_debuff),
        expected_old_count=expected_old_count,
        initial_count=initial_count,
    )


def _make_jane_passion_state_sync_case(
    monkeypatch: pytest.MonkeyPatch,
    *,
    static_ap: float,
    trigger_active: bool = True,
    field_ap: float = 0.0,
    flat_ap: float = 0.0,
    initial_count: float = 44.0,
) -> _JanePassionStateSyncCase:
    calls: list[tuple[Any, ...]] = []
    active_buff = _StateSyncBuffProbe(
        index="jane-passion-state-ap-trans-atk",
        tick=840,
        calls=calls,
        initial_count=initial_count,
    )
    char_buff = object()
    enemy_debuff = object()
    char = _make_jane_character(ap=static_ap)
    enemy = _make_enemy(
        sim_instance=active_buff.sim_instance,
        enemy_debuffs=(enemy_debuff,),
    )
    dynamic_buff_list = {char.NAME: [char_buff]}
    _attach_buff_runtime_state(
        sim_instance=active_buff.sim_instance,
        dynamic_buff_list=dynamic_buff_list,
        enemy=enemy,
    )
    aggregation_calls = _patch_buff_aggregation(
        monkeypatch,
        {
            "局内异常精通": field_ap,
            "固定异常精通": flat_ap,
        },
    )
    buff_0 = SimpleNamespace(dy=SimpleNamespace(count=initial_count))
    trigger_buff_0 = SimpleNamespace(dy=SimpleNamespace(active=trigger_active))
    sub_exist_buff_dict = {active_buff.ft.index: buff_0}

    logic = cast(Any, object.__new__(JanePassionStateAPTransToATK))
    logic.buff_instance = active_buff
    logic.buff_0 = buff_0
    logic.record = SimpleNamespace(
        enemy=enemy,
        dynamic_buff_list=dynamic_buff_list,
        char=char,
        trigger_buff_0=trigger_buff_0,
        sub_exist_buff_dict=sub_exist_buff_dict,
    )
    logic.check_record_module = lambda: None

    get_prepared_calls: list[dict[str, object]] = []
    logic.get_prepared = lambda **kwargs: get_prepared_calls.append(kwargs)
    expected_old_count = _old_jane_passion_state_atk_count(
        enemy=enemy,
        dynamic_buff_list=dynamic_buff_list,
        char=char,
    )
    return _JanePassionStateSyncCase(
        logic=logic,
        active_buff=active_buff,
        buff_0=buff_0,
        calls=calls,
        get_prepared_calls=get_prepared_calls,
        aggregation_calls=aggregation_calls,
        expected_enabled_buff=(char_buff, enemy_debuff),
        expected_old_count=expected_old_count,
        initial_count=initial_count,
    )


def _make_buff_0(
    calls: list[tuple[Any, ...]],
    *,
    initial_count: float,
    step: float,
    record_count_writes: bool = False,
) -> SimpleNamespace:
    dy: object
    if record_count_writes:
        dy = _DynamicCountRecorder(
            calls,
            initial_count,
            label="buff_0.dy.count",
        )
    else:
        dy = SimpleNamespace(count=initial_count)
    return SimpleNamespace(
        dy=dy,
        ft=SimpleNamespace(step=step),
        history=SimpleNamespace(record=None),
    )


def _make_lighter_impact_state_sync_case(
    monkeypatch: pytest.MonkeyPatch,
    *,
    static_imp: float,
    field_imp: float = 0.0,
    flat_imp: float = 0.0,
    initial_count: float = 20.0,
    initial_real_count: float = 10.0,
    step: float = 5.0,
    maxcount: float = 300.0,
) -> _P2BStateSyncCase:
    calls: list[tuple[Any, ...]] = []
    active_buff = _StateSyncBuffProbe(
        index="lighter-additional-ability-ice-fire",
        tick=900,
        calls=calls,
        initial_count=initial_count,
        maxcount=maxcount,
        step=step,
    )
    char_buff = object()
    enemy_debuff = object()
    char = _make_p2b_character(name="莱特", cid=1161, imp=static_imp)
    enemy = _make_enemy(
        sim_instance=active_buff.sim_instance,
        enemy_debuffs=(enemy_debuff,),
    )
    dynamic_buff_list = {char.NAME: [char_buff]}
    _attach_buff_runtime_state(
        sim_instance=active_buff.sim_instance,
        dynamic_buff_list=dynamic_buff_list,
        enemy=enemy,
    )
    aggregation_calls = _patch_buff_aggregation(
        monkeypatch,
        {
            "局内冲击力%": field_imp,
            "固定冲击力": flat_imp,
        },
        call_log=calls,
    )
    buff_0 = _make_buff_0(calls, initial_count=initial_count, step=step)
    sub_exist_buff_dict = {active_buff.ft.index: buff_0}

    logic = cast(Any, object.__new__(LighterExtraSkill_IceFireBonus))
    logic.buff_instance = active_buff
    logic.buff_0 = buff_0
    logic.record = SimpleNamespace(
        enemy=enemy,
        dynamic_buff_list=dynamic_buff_list,
        char=char,
        sub_exist_buff_dict=sub_exist_buff_dict,
        real_count=initial_real_count,
    )
    logic.check_record_module = lambda: None

    get_prepared_calls: list[dict[str, object]] = []
    logic.get_prepared = lambda **kwargs: get_prepared_calls.append(kwargs)
    expected_old_count, expected_real_count = _old_lighter_count(
        enemy=enemy,
        dynamic_buff_list=dynamic_buff_list,
        char=char,
        initial_real_count=initial_real_count,
        step=step,
    )
    MultiplierData.mul_data_cache.clear()
    calls.clear()
    return _P2BStateSyncCase(
        logic=logic,
        active_buff=active_buff,
        buff_0=buff_0,
        calls=calls,
        get_prepared_calls=get_prepared_calls,
        aggregation_calls=aggregation_calls,
        expected_enabled_buff=(char_buff, enemy_debuff),
        expected_old_count=expected_old_count,
        initial_count=initial_count,
        expected_real_count=expected_real_count,
    )


def _make_qingyi_impact_state_sync_case(
    monkeypatch: pytest.MonkeyPatch,
    *,
    static_imp: float,
    field_imp: float = 0.0,
    flat_imp: float = 0.0,
    initial_count: float = 35.0,
    step: float = 1.0,
    maxcount: float = 600.0,
) -> _P2BStateSyncCase:
    calls: list[tuple[Any, ...]] = []
    active_buff = _StateSyncBuffProbe(
        index="qingyi-additional-ability-stun-convert-atk",
        tick=910,
        calls=calls,
        initial_count=initial_count,
        maxcount=maxcount,
        step=step,
    )
    char_buff = object()
    enemy_debuff = object()
    char = _make_p2b_character(name="青衣", cid=1251, imp=static_imp)
    enemy = _make_enemy(
        sim_instance=active_buff.sim_instance,
        enemy_debuffs=(enemy_debuff,),
    )
    dynamic_buff_list = {char.NAME: [char_buff]}
    _attach_buff_runtime_state(
        sim_instance=active_buff.sim_instance,
        dynamic_buff_list=dynamic_buff_list,
        enemy=enemy,
    )
    aggregation_calls = _patch_buff_aggregation(
        monkeypatch,
        {
            "局内冲击力%": field_imp,
            "固定冲击力": flat_imp,
        },
        call_log=calls,
    )
    buff_0 = _make_buff_0(
        calls,
        initial_count=initial_count,
        step=step,
        record_count_writes=True,
    )
    sub_exist_buff_dict = {active_buff.ft.index: buff_0}

    logic = cast(Any, object.__new__(QingYiAdditionalAbilityStunConvertToATK))
    logic.buff_instance = active_buff
    logic.buff_0 = buff_0
    logic.record = SimpleNamespace(
        enemy=enemy,
        dynamic_buff_list=dynamic_buff_list,
        char=char,
        sub_exist_buff_dict=sub_exist_buff_dict,
    )
    logic.check_record_module = lambda: None

    get_prepared_calls: list[dict[str, object]] = []
    logic.get_prepared = lambda **kwargs: get_prepared_calls.append(kwargs)
    expected_old_count = _old_qingyi_count(
        enemy=enemy,
        dynamic_buff_list=dynamic_buff_list,
        char=char,
        maxcount=maxcount,
    )
    MultiplierData.mul_data_cache.clear()
    calls.clear()
    return _P2BStateSyncCase(
        logic=logic,
        active_buff=active_buff,
        buff_0=buff_0,
        calls=calls,
        get_prepared_calls=get_prepared_calls,
        aggregation_calls=aggregation_calls,
        expected_enabled_buff=(char_buff, enemy_debuff),
        expected_old_count=expected_old_count,
        initial_count=initial_count,
    )


def _make_trigger_personal_crit_rate_state_sync_case(
    monkeypatch: pytest.MonkeyPatch,
    *,
    static_crit_rate: float,
    field_crit_rate: float = 0.0,
    flat_crit_rate: float = 0.0,
    received_crit_rate: float = 0.0,
    initial_count: float = 12.0,
) -> _P2BStateSyncCase:
    calls: list[tuple[Any, ...]] = []
    active_buff = _StateSyncBuffProbe(
        index="trigger-additional-ability-stun-bonus",
        tick=920,
        calls=calls,
        initial_count=initial_count,
    )
    char_buff = object()
    enemy_debuff = object()
    char = _make_p2b_character(name="扳机", cid=1361, crit_rate=static_crit_rate)
    enemy = _make_enemy(
        sim_instance=active_buff.sim_instance,
        enemy_debuffs=(enemy_debuff,),
    )
    dynamic_buff_list = {char.NAME: [char_buff]}
    _attach_buff_runtime_state(
        sim_instance=active_buff.sim_instance,
        dynamic_buff_list=dynamic_buff_list,
        enemy=enemy,
    )
    aggregation_calls = _patch_buff_aggregation(
        monkeypatch,
        {
            "局内暴击率": field_crit_rate,
            "固定暴击率": flat_crit_rate,
            "被暴击几率增加": received_crit_rate,
        },
        call_log=calls,
    )
    buff_0 = _make_buff_0(calls, initial_count=initial_count, step=1.0)
    sub_exist_buff_dict = {active_buff.ft.index: buff_0}

    logic = cast(Any, object.__new__(TriggerAdditionalAbilityStunBonus))
    logic.buff_instance = active_buff
    logic.buff_0 = buff_0
    logic.record = SimpleNamespace(
        enemy=enemy,
        dynamic_buff_list=dynamic_buff_list,
        char=char,
        sub_exist_buff_dict=sub_exist_buff_dict,
    )
    logic.check_record_module = lambda: None

    get_prepared_calls: list[dict[str, object]] = []
    logic.get_prepared = lambda **kwargs: get_prepared_calls.append(kwargs)
    expected_old_count = _old_trigger_personal_crit_rate_count(
        enemy=enemy,
        dynamic_buff_list=dynamic_buff_list,
        char=char,
    )
    MultiplierData.mul_data_cache.clear()
    calls.clear()
    return _P2BStateSyncCase(
        logic=logic,
        active_buff=active_buff,
        buff_0=buff_0,
        calls=calls,
        get_prepared_calls=get_prepared_calls,
        aggregation_calls=aggregation_calls,
        expected_enabled_buff=(char_buff, enemy_debuff),
        expected_old_count=expected_old_count,
        initial_count=initial_count,
    )


def _make_soldier0_anby_personal_crit_damage_state_sync_case(
    monkeypatch: pytest.MonkeyPatch,
    *,
    static_crit_damage: float,
    field_crit_damage: float = 0.0,
    flat_crit_damage: float = 0.0,
    received_crit_damage: float = 0.0,
    trigger_active: bool = True,
    initial_count: float = 15.0,
) -> _P2BStateSyncCase:
    calls: list[tuple[Any, ...]] = []
    active_buff = _StateSyncBuffProbe(
        index="soldier0-anby-core-skill-crit-dmg-bonus",
        tick=930,
        calls=calls,
        initial_count=initial_count,
    )
    char_buff = object()
    enemy_debuff = object()
    char = _make_p2b_character(
        name="零号·安比",
        cid=1381,
        crit_damage=static_crit_damage,
    )
    enemy = _make_enemy(
        sim_instance=active_buff.sim_instance,
        enemy_debuffs=(enemy_debuff,),
    )
    dynamic_buff_list = {char.NAME: [char_buff]}
    _attach_buff_runtime_state(
        sim_instance=active_buff.sim_instance,
        dynamic_buff_list=dynamic_buff_list,
        enemy=enemy,
    )
    aggregation_calls = _patch_buff_aggregation(
        monkeypatch,
        {
            "局内暴击伤害": field_crit_damage,
            "固定暴击伤害": flat_crit_damage,
            "受暴击伤害增加": received_crit_damage,
        },
        call_log=calls,
    )
    buff_0 = _make_buff_0(calls, initial_count=initial_count, step=1.0)
    trigger_buff_0 = SimpleNamespace(dy=SimpleNamespace(active=trigger_active))
    sub_exist_buff_dict = {active_buff.ft.index: buff_0}

    logic = cast(Any, object.__new__(Soldier0AnbyCoreSkillCritDMGBonus))
    logic.buff_instance = active_buff
    logic.buff_0 = buff_0
    logic.record = SimpleNamespace(
        enemy=enemy,
        dynamic_buff_list=dynamic_buff_list,
        char=char,
        sub_exist_buff_dict=sub_exist_buff_dict,
        trigger_buff_0=trigger_buff_0,
    )
    logic.check_record_module = lambda: None

    get_prepared_calls: list[dict[str, object]] = []
    logic.get_prepared = lambda **kwargs: get_prepared_calls.append(kwargs)
    expected_old_count = _old_soldier0_anby_personal_crit_damage_count(
        enemy=enemy,
        dynamic_buff_list=dynamic_buff_list,
        char=char,
    )
    MultiplierData.mul_data_cache.clear()
    calls.clear()
    return _P2BStateSyncCase(
        logic=logic,
        active_buff=active_buff,
        buff_0=buff_0,
        calls=calls,
        get_prepared_calls=get_prepared_calls,
        aggregation_calls=aggregation_calls,
        expected_enabled_buff=(char_buff, enemy_debuff),
        expected_old_count=expected_old_count,
        initial_count=initial_count,
    )


def _trigger_skill_node(
    *,
    skill_tag: str = "1361",
    labels: dict[str, object] | None = None,
) -> SimpleNamespace:
    if labels is None:
        labels = {"aftershock_attack": object()}
    return SimpleNamespace(skill_tag=skill_tag, skill=SimpleNamespace(labels=labels))


@pytest.mark.parametrize(
    (
        "module",
        "logic_cls",
        "record_cls",
        "owner",
        "index",
    ),
    [
        (
            lighter_module,
            LighterExtraSkill_IceFireBonus,
            lighter_module.LighterExtraSkillRecord,
            "莱特",
            "lighter-additional-ability-ice-fire",
        ),
        (
            qingyi_module,
            QingYiAdditionalAbilityStunConvertToATK,
            qingyi_module.QingYiAdditionalSkillRecord,
            "青衣",
            "qingyi-additional-ability-stun-convert-atk",
        ),
        (
            trigger_module,
            TriggerAdditionalAbilityStunBonus,
            trigger_module.TriggerAdditionalAbilityStunBonusRecord,
            "扳机",
            "trigger-additional-ability-stun-bonus",
        ),
        (
            soldier0_anby_module,
            Soldier0AnbyCoreSkillCritDMGBonus,
            soldier0_anby_module.Soldier0AnbyCoreSkillCritDMGBonusRecord,
            "零号·安比",
            "soldier0-anby-core-skill-crit-dmg-bonus",
        ),
    ],
)
def test_selected_owner_family_check_record_module_preserves_old_template_identity_and_lazy_record(
    monkeypatch: pytest.MonkeyPatch,
    module: object,
    logic_cls: type[object],
    record_cls: type[object],
    owner: str,
    index: str,
) -> None:
    calls: list[tuple[Any, ...]] = []
    active_buff = _StateSyncBuffProbe(
        index=index,
        tick=950,
        calls=calls,
        initial_count=7.0,
    )
    buff_0 = _make_buff_0(calls, initial_count=7.0, step=1.0)
    expected_lookup_calls = (
        [] if logic_cls is Soldier0AnbyCoreSkillCritDMGBonus else [active_buff.sim_instance]
    )
    preparation_context_calls: list[tuple[str, object]] = []
    expected_preparation_context_calls: list[tuple[str, object]] = []

    if logic_cls is Soldier0AnbyCoreSkillCritDMGBonus:

        class _FakePreparationContext:
            def find_sub_exist_buff_dict(self, target_owner: str) -> dict[str, object]:
                preparation_context_calls.append(("find_sub_exist_buff_dict", target_owner))
                return {index: buff_0}

        def fake_build_preparation_context_from_buff(
            buff_instance: object,
        ) -> _FakePreparationContext:
            preparation_context_calls.append(("build", buff_instance))
            return _FakePreparationContext()

        monkeypatch.setattr(
            cast(Any, module),
            "build_preparation_context_from_buff",
            fake_build_preparation_context_from_buff,
        )
        expected_preparation_context_calls = [
            ("build", active_buff),
            ("find_sub_exist_buff_dict", owner),
        ]

    lookup_calls: list[object] = []

    def fake_find_exist_buff_dict(*, sim_instance: object) -> dict[str, dict[str, object]]:
        lookup_calls.append(sim_instance)
        return {owner: {index: buff_0}}

    monkeypatch.setattr(
        cast(Any, module).JudgeTools,
        "find_exist_buff_dict",
        fake_find_exist_buff_dict,
    )

    logic = cast(Any, object.__new__(logic_cls))
    logic.buff_instance = active_buff
    logic.buff_0 = None
    logic.record = None

    logic.check_record_module()

    assert lookup_calls == expected_lookup_calls
    assert preparation_context_calls == expected_preparation_context_calls
    assert logic.buff_0 is buff_0
    assert logic.record is buff_0.history.record
    assert isinstance(logic.record, record_cls)
    assert buff_0.dy.count == pytest.approx(7.0)

    existing_record = logic.record
    logic.check_record_module()

    assert lookup_calls == expected_lookup_calls
    assert preparation_context_calls == expected_preparation_context_calls
    assert logic.buff_0 is buff_0
    assert logic.record is existing_record
    assert buff_0.history.record is existing_record
    assert buff_0.dy.count == pytest.approx(7.0)


def test_count_state_sync_preserves_simple_start_assignment_update_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = _make_alice_state_sync_case(
        monkeypatch,
        static_am=145.0,
    )

    case.logic.special_judge_logic()

    assert case.expected_old_count == pytest.approx(8.0)
    assert case.get_prepared_calls == [{"char_CID": 1401, "sub_exist_buff_dict": 1, "enemy": 1}]
    assert case.aggregation_calls == [
        (case.expected_enabled_buff, None, case.active_buff.sim_instance, "Alice"),
        (case.expected_enabled_buff, None, case.active_buff.sim_instance, "Alice"),
    ]
    assert case.calls == [
        ("simple_start", 600, True, 123.0, case.buff_0),
        ("dy.count", case.expected_old_count),
        ("update_to_buff_0", case.buff_0, case.expected_old_count),
    ]
    assert case.active_buff.dy.count == pytest.approx(case.expected_old_count)
    assert case.buff_0.dy.count == pytest.approx(case.expected_old_count)


def test_count_state_sync_skips_writeback_below_am_threshold(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = _make_alice_state_sync_case(
        monkeypatch,
        static_am=139.99,
    )

    result = case.logic.special_judge_logic()

    assert result is None
    assert case.expected_old_count is None
    assert case.get_prepared_calls == [{"char_CID": 1401, "sub_exist_buff_dict": 1, "enemy": 1}]
    assert case.aggregation_calls == [
        (case.expected_enabled_buff, None, case.active_buff.sim_instance, "Alice"),
        (case.expected_enabled_buff, None, case.active_buff.sim_instance, "Alice"),
    ]
    assert case.calls == []
    assert case.active_buff.dy.count == pytest.approx(123.0)
    assert case.buff_0.dy.count == pytest.approx(123.0)


def test_alice_reader_path_matches_old_count_for_high_am_source_behavior(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = _make_alice_state_sync_case(
        monkeypatch,
        static_am=800.0,
        maxcount=999.0,
    )

    case.logic.special_judge_logic()

    assert case.expected_old_count == pytest.approx((800.0 - 140.0) * 1.6)
    assert case.expected_old_count > case.active_buff.ft.maxcount
    assert case.calls == [
        ("simple_start", 600, True, 123.0, case.buff_0),
        ("dy.count", case.expected_old_count),
        ("update_to_buff_0", case.buff_0, case.expected_old_count),
    ]
    assert case.active_buff.dy.count == pytest.approx(case.expected_old_count)
    assert case.buff_0.dy.count == pytest.approx(case.expected_old_count)


def test_yuzuha_buildup_skips_writeback_below_am_threshold(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = _make_yuzuha_state_sync_case(
        monkeypatch,
        static_am=99.99,
        cinema=0,
    )

    result = case.logic.special_hit_logic()

    assert result is None
    assert case.expected_old_count is None
    assert case.logic.record.cinema_1_ratio == pytest.approx(case.expected_cinema_1_ratio)
    assert case.get_prepared_calls == [{"char_CID": 1411, "sub_exist_buff_dict": 1, "enemy": 1}]
    assert case.aggregation_calls == [
        (case.expected_enabled_buff, None, case.active_buff.sim_instance, "Yuzuha"),
        (case.expected_enabled_buff, None, case.active_buff.sim_instance, "Yuzuha"),
    ]
    assert case.calls == []
    assert case.active_buff.dy.count == pytest.approx(88.0)
    assert case.buff_0.dy.count == pytest.approx(88.0)


def test_yuzuha_buildup_reader_path_matches_old_count_for_cinema_zero_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = _make_yuzuha_state_sync_case(
        monkeypatch,
        static_am=145.0,
        cinema=0,
    )

    case.logic.special_hit_logic()

    assert case.expected_old_count == pytest.approx(45.0)
    assert case.logic.record.cinema_1_ratio == pytest.approx(1.0)
    assert case.get_prepared_calls == [{"char_CID": 1411, "sub_exist_buff_dict": 1, "enemy": 1}]
    assert case.aggregation_calls == [
        (case.expected_enabled_buff, None, case.active_buff.sim_instance, "Yuzuha"),
        (case.expected_enabled_buff, None, case.active_buff.sim_instance, "Yuzuha"),
    ]
    assert case.calls == [
        ("simple_start", 700, True, 88.0, case.buff_0),
        ("dy.count", case.expected_old_count),
        ("update_to_buff_0", case.buff_0, case.expected_old_count),
    ]
    assert case.active_buff.dy.count == pytest.approx(case.expected_old_count)
    assert case.buff_0.dy.count == pytest.approx(case.expected_old_count)


def test_yuzuha_buildup_reader_path_matches_old_count_for_cinema_one_plus_cap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = _make_yuzuha_state_sync_case(
        monkeypatch,
        static_am=250.0,
        cinema=1,
    )

    case.logic.special_hit_logic()

    assert case.expected_old_count == pytest.approx(130.0)
    assert case.logic.record.cinema_1_ratio == pytest.approx(1.3)
    assert case.get_prepared_calls == [{"char_CID": 1411, "sub_exist_buff_dict": 1, "enemy": 1}]
    assert case.aggregation_calls == [
        (case.expected_enabled_buff, None, case.active_buff.sim_instance, "Yuzuha"),
        (case.expected_enabled_buff, None, case.active_buff.sim_instance, "Yuzuha"),
    ]
    assert case.calls == [
        ("simple_start", 700, True, 88.0, case.buff_0),
        ("dy.count", case.expected_old_count),
        ("update_to_buff_0", case.buff_0, case.expected_old_count),
    ]
    assert case.active_buff.dy.count == pytest.approx(case.expected_old_count)
    assert case.buff_0.dy.count == pytest.approx(case.expected_old_count)


def test_yuzuha_damage_skips_writeback_below_am_threshold(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = _make_yuzuha_state_sync_case(
        monkeypatch,
        static_am=99.99,
        cinema=0,
        logic_cls=YuzuhaAdditionalAbilityAnomalyDmgBonus,
        buff_index="yuzuha-additional-ability-anomaly-dmg",
        report_enabled=True,
    )

    result = case.logic.special_hit_logic()

    assert result is None
    assert case.expected_old_count is None
    assert case.logic.record.cinema_1_ratio == pytest.approx(case.expected_cinema_1_ratio)
    assert case.get_prepared_calls == [{"char_CID": 1411, "sub_exist_buff_dict": 1, "enemy": 1}]
    assert case.aggregation_calls == [
        (case.expected_enabled_buff, None, case.active_buff.sim_instance, "Yuzuha"),
        (case.expected_enabled_buff, None, case.active_buff.sim_instance, "Yuzuha"),
    ]
    assert case.calls == []
    assert case.active_buff.dy.count == pytest.approx(88.0)
    assert case.buff_0.dy.count == pytest.approx(88.0)


def test_yuzuha_damage_reader_path_matches_old_count_for_cinema_zero_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = _make_yuzuha_state_sync_case(
        monkeypatch,
        static_am=145.0,
        cinema=0,
        logic_cls=YuzuhaAdditionalAbilityAnomalyDmgBonus,
        buff_index="yuzuha-additional-ability-anomaly-dmg",
        report_enabled=False,
    )

    case.logic.special_hit_logic()

    assert case.expected_old_count == pytest.approx(45.0)
    assert case.logic.record.cinema_1_ratio == pytest.approx(1.0)
    assert case.get_prepared_calls == [{"char_CID": 1411, "sub_exist_buff_dict": 1, "enemy": 1}]
    assert case.aggregation_calls == [
        (case.expected_enabled_buff, None, case.active_buff.sim_instance, "Yuzuha"),
        (case.expected_enabled_buff, None, case.active_buff.sim_instance, "Yuzuha"),
    ]
    assert case.calls == [
        ("simple_start", 700, True, 88.0, case.buff_0),
        ("dy.count", case.expected_old_count),
        ("update_to_buff_0", case.buff_0, case.expected_old_count),
    ]
    assert case.active_buff.dy.count == pytest.approx(case.expected_old_count)
    assert case.buff_0.dy.count == pytest.approx(case.expected_old_count)


def test_yuzuha_damage_reader_path_keeps_cinema_one_plus_cap_and_report(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = _make_yuzuha_state_sync_case(
        monkeypatch,
        static_am=250.0,
        cinema=1,
        logic_cls=YuzuhaAdditionalAbilityAnomalyDmgBonus,
        buff_index="yuzuha-additional-ability-anomaly-dmg",
        report_enabled=True,
    )

    case.logic.special_hit_logic()

    assert case.expected_old_count == pytest.approx(130.0)
    assert case.logic.record.cinema_1_ratio == pytest.approx(1.3)
    assert case.get_prepared_calls == [{"char_CID": 1411, "sub_exist_buff_dict": 1, "enemy": 1}]
    assert case.aggregation_calls == [
        (case.expected_enabled_buff, None, case.active_buff.sim_instance, "Yuzuha"),
        (case.expected_enabled_buff, None, case.active_buff.sim_instance, "Yuzuha"),
    ]
    assert case.calls == [
        ("simple_start", 700, True, 88.0, case.buff_0),
        ("dy.count", case.expected_old_count),
        ("update_to_buff_0", case.buff_0, case.expected_old_count),
        ("change_process_state",),
    ]
    assert case.active_buff.dy.count == pytest.approx(case.expected_old_count)
    assert case.buff_0.dy.count == pytest.approx(case.expected_old_count)


def test_jane_cinema1_inactive_trigger_gate_skips_writeback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = _make_jane_cinema1_state_sync_case(
        monkeypatch,
        static_ap=200.0,
        trigger_active=False,
    )
    case.aggregation_calls.clear()

    result = case.logic.special_judge_logic()

    assert result is False
    assert case.get_prepared_calls == [
        {"char_CID": 1261, "trigger_buff_0": ("简", "Buff-角色-简-狂热状态触发器")}
    ]
    assert case.aggregation_calls == []
    assert case.calls == []
    assert case.active_buff.dy.count == pytest.approx(case.initial_count)
    assert case.buff_0.dy.count == pytest.approx(case.initial_count)


def test_jane_cinema1_active_trigger_count_parity_and_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = _make_jane_cinema1_state_sync_case(
        monkeypatch,
        static_ap=200.0,
    )

    assert case.logic.special_judge_logic() is True
    case.logic.special_hit_logic()

    assert case.expected_old_count == pytest.approx(20.0)
    assert case.get_prepared_calls == [
        {"char_CID": 1261, "trigger_buff_0": ("简", "Buff-角色-简-狂热状态触发器")},
        {
            "char_CID": 1261,
            "trigger_buff_0": ("简", "Buff-角色-简-狂热状态触发器"),
            "enemy": 1,
            "sub_exist_buff_dict": 1,
        },
    ]
    assert case.aggregation_calls == [
        (case.expected_enabled_buff, None, case.active_buff.sim_instance, "Jane"),
        (case.expected_enabled_buff, None, case.active_buff.sim_instance, "Jane"),
    ]
    assert case.calls == [
        ("simple_start", 800, True, case.initial_count, case.buff_0),
        ("dy.count", case.expected_old_count),
        ("update_to_buff_0", case.buff_0, case.expected_old_count),
    ]
    assert case.active_buff.dy.count == pytest.approx(case.expected_old_count)
    assert case.buff_0.dy.count == pytest.approx(case.expected_old_count)


def test_jane_cinema1_reader_path_keeps_maxcount_cap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = _make_jane_cinema1_state_sync_case(
        monkeypatch,
        static_ap=1500.0,
        maxcount=100.0,
    )

    case.logic.special_hit_logic()

    assert case.expected_old_count == pytest.approx(100.0)
    assert case.aggregation_calls == [
        (case.expected_enabled_buff, None, case.active_buff.sim_instance, "Jane"),
        (case.expected_enabled_buff, None, case.active_buff.sim_instance, "Jane"),
    ]
    assert case.calls == [
        ("simple_start", 800, True, case.initial_count, case.buff_0),
        ("dy.count", case.expected_old_count),
        ("update_to_buff_0", case.buff_0, case.expected_old_count),
    ]
    assert case.active_buff.dy.count == pytest.approx(case.expected_old_count)
    assert case.buff_0.dy.count == pytest.approx(case.expected_old_count)


def test_jane_core_skill_crit_rate_inactive_trigger_gate_skips_writeback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = _make_jane_core_skill_crit_rate_state_sync_case(
        monkeypatch,
        static_ap=200.0,
        trigger_active=False,
    )
    case.aggregation_calls.clear()

    result = case.logic.special_judge_logic()

    assert result is False
    assert case.get_prepared_calls == [
        {"char_CID": 1261, "trigger_buff_0": ("enemy", "Buff-角色-简-核心被动-啮咬触发器")}
    ]
    assert case.aggregation_calls == []
    assert case.calls == []
    assert case.active_buff.dy.count == pytest.approx(case.initial_count)
    assert case.buff_0.dy.count == pytest.approx(case.initial_count)


def test_jane_core_skill_crit_rate_active_trigger_count_parity_and_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = _make_jane_core_skill_crit_rate_state_sync_case(
        monkeypatch,
        static_ap=200.0,
    )

    assert case.logic.special_judge_logic() is True
    case.logic.special_hit_logic()

    assert case.expected_old_count == pytest.approx(72.0)
    assert case.get_prepared_calls == [
        {"char_CID": 1261, "trigger_buff_0": ("enemy", "Buff-角色-简-核心被动-啮咬触发器")},
        {
            "char_CID": 1261,
            "trigger_buff_0": ("enemy", "Buff-角色-简-核心被动-啮咬触发器"),
            "enemy": 1,
            "sub_exist_buff_dict": 1,
        },
    ]
    assert case.aggregation_calls == [
        (case.expected_enabled_buff, None, case.active_buff.sim_instance, "Jane"),
        (case.expected_enabled_buff, None, case.active_buff.sim_instance, "Jane"),
    ]
    assert case.calls == [
        ("simple_start", 820, True, case.initial_count, case.buff_0),
        ("dy.count", case.expected_old_count),
        ("update_to_buff_0", case.buff_0, case.expected_old_count),
    ]
    assert case.active_buff.dy.count == pytest.approx(case.expected_old_count)
    assert case.buff_0.dy.count == pytest.approx(case.expected_old_count)


def test_jane_core_skill_crit_rate_reader_path_keeps_formula_cap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = _make_jane_core_skill_crit_rate_state_sync_case(
        monkeypatch,
        static_ap=500.0,
    )

    case.logic.special_hit_logic()

    assert case.expected_old_count == pytest.approx(100.0)
    assert case.aggregation_calls == [
        (case.expected_enabled_buff, None, case.active_buff.sim_instance, "Jane"),
        (case.expected_enabled_buff, None, case.active_buff.sim_instance, "Jane"),
    ]
    assert case.calls == [
        ("simple_start", 820, True, case.initial_count, case.buff_0),
        ("dy.count", case.expected_old_count),
        ("update_to_buff_0", case.buff_0, case.expected_old_count),
    ]
    assert case.active_buff.dy.count == pytest.approx(case.expected_old_count)
    assert case.buff_0.dy.count == pytest.approx(case.expected_old_count)


def test_jane_passion_state_inactive_trigger_gate_skips_writeback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = _make_jane_passion_state_sync_case(
        monkeypatch,
        static_ap=200.0,
        trigger_active=False,
    )
    case.aggregation_calls.clear()

    result = case.logic.special_judge_logic()

    assert result is False
    assert case.get_prepared_calls == [
        {"char_CID": 1261, "trigger_buff_0": ("简", "Buff-角色-简-狂热状态触发器")}
    ]
    assert case.aggregation_calls == []
    assert case.calls == []
    assert case.active_buff.dy.count == pytest.approx(case.initial_count)
    assert case.buff_0.dy.count == pytest.approx(case.initial_count)


def test_jane_passion_state_ap_under_120_writes_zero_count(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = _make_jane_passion_state_sync_case(
        monkeypatch,
        static_ap=119.9,
    )

    assert case.logic.special_judge_logic() is True
    case.logic.special_hit_logic()

    assert case.expected_old_count == pytest.approx(0.0)
    assert case.get_prepared_calls == [
        {"char_CID": 1261, "trigger_buff_0": ("简", "Buff-角色-简-狂热状态触发器")},
        {
            "char_CID": 1261,
            "trigger_buff_0": ("简", "Buff-角色-简-狂热状态触发器"),
            "enemy": 1,
            "sub_exist_buff_dict": 1,
        },
    ]
    assert case.aggregation_calls == [
        (case.expected_enabled_buff, None, case.active_buff.sim_instance, "Jane"),
        (case.expected_enabled_buff, None, case.active_buff.sim_instance, "Jane"),
    ]
    assert case.calls == [
        ("simple_start", 840, True, case.initial_count, case.buff_0),
        ("dy.count", case.expected_old_count),
        ("update_to_buff_0", case.buff_0, case.expected_old_count),
    ]
    assert case.active_buff.dy.count == pytest.approx(case.expected_old_count)
    assert case.buff_0.dy.count == pytest.approx(case.expected_old_count)


def test_jane_passion_state_fractional_ap_above_120_is_floored(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = _make_jane_passion_state_sync_case(
        monkeypatch,
        static_ap=120.99,
    )

    case.logic.special_hit_logic()

    assert case.expected_old_count == pytest.approx(0.0)
    assert case.aggregation_calls == [
        (case.expected_enabled_buff, None, case.active_buff.sim_instance, "Jane"),
        (case.expected_enabled_buff, None, case.active_buff.sim_instance, "Jane"),
    ]
    assert case.calls == [
        ("simple_start", 840, True, case.initial_count, case.buff_0),
        ("dy.count", case.expected_old_count),
        ("update_to_buff_0", case.buff_0, case.expected_old_count),
    ]
    assert case.active_buff.dy.count == pytest.approx(case.expected_old_count)
    assert case.buff_0.dy.count == pytest.approx(case.expected_old_count)


def test_jane_passion_state_higher_ap_count_parity_and_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = _make_jane_passion_state_sync_case(
        monkeypatch,
        static_ap=255.25,
        field_ap=0.1,
        flat_ap=5.5,
    )

    case.logic.special_hit_logic()

    assert case.expected_old_count == pytest.approx(166.0)
    assert case.aggregation_calls == [
        (case.expected_enabled_buff, None, case.active_buff.sim_instance, "Jane"),
        (case.expected_enabled_buff, None, case.active_buff.sim_instance, "Jane"),
    ]
    assert case.calls == [
        ("simple_start", 840, True, case.initial_count, case.buff_0),
        ("dy.count", case.expected_old_count),
        ("update_to_buff_0", case.buff_0, case.expected_old_count),
    ]
    assert case.active_buff.dy.count == pytest.approx(case.expected_old_count)
    assert case.buff_0.dy.count == pytest.approx(case.expected_old_count)


def test_lighter_impact_state_sync_keeps_base_count_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = _make_lighter_impact_state_sync_case(
        monkeypatch,
        static_imp=160.0,
        initial_real_count=0.0,
    )

    case.logic.special_hit_logic()

    assert case.expected_real_count == pytest.approx(5.0)
    assert case.expected_old_count == pytest.approx(5.0)
    assert case.logic.record.real_count == pytest.approx(case.expected_real_count)
    assert case.get_prepared_calls == [{"char_CID": 1161, "enemy": 1, "sub_exist_buff_dict": 1}]
    assert case.aggregation_calls == [
        (case.expected_enabled_buff, None, case.active_buff.sim_instance, "莱特"),
        (case.expected_enabled_buff, None, case.active_buff.sim_instance, "莱特"),
    ]
    assert case.calls == [
        ("simple_start", 900, False, case.initial_count, case.buff_0),
        ("dy.count", case.initial_count + case.active_buff.ft.step),
        ("attribute_read",),
        ("dy.count", case.expected_old_count),
        ("update_to_buff_0", case.buff_0, case.expected_old_count),
    ]
    _assert_final_count_writeback_order(
        case.calls,
        buff_0=case.buff_0,
        expected_count=case.expected_old_count,
    )
    assert case.active_buff.dy.count == pytest.approx(case.expected_old_count)
    assert case.buff_0.dy.count == pytest.approx(case.expected_old_count)


def test_lighter_impact_state_sync_keeps_high_impact_cap_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = _make_lighter_impact_state_sync_case(
        monkeypatch,
        static_imp=1000.0,
        initial_real_count=95.0,
    )

    case.logic.special_hit_logic()

    assert case.expected_real_count == pytest.approx(100.0)
    assert case.expected_old_count == pytest.approx(300.0)
    assert case.logic.record.real_count == pytest.approx(case.expected_real_count)
    assert case.calls == [
        ("simple_start", 900, False, case.initial_count, case.buff_0),
        ("dy.count", case.initial_count + case.active_buff.ft.step),
        ("attribute_read",),
        ("dy.count", case.expected_old_count),
        ("update_to_buff_0", case.buff_0, case.expected_old_count),
    ]
    _assert_final_count_writeback_order(
        case.calls,
        buff_0=case.buff_0,
        expected_count=case.expected_old_count,
    )
    assert case.active_buff.dy.count == pytest.approx(case.expected_old_count)
    assert case.buff_0.dy.count == pytest.approx(case.expected_old_count)


def test_lighter_impact_uses_reader_not_multiplier_data() -> None:
    source = Path(
        "zsim/sim_progress/Buff/BuffXLogic/LighterAdditionalAbility_IceFireBonus.py"
    ).read_text(encoding="utf-8")

    assert "MultiplierData" not in source
    assert "Calculator.StunMul.cal_imp" not in source
    assert "create_calculator_runtime_read_context_from_sim_instance" in source
    assert "get_calculator_buff_attribute_reader_service" in source
    assert "active_buff_view=self.record.dynamic_buff_list" not in source
    assert "read_impact" in source


def test_qingyi_impact_state_sync_keeps_old_count_adjustment_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = _make_qingyi_impact_state_sync_case(
        monkeypatch,
        static_imp=150.0,
    )

    case.logic.special_hit_logic()

    assert case.expected_old_count == pytest.approx(180.0)
    assert case.get_prepared_calls == [{"char_CID": 1251, "enemy": 1, "sub_exist_buff_dict": 1}]
    assert case.aggregation_calls == [
        (case.expected_enabled_buff, None, case.active_buff.sim_instance, "青衣"),
        (case.expected_enabled_buff, None, case.active_buff.sim_instance, "青衣"),
    ]
    assert case.calls == [
        ("simple_start", 910, False, case.initial_count, case.buff_0),
        ("dy.count", case.initial_count + case.active_buff.ft.step),
        ("buff_0.dy.count", case.initial_count + case.active_buff.ft.step),
        ("buff_0.dy.count", case.initial_count),
        ("attribute_read",),
        ("dy.count", case.expected_old_count),
        ("update_to_buff_0", case.buff_0, case.expected_old_count),
        ("buff_0.dy.count", case.expected_old_count),
    ]
    _assert_final_count_writeback_order(
        case.calls,
        buff_0=case.buff_0,
        expected_count=case.expected_old_count,
    )
    assert case.active_buff.dy.count == pytest.approx(case.expected_old_count)
    assert case.buff_0.dy.count == pytest.approx(case.expected_old_count)


def test_qingyi_impact_state_sync_keeps_maxcount_cap_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = _make_qingyi_impact_state_sync_case(
        monkeypatch,
        static_imp=200.0,
        maxcount=120.0,
    )

    case.logic.special_hit_logic()

    assert case.expected_old_count == pytest.approx(120.0)
    assert case.calls == [
        ("simple_start", 910, False, case.initial_count, case.buff_0),
        ("dy.count", case.initial_count + case.active_buff.ft.step),
        ("buff_0.dy.count", case.initial_count + case.active_buff.ft.step),
        ("buff_0.dy.count", case.initial_count),
        ("attribute_read",),
        ("dy.count", case.expected_old_count),
        ("update_to_buff_0", case.buff_0, case.expected_old_count),
        ("buff_0.dy.count", case.expected_old_count),
    ]
    _assert_final_count_writeback_order(
        case.calls,
        buff_0=case.buff_0,
        expected_count=case.expected_old_count,
    )
    assert case.active_buff.dy.count == pytest.approx(case.expected_old_count)
    assert case.buff_0.dy.count == pytest.approx(case.expected_old_count)


def test_qingyi_impact_uses_reader_not_multiplier_data() -> None:
    source = Path(
        "zsim/sim_progress/Buff/BuffXLogic/QingYiAdditionalAbilityStunConvertToATK.py"
    ).read_text(encoding="utf-8")

    assert "MultiplierData" not in source
    assert "Calculator.StunMul.cal_imp" not in source
    assert "create_calculator_runtime_read_context_from_sim_instance" in source
    assert "get_calculator_buff_attribute_reader_service" in source
    assert "active_buff_view=self.record.dynamic_buff_list" not in source
    assert "read_impact" in source


def test_trigger_personal_crit_rate_inactive_gate_skips_state_sync_and_read(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = _make_trigger_personal_crit_rate_state_sync_case(
        monkeypatch,
        static_crit_rate=0.8,
    )
    case.aggregation_calls.clear()

    result = case.logic.special_judge_logic(skill_node=_trigger_skill_node(labels={}))

    assert result is False
    assert case.get_prepared_calls == [{"char_CID": 1361}]
    assert case.aggregation_calls == []
    assert case.calls == []
    assert case.active_buff.dy.count == pytest.approx(case.initial_count)
    assert case.buff_0.dy.count == pytest.approx(case.initial_count)


def test_trigger_personal_crit_rate_read_precedes_simple_start_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = _make_trigger_personal_crit_rate_state_sync_case(
        monkeypatch,
        static_crit_rate=0.55,
        field_crit_rate=0.05,
        received_crit_rate=0.4,
    )

    assert case.logic.special_judge_logic(skill_node=_trigger_skill_node()) is True
    case.logic.special_hit_logic()

    assert case.expected_old_count == pytest.approx(30.0)
    assert case.get_prepared_calls == [
        {"char_CID": 1361},
        {"char_CID": 1361, "sub_exist_buff_dict": 1, "enemy": 1},
    ]
    assert case.aggregation_calls == [
        (case.expected_enabled_buff, None, case.active_buff.sim_instance, "扳机"),
        (case.expected_enabled_buff, None, case.active_buff.sim_instance, "扳机"),
    ]
    assert case.calls == [
        ("attribute_read",),
        ("simple_start", 920, True, case.initial_count, case.buff_0),
        ("dy.count", case.expected_old_count),
        ("update_to_buff_0", case.buff_0, case.expected_old_count),
    ]
    _assert_final_count_writeback_order(
        case.calls,
        buff_0=case.buff_0,
        expected_count=case.expected_old_count,
    )
    assert case.active_buff.dy.count == pytest.approx(case.expected_old_count)
    assert case.buff_0.dy.count == pytest.approx(case.expected_old_count)


def test_trigger_personal_crit_rate_preserves_fractional_count(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = _make_trigger_personal_crit_rate_state_sync_case(
        monkeypatch,
        static_crit_rate=0.826,
    )

    case.logic.special_hit_logic()

    assert case.expected_old_count == pytest.approx(63.9)
    assert case.calls == [
        ("attribute_read",),
        ("simple_start", 920, True, case.initial_count, case.buff_0),
        ("dy.count", case.expected_old_count),
        ("update_to_buff_0", case.buff_0, case.expected_old_count),
    ]
    assert case.active_buff.dy.count == pytest.approx(case.expected_old_count)
    assert case.buff_0.dy.count == pytest.approx(case.expected_old_count)


def test_trigger_personal_crit_rate_keeps_count_cap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = _make_trigger_personal_crit_rate_state_sync_case(
        monkeypatch,
        static_crit_rate=1.2,
    )

    case.logic.special_hit_logic()

    assert case.expected_old_count == pytest.approx(75.0)
    assert case.calls == [
        ("attribute_read",),
        ("simple_start", 920, True, case.initial_count, case.buff_0),
        ("dy.count", case.expected_old_count),
        ("update_to_buff_0", case.buff_0, case.expected_old_count),
    ]
    _assert_final_count_writeback_order(
        case.calls,
        buff_0=case.buff_0,
        expected_count=case.expected_old_count,
    )
    assert case.active_buff.dy.count == pytest.approx(case.expected_old_count)
    assert case.buff_0.dy.count == pytest.approx(case.expected_old_count)


def test_trigger_personal_crit_rate_uses_reader_not_multiplier_data() -> None:
    source = Path(
        "zsim/sim_progress/Buff/BuffXLogic/TriggerAdditionalAbilityStunBonus.py"
    ).read_text(encoding="utf-8")

    assert "MultiplierData" not in source
    assert "Calculator.RegularMul.cal_personal_crit_rate" not in source
    assert "create_calculator_runtime_read_context_from_sim_instance" in source
    assert "get_calculator_buff_attribute_reader_service" in source
    assert "active_buff_view=self.record.dynamic_buff_list" not in source
    assert "read_personal_crit_rate" in source


def test_soldier0_anby_personal_crit_damage_inactive_gate_skips_state_sync_and_read(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = _make_soldier0_anby_personal_crit_damage_state_sync_case(
        monkeypatch,
        static_crit_damage=0.8,
        trigger_active=False,
    )
    case.aggregation_calls.clear()

    result = case.logic.special_judge_logic()

    assert result is False
    assert case.get_prepared_calls == [
        {"char_CID": 1381, "trigger_buff_0": ("零号·安比", "Buff-角色-零号·安比-银星触发器")}
    ]
    assert case.aggregation_calls == []
    assert case.calls == []
    assert case.active_buff.dy.count == pytest.approx(case.initial_count)
    assert case.buff_0.dy.count == pytest.approx(case.initial_count)


def test_soldier0_anby_personal_crit_damage_simple_start_precedes_read_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = _make_soldier0_anby_personal_crit_damage_state_sync_case(
        monkeypatch,
        static_crit_damage=0.5,
        field_crit_damage=0.2,
        flat_crit_damage=0.3,
        received_crit_damage=0.4,
    )

    assert case.logic.special_judge_logic() is True
    case.logic.special_hit_logic()

    assert case.expected_old_count == pytest.approx(30.0)
    assert case.get_prepared_calls == [
        {"char_CID": 1381, "trigger_buff_0": ("零号·安比", "Buff-角色-零号·安比-银星触发器")},
        {"char_CID": 1381, "enemy": 1, "sub_exist_buff_dict": 1},
    ]
    assert case.aggregation_calls == [
        (case.expected_enabled_buff, None, case.active_buff.sim_instance, "零号·安比"),
        (case.expected_enabled_buff, None, case.active_buff.sim_instance, "零号·安比"),
    ]
    assert case.calls == [
        ("simple_start", 930, True, case.initial_count, case.buff_0),
        ("attribute_read",),
        ("dy.count", case.expected_old_count),
        ("update_to_buff_0", case.buff_0, case.expected_old_count),
    ]
    _assert_final_count_writeback_order(
        case.calls,
        buff_0=case.buff_0,
        expected_count=case.expected_old_count,
    )
    assert case.active_buff.dy.count == pytest.approx(case.expected_old_count)
    assert case.buff_0.dy.count == pytest.approx(case.expected_old_count)


def test_soldier0_anby_personal_crit_damage_keeps_uncapped_high_count(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = _make_soldier0_anby_personal_crit_damage_state_sync_case(
        monkeypatch,
        static_crit_damage=2.0,
        field_crit_damage=0.5,
        flat_crit_damage=0.5,
        received_crit_damage=1.0,
    )

    assert case.logic.special_judge_logic() is True
    case.logic.special_hit_logic()

    assert case.expected_old_count == pytest.approx(90.0)
    assert case.active_buff.dy.count == pytest.approx(case.expected_old_count)
    assert case.buff_0.dy.count == pytest.approx(case.expected_old_count)
    assert case.calls == [
        ("simple_start", 930, True, case.initial_count, case.buff_0),
        ("attribute_read",),
        ("dy.count", case.expected_old_count),
        ("update_to_buff_0", case.buff_0, case.expected_old_count),
    ]
    _assert_final_count_writeback_order(
        case.calls,
        buff_0=case.buff_0,
        expected_count=case.expected_old_count,
    )


def test_soldier0_anby_personal_crit_damage_uses_reader_not_multiplier_data_alias() -> None:
    source = Path(
        "zsim/sim_progress/Buff/BuffXLogic/Soldier0AnbyCoreSkillCritDMGBonus.py"
    ).read_text(encoding="utf-8")

    assert "MultiplierData" not in source
    assert "MultiplierData as Mul" not in source
    assert "Mul(" not in source
    assert "Calculator.RegularMul.cal_personal_crit_dmg" not in source
    assert "Cal.RegularMul.cal_personal_crit_dmg" not in source
    assert "create_calculator_runtime_read_context_from_sim_instance" in source
    assert "get_calculator_buff_attribute_reader_service" in source
    assert "active_buff_view=self.record.dynamic_buff_list" not in source
    assert "read_personal_crit_damage" in source


def test_alice_additional_ability_uses_reader_not_multiplier_data() -> None:
    source = Path("zsim/sim_progress/Buff/BuffXLogic/AliceAdditionalAbilityApBonus.py").read_text(
        encoding="utf-8"
    )

    assert "MultiplierData" not in source
    assert "Calculator.AnomalyMul.cal_am" not in source
    assert "create_calculator_runtime_read_context_from_sim_instance" in source
    assert "get_calculator_buff_attribute_reader_service" in source
    assert "active_buff_view=self.record.dynamic_buff_list" not in source
    assert "read_anomaly_mastery" in source


def test_yuzuha_buildup_uses_reader_not_multiplier_data() -> None:
    source = Path(
        "zsim/sim_progress/Buff/BuffXLogic/YuzuhaAdditionalAbilityAnomalyBuildupBonus.py"
    ).read_text(encoding="utf-8")

    assert "MultiplierData" not in source
    assert "Calculator.AnomalyMul.cal_am" not in source
    assert "create_calculator_runtime_read_context_from_sim_instance" in source
    assert "get_calculator_buff_attribute_reader_service" in source
    assert "active_buff_view=self.record.dynamic_buff_list" not in source
    assert "read_anomaly_mastery" in source


def test_yuzuha_additional_ability_damage_uses_shared_reader_pattern() -> None:
    buildup_source = Path(
        "zsim/sim_progress/Buff/BuffXLogic/YuzuhaAdditionalAbilityAnomalyBuildupBonus.py"
    ).read_text(encoding="utf-8")
    damage_source = Path(
        "zsim/sim_progress/Buff/BuffXLogic/YuzuhaAdditionalAbilityAnomalyDmgBonus.py"
    ).read_text(encoding="utf-8")

    for source in (buildup_source, damage_source):
        assert "MultiplierData" not in source
        assert "Calculator.AnomalyMul.cal_am" not in source
        assert "create_calculator_runtime_read_context_from_sim_instance" in source
        assert "get_calculator_buff_attribute_reader_service" in source
        assert "active_buff_view=self.record.dynamic_buff_list" not in source
        assert "read_anomaly_mastery" in source


def test_jane_cinema1_uses_reader_not_multiplier_data_alias() -> None:
    source = Path("zsim/sim_progress/Buff/BuffXLogic/JaneCinema1APTransToDmgBonus.py").read_text(
        encoding="utf-8"
    )

    assert "MultiplierData as Mul" not in source
    assert "Mul(" not in source
    assert "Calculator.AnomalyMul.cal_ap" not in source
    assert "create_calculator_runtime_read_context_from_sim_instance" in source
    assert "get_calculator_buff_attribute_reader_service" in source
    assert "active_buff_view=self.record.dynamic_buff_list" not in source
    assert "read_anomaly_proficiency" in source


def test_jane_core_skill_crit_rate_uses_reader_not_multiplier_data_alias() -> None:
    source = Path(
        "zsim/sim_progress/Buff/BuffXLogic/JaneCoreSkillStrikeCritRateBonus.py"
    ).read_text(encoding="utf-8")

    assert "MultiplierData as Mul" not in source
    assert "Mul(" not in source
    assert "Cal.AnomalyMul.cal_ap" not in source
    assert "Calculator.AnomalyMul.cal_ap" not in source
    assert "create_calculator_runtime_read_context_from_sim_instance" in source
    assert "get_calculator_buff_attribute_reader_service" in source
    assert "active_buff_view=self.record.dynamic_buff_list" not in source
    assert "read_anomaly_proficiency" in source


def test_jane_passion_state_uses_reader_not_multiplier_data_alias() -> None:
    source = Path("zsim/sim_progress/Buff/BuffXLogic/JanePassionStateAPTransToATK.py").read_text(
        encoding="utf-8"
    )

    assert "MultiplierData as Mul" not in source
    assert "Mul(" not in source
    assert "Cal.AnomalyMul.cal_ap" not in source
    assert "Calculator.AnomalyMul.cal_ap" not in source
    assert "create_calculator_runtime_read_context_from_sim_instance" in source
    assert "get_calculator_buff_attribute_reader_service" in source
    assert "active_buff_view=self.record.dynamic_buff_list" not in source
    assert "read_anomaly_proficiency" in source
