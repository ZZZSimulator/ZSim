from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any, Iterator, cast

import numpy as np
import pytest

import zsim.sim_progress.calculation.anomaly_calculator as cal_anomaly_module
import zsim.sim_progress.calculation.calculator as calculator_module
from zsim.sim_progress.anomaly_bar import AnomalyBar
from zsim.sim_progress.anomaly_bar.CopyAnomalyForOutput import (
    Disorder,
    PolarityDisorder,
)
from zsim.sim_progress.calculation.anomaly_calculator import (
    CalDisorder,
    CalPolarityDisorder,
)
from zsim.sim_progress.calculation.calculator import Calculator, MultiplierData


@dataclass(frozen=True)
class _DisorderCase:
    case_id: str
    element_type: int
    base_mul: float
    element_disorder_basic_attr: str
    expected_base_dmg: float


@dataclass(frozen=True)
class _DisorderFixture:
    sim_instance: SimpleNamespace
    character: SimpleNamespace
    activation: SimpleNamespace
    enemy: SimpleNamespace
    active_buff_view: dict[str, list[object]]
    anomaly_bar: AnomalyBar


_DISORDER_COMMON_DYNAMIC_ATTRS = {
    "all_disorder_basic_mul": 0.10,
    "disorder_dmg_mul": 0.45,
    "stun_res": 0.12,
    "received_stun_increase": 0.16,
}

_DISORDER_CASES = (
    _DisorderCase(
        case_id="physical-strike-floor-seconds",
        element_type=0,
        base_mul=713.0,
        element_disorder_basic_attr="strike_disorder_basic_mul",
        expected_base_dmg=517.5,
    ),
    _DisorderCase(
        case_id="fire-burn-half-second-floor",
        element_type=1,
        base_mul=50.0,
        element_disorder_basic_attr="burn_disorder_basic_mul",
        expected_base_dmg=980.0,
    ),
    _DisorderCase(
        case_id="ice-frostbite-floor-seconds",
        element_type=2,
        base_mul=500.0,
        element_disorder_basic_attr="frostbite_disorder_basic_mul",
        expected_base_dmg=517.5,
    ),
    _DisorderCase(
        case_id="electric-shock-floor-seconds",
        element_type=3,
        base_mul=125.0,
        element_disorder_basic_attr="shock_disorder_basic_mul",
        expected_base_dmg=1105.0,
    ),
    _DisorderCase(
        case_id="ether-chaos-half-second-floor",
        element_type=4,
        base_mul=62.5,
        element_disorder_basic_attr="chaos_disorder_basic_mul",
        expected_base_dmg=1105.0,
    ),
    _DisorderCase(
        case_id="auric-ink-frostbite-floor-seconds",
        element_type=5,
        base_mul=500.0,
        element_disorder_basic_attr="frostbite_disorder_basic_mul",
        expected_base_dmg=1005.0,
    ),
    _DisorderCase(
        case_id="auric-ether-chaos-half-second-floor",
        element_type=6,
        base_mul=62.5,
        element_disorder_basic_attr="chaos_disorder_basic_mul",
        expected_base_dmg=1105.0,
    ),
)


def _reset_formula_oracle_caches() -> None:
    MultiplierData.mul_data_cache.clear()
    MultiplierData.StaticStatement._instance_cache.clear()
    Calculator.AnomalyMul.cal_ap.cache_clear()


@pytest.fixture(autouse=True)
def _reset_formula_fixture_state() -> Iterator[None]:
    _reset_formula_oracle_caches()
    yield
    _reset_formula_oracle_caches()


def _make_character(*, name: str = "异常公式角色", ap: float = 0.0) -> SimpleNamespace:
    statement = SimpleNamespace(statement={"AP": ap}, AP=ap)
    return SimpleNamespace(
        NAME=name,
        CID=1301,
        level=60,
        statement=statement,
        crit_balancing=False,
    )


def _make_enemy() -> SimpleNamespace:
    return SimpleNamespace(
        dynamic=SimpleNamespace(
            dynamic_debuff_list=[],
            dynamic_dot_list=[],
            stun=False,
        ),
        sim_instance=SimpleNamespace(marker="enemy-sim"),
        max_DEF=0.0,
        stun_DMG_take_ratio=0.0,
        anomaly_resistance_dict={},
        stun_resistance_dict={},
        PHY_damage_resistance=0.0,
        FIRE_damage_resistance=0.0,
        ICE_damage_resistance=0.0,
        ELECTRIC_damage_resistance=0.0,
        ETHER_damage_resistance=0.0,
    )


