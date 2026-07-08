from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import numpy as np
import pytest

import zsim.sim_progress.calculation.anomaly_calculator as cal_anomaly_module
from zsim.sim_progress.anomaly_bar import AnomalyBar
from zsim.sim_progress.Buff import Buff
from zsim.sim_progress.calculation.calculator import MultiplierData
from zsim.sim_progress.data_struct.data_analyzer import cal_buff_total_bonus

_FINAL_MULTIPLIER_ORDER = (
    "base_dmg",
    "dmg_bonus",
    "am_mul",
    "k_level",
    "anomaly_bonus",
    "active_crit",
    "def_mul",
    "res_mul",
    "vulnerability_mul",
    "snapshot_impact",
    "snapshot_stun_bonus",
    "stun_vulnerability",
    "special_mul",
)


class _HashableNamespace(SimpleNamespace):
    __hash__ = object.__hash__


@pytest.fixture(autouse=True)
def _clear_formula_caches() -> None:
    MultiplierData.mul_data_cache.clear()
    MultiplierData.StaticStatement._instance_cache.clear()
    cal_buff_total_bonus.cache_clear()


def _make_statement(**values: float) -> SimpleNamespace:
    statement = SimpleNamespace(statement=dict(values))
    for key, value in values.items():
        setattr(statement, key, value)
    return statement


def _make_character(name: str = "异常公式Oracle") -> SimpleNamespace:
    return SimpleNamespace(
        NAME=name,
        CID=999001,
        level=60,
        statement=_make_statement(
            ATK=0.0,
            HP=0.0,
            DEF=0.0,
            AM=0.0,
            AP=0.0,
            IMP=0.0,
            CRIT_rate=0.0,
            CRIT_damage=0.0,
            PEN_ratio=0.0,
            PEN_numeric=0.0,
        ),
    )


def _make_enemy(sim_instance: Any) -> SimpleNamespace:
    return SimpleNamespace(
        dynamic=SimpleNamespace(
            dynamic_debuff_list=[],
            dynamic_dot_list=[],
            stun=True,
        ),
        sim_instance=sim_instance,
        max_DEF=600.0,
        stun_DMG_take_ratio=0.45,
        PHY_damage_resistance=0.22,
        FIRE_damage_resistance=0.0,
        ICE_damage_resistance=0.0,
        ELECTRIC_damage_resistance=0.0,
        ETHER_damage_resistance=0.0,
    )


def _make_active_buff(effect_dct: dict[str, float]) -> Buff:
    buff = Buff.__new__(Buff)
    buff.ft = SimpleNamespace(
        index="Buff-测试-异常公式乘区",
        label={},
        beneficiary="异常公式Oracle",
    )
    buff.dy = SimpleNamespace(active=True, count=1)
    buff.effect_dct = effect_dct
    buff.sim_instance = _HashableNamespace()
    return buff


def _make_settled_anomaly_bar(
    sim_instance: Any,
    character: Any,
    *,
    snapshot_values: tuple[float, ...],
    scaling_factor: float,
) -> AnomalyBar:
    bar = AnomalyBar(sim_instance=sim_instance, element_type=0)
    bar.current_ndarray = np.array([snapshot_values], dtype=np.float64)
    bar.settled = True
    bar.scaling_factor = scaling_factor
    bar.activated_by = SimpleNamespace(
        char_name=character.NAME,
        skill_tag="999001_ANOMALY_ORACLE",
        skill=SimpleNamespace(char_obj=character),
    )
    return bar


def _build_calculator(
    *,
    snapshot_values: tuple[float, ...] = (
        120.0,
        1.15,
        2.25,
        60.0,
        1.35,
        999.0,
        0.07,
        12.0,
        0.09,
        1.20,
        1.40,
    ),
    scaling_factor: float = 1.75,
) -> cal_anomaly_module.CalAnomaly:
    sim_instance = _HashableNamespace(tick=240)
    character = _make_character()
    enemy = _make_enemy(sim_instance)
    anomaly_bar = _make_settled_anomaly_bar(
        sim_instance,
        character,
        snapshot_values=snapshot_values,
        scaling_factor=scaling_factor,
    )
    buff = _make_active_buff(
        {
            "强击暴击率增加": 0.30,
            "强击暴击伤害增加": 0.50,
            "强击无视防御": 0.04,
            "百分比减防": 0.20,
            "固定减防": 40.0,
            "穿透率": 0.10,
            "穿透值": 25.0,
            "物理伤害抗性降低": 0.08,
            "物理抗性穿透": 0.03,
            "全属性伤害抗性降低": 0.06,
            "全属性抗性穿透": 0.02,
            "物理易伤": 0.14,
            "全易伤": 0.11,
            "失衡易伤增加": 0.20,
            "全时段失衡易伤增加": 0.05,
            "特殊乘区": 0.07,
        }
    )

    return cal_anomaly_module.CalAnomaly(
        anomaly_obj=anomaly_bar,
        enemy_obj=enemy,
        dynamic_buff={character.NAME: [buff]},
        sim_instance=sim_instance,
    )


def test_cal_anomaly_public_entry_point_assembles_current_physical_damage_vector() -> None:
    calculator = _build_calculator()

    expected_multipliers = np.array(
        [
            120.0,
            1.15,
            2.25,
            2.0,
            1.35,
            1.15,
            0.7188122397247874,
            1.06,
            1.25,
            1.20,
            1.40,
            1.70,
            1.07,
        ],
        dtype=np.float64,
    )

    assert calculator.dmg_sp is calculator.anomaly_obj.current_ndarray
    assert calculator.final_multipliers.shape == (len(_FINAL_MULTIPLIER_ORDER),)
    np.testing.assert_allclose(calculator.final_multipliers, expected_multipliers)
    assert {
        label: calculator.final_multipliers[index]
        for index, label in enumerate(_FINAL_MULTIPLIER_ORDER)
    } == pytest.approx(
        {label: expected_multipliers[index] for index, label in enumerate(_FINAL_MULTIPLIER_ORDER)}
    )

    expected_damage = (
        np.prod(expected_multipliers)
        / (expected_multipliers[9] * expected_multipliers[10])
        * calculator.anomaly_obj.scaling_factor
    )
    assert calculator.cal_anomaly_dmg() == pytest.approx(expected_damage)


def test_cal_anomaly_damage_applies_scaling_factor_after_snapshot_stun_terms_cancel() -> None:
    base = _build_calculator(scaling_factor=1.0)
    scaled = _build_calculator(scaling_factor=2.5)

    np.testing.assert_allclose(base.final_multipliers, scaled.final_multipliers)
    assert scaled.cal_anomaly_dmg() == pytest.approx(base.cal_anomaly_dmg() * 2.5)


@pytest.mark.parametrize(
    ("input_level", "expected", "expected_messages"),
    [
        (-7, 0.0, ("角色等级-7过低，将被设置为0",)),
        (0, 0.0, ()),
        (60, 2.0, ()),
        (83, 2.0, ("角色等级83过高，将被设置为60",)),
    ],
)
def test_cal_anomaly_level_lookup_clamps_to_current_retained_table(
    monkeypatch: pytest.MonkeyPatch,
    input_level: int,
    expected: float,
    expected_messages: tuple[str, ...],
) -> None:
    log_messages: list[str] = []
    monkeypatch.setattr(cal_anomaly_module, "report_to_log", log_messages.append)

    assert cal_anomaly_module.CalAnomaly.cal_k_level(input_level) == pytest.approx(expected)
    assert tuple(log_messages) == expected_messages