def _make_disorder_snapshot(base_mul: float) -> np.ndarray:
    return np.array(
        [
            [
                base_mul,
                1.11,
                2.20,
                60.0,
                9.99,
                777.0,
                0.0,
                0.0,
                0.0,
                1.25,
                1.35,
            ]
        ],
        dtype=np.float64,
    )


def _make_settled_anomaly_fixture(
    *,
    element_type: int,
    base_mul: float,
) -> _DisorderFixture:
    sim_instance = SimpleNamespace(tick=300)
    character = _make_character()
    activation = SimpleNamespace(skill=SimpleNamespace(char_obj=character))
    enemy = _make_enemy()
    active_buff_view: dict[str, list[object]] = {character.NAME: []}
    anomaly_bar = AnomalyBar(
        sim_instance=cast(Any, sim_instance),
        element_type=element_type,
    )
    anomaly_bar.current_ndarray = _make_disorder_snapshot(base_mul)
    anomaly_bar.current_effective_anomaly = np.float64(30.0)
    anomaly_bar.current_anomaly = np.float64(129.0)
    anomaly_bar.max_duration = 500
    anomaly_bar.last_active = 115
    anomaly_bar.settled = True
    anomaly_bar.activated_by = cast(Any, activation)
    anomaly_bar.scaling_factor = 1.0
    enemy.stun_resistance_dict[element_type] = 0.18
    return _DisorderFixture(
        sim_instance=sim_instance,
        character=character,
        activation=activation,
        enemy=enemy,
        active_buff_view=active_buff_view,
        anomaly_bar=anomaly_bar,
    )


def _dynamic_statement_by_attr(**attrs: float) -> dict[str, float]:
    effect_by_attr = {
        cast(str, attr): cast(str, effect)
        for effect, attr in calculator_module.buff_effect_trans.items()
    }
    return {effect_by_attr[attr]: value for attr, value in attrs.items()}


def _patch_buff_aggregation(
    monkeypatch: pytest.MonkeyPatch,
    dynamic_statement: dict[str, float],
) -> list[tuple[tuple[object, ...], object | None, object, str | None]]:
    aggregation_calls: list[tuple[tuple[object, ...], object | None, object, str | None]] = []

    def fake_cal_buff_total_bonus(
        *,
        enabled_buff: tuple[object, ...],
        judge_obj: object | None,
        sim_instance: object,
        char_name: str | None,
    ) -> dict[str, float]:
        aggregation_calls.append((enabled_buff, judge_obj, sim_instance, char_name))
        return dict(dynamic_statement)

    monkeypatch.setattr(
        calculator_module,
        "cal_buff_total_bonus",
        fake_cal_buff_total_bonus,
    )
    return aggregation_calls


def _disorder_dynamic_attrs(case: _DisorderCase) -> dict[str, float]:
    return {
        **_DISORDER_COMMON_DYNAMIC_ATTRS,
        case.element_disorder_basic_attr: 0.20,
    }


def _make_disorder_calculator(
    monkeypatch: pytest.MonkeyPatch,
    case: _DisorderCase,
) -> tuple[CalDisorder, Disorder, _DisorderFixture]:
    fixture = _make_settled_anomaly_fixture(
        element_type=case.element_type,
        base_mul=case.base_mul,
    )
    _patch_buff_aggregation(
        monkeypatch,
        _dynamic_statement_by_attr(**_disorder_dynamic_attrs(case)),
    )
    disorder_payload = Disorder(
        fixture.anomaly_bar,
        active_by=cast(Any, fixture.activation),
        sim_instance=cast(Any, fixture.sim_instance),
    )
    calculator = CalDisorder(
        disorder_obj=disorder_payload,
        enemy_obj=cast(Any, fixture.enemy),
        dynamic_buff=fixture.active_buff_view,
        sim_instance=cast(Any, fixture.sim_instance),
    )
    return calculator, disorder_payload, fixture


@pytest.mark.parametrize("case", _DISORDER_CASES, ids=lambda case: case.case_id)
def test_cal_disorder_current_base_damage_for_each_supported_element(
    monkeypatch: pytest.MonkeyPatch,
    case: _DisorderCase,
) -> None:
    calculator, disorder_payload, _ = _make_disorder_calculator(monkeypatch, case)

    assert disorder_payload.remaining_tick() == pytest.approx(315)
    assert calculator.cal_disorder_base_dmg(np.float64(case.base_mul)) == pytest.approx(
        case.expected_base_dmg
    )
    assert calculator.final_multipliers[0] == pytest.approx(case.expected_base_dmg)


@pytest.mark.parametrize("case", _DISORDER_CASES, ids=lambda case: case.case_id)
def test_cal_disorder_current_extra_multiplier_and_stun(
    monkeypatch: pytest.MonkeyPatch,
    case: _DisorderCase,
) -> None:
    calculator, _, _ = _make_disorder_calculator(monkeypatch, case)

    assert calculator.cal_disorder_extra_mul() == pytest.approx(1.45)
    assert calculator.final_multipliers[4] == pytest.approx(1.45)
    assert calculator.cal_disorder_stun() == pytest.approx(3.973725)
    np.testing.assert_allclose(
        calculator.final_multipliers,
        np.array(
            [
                case.expected_base_dmg,
                1.11,
                2.20,
                2.0,
                1.45,
                1.0,
                1.0,
                1.0,
                1.0,
                1.25,
                1.35,
                1.0,
                1.0,
            ],
            dtype=np.float64,
        ),
    )


def test_cal_polarity_disorder_current_ratio_and_yanagi_ap_additional_term(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = _DISORDER_CASES[3]
    fixture = _make_settled_anomaly_fixture(
        element_type=case.element_type,
        base_mul=case.base_mul,
    )
    dynamic_attrs = {
        **_disorder_dynamic_attrs(case),
        "field_anomaly_proficiency": 0.25,
        "anomaly_proficiency": 60.0,
    }
    aggregation_calls = _patch_buff_aggregation(
        monkeypatch,
        _dynamic_statement_by_attr(**dynamic_attrs),
    )

    class _YanagiFormulaProbe(SimpleNamespace):
        pass

    monkeypatch.setattr(cal_anomaly_module, "Yanagi", _YanagiFormulaProbe)
    yanagi = _YanagiFormulaProbe(
        NAME="柳",
        CID=1221,
        level=60,
        statement=_make_character(name="柳", ap=400.0).statement,
    )
    fixture.sim_instance.char_data = SimpleNamespace(char_obj_dict={"柳": yanagi})
    fixture.active_buff_view[yanagi.NAME] = []

    polarity_payload = PolarityDisorder(
        fixture.anomaly_bar,
        0.13,
        active_by=cast(Any, fixture.activation),
        sim_instance=cast(Any, fixture.sim_instance),
    )
    polarity_payload.additional_dmg_ap_ratio = 17.5
    calculator = CalPolarityDisorder(
        disorder_obj=polarity_payload,
        enemy_obj=cast(Any, fixture.enemy),
        dynamic_buff=fixture.active_buff_view,
        sim_instance=cast(Any, fixture.sim_instance),
    )

    expected_yanagi_ap = 400.0 * (1 + 0.25) + 60.0
    expected_polarity_base = (case.expected_base_dmg * 0.13) + (expected_yanagi_ap * 17.5)
    assert aggregation_calls == [
        ((), polarity_payload, fixture.enemy.sim_instance, fixture.character.NAME),
        ((), None, fixture.enemy.sim_instance, yanagi.NAME),
    ]
    assert Calculator.AnomalyMul.cal_ap(
        MultiplierData(
            enemy_obj=cast(Any, fixture.enemy),
            dynamic_buff=fixture.active_buff_view,
            character_obj=yanagi,
        )
    ) == pytest.approx(expected_yanagi_ap)
    assert calculator.cal_polarity_disorder_base_dmg(
        np.float64(case.expected_base_dmg),
        np.float64(expected_yanagi_ap),
        polarity_disorder_ratio=polarity_payload.polarity_disorder_ratio,
        additional_dmg_ap_ratio=polarity_payload.additional_dmg_ap_ratio,
    ) == pytest.approx(expected_polarity_base)
    assert calculator.final_multipliers[0] == pytest.approx(expected_polarity_base)
    assert calculator.cal_anomaly_dmg() == pytest.approx(
        np.prod(calculator.final_multipliers)
        / (calculator.final_multipliers[9] * calculator.final_multipliers[10])
    )
