from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import numpy as np
import pytest

import zsim.sim_progress.calculation.calculator as calculator_module
from zsim.sim_progress.calculation.calculator import Calculator
from zsim.sim_progress.calculation.identities import FROST_DAMAGE, ICE_AFFINITY
from zsim.sim_progress.calculation.inputs.regular import (
    RegularDamageBonusInput,
    RegularDamageMultipliers,
)


def _static_statement() -> SimpleNamespace:
    return SimpleNamespace(
        atk=100.0,
        hp=200.0,
        defense=300.0,
        ap=400.0,
        crit_rate=0.10,
        crit_damage=0.50,
        pen_ratio=0.05,
        pen_numeric=11.0,
        phy_dmg_bonus=0.01,
        fire_dmg_bonus=0.02,
        ice_dmg_bonus=0.03,
        electric_dmg_bonus=0.04,
        ether_dmg_bonus=0.05,
    )


def _dynamic_statement() -> SimpleNamespace:
    return SimpleNamespace(
        atk=10.0,
        hp=20.0,
        defense=30.0,
        anomaly_proficiency=40.0,
        field_atk_percentage=0.10,
        field_hp_percentage=0.20,
        field_def_percentage=0.30,
        field_anomaly_proficiency=0.40,
        extra_damage_ratio=0.50,
        base_dmg_increase_percentage=0.60,
        base_dmg_increase=70.0,
        sheer_atk=8.0,
        field_sheer_atk_percentage=0.0,
        crit_rate=0.20,
        field_crit_rate=0.30,
        crit_rate_received_increase=0.40,
        crit_dmg=0.60,
        field_crit_dmg=0.70,
        received_crit_dmg_bonus=0.80,
        aftershock_attack_crit_dmg_bonus=0.90,
        phy_dmg_bonus=0.11,
        fire_dmg_bonus=0.12,
        ice_dmg_bonus=0.13,
        electric_dmg_bonus=0.14,
        ether_dmg_bonus=0.15,
        normal_attack_dmg_bonus=0.21,
        special_skill_dmg_bonus=0.22,
        ex_special_skill_dmg_bonus=0.23,
        dash_attack_dmg_bonus=0.24,
        counter_attack_dmg_bonus=0.25,
        qte_dmg_bonus=0.26,
        ultimate_dmg_bonus=0.27,
        quick_aid_dmg_bonus=0.28,
        defensive_aid_dmg_bonus=0.29,
        assault_aid_dmg_bonus=0.30,
        all_dmg_bonus=0.31,
        aftershock_attack_dmg_bonus=0.32,
        pen_ratio=0.06,
        pen_numeric=12.0,
        percentage_def_reduction=0.07,
        def_reduction=13.0,
        physical_dmg_res_decrease=0.01,
        fire_dmg_res_decrease=0.02,
        ice_dmg_res_decrease=0.03,
        electric_dmg_res_decrease=0.04,
        ether_dmg_res_decrease=0.05,
        physical_res_pen_increase=0.06,
        fire_res_pen_increase=0.07,
        ice_res_pen_increase=0.08,
        electric_res_pen_increase=0.09,
        ether_res_pen_increase=0.10,
        all_dmg_res_decrease=0.11,
        all_res_pen_increase=0.12,
        physical_vulnerability=0.13,
        fire_vulnerability=0.14,
        ice_vulnerability=0.15,
        electric_vulnerability=0.16,
        ether_vulnerability=0.17,
        all_vulnerability=0.18,
        stun_vulnerability_increase=0.19,
        stun_vulnerability_increase_all_time=0.20,
        special_multiplier_zone=0.21,
        sheer_dmg_bonus=0.22,
    )


def _skill_node(*, element_type: int = 5, diff_multiplier: int = 0) -> SimpleNamespace:
    return SimpleNamespace(
        element_type=element_type,
        hit_times=2,
        skill=SimpleNamespace(
            damage_ratio=4.0,
            diff_multiplier=diff_multiplier,
            trigger_buff_level=2,
            labels={"aftershock_attack": 1},
        ),
    )


def test_damage_bonus_wrapper_assembles_regular_domain_input(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: list[RegularDamageBonusInput] = []

    def fake_calculate(input_snapshot: RegularDamageBonusInput) -> float:
        captured.append(input_snapshot)
        return 9.87

    monkeypatch.setattr(
        calculator_module,
        "calculate_regular_damage_bonus",
        fake_calculate,
    )

    result = calculator_module._calculate_damage_bonus(
        _static_statement(),
        _dynamic_statement(),
        _skill_node(element_type=5),
    )

    assert result == pytest.approx(9.87)
    assert len(captured) == 1
    input_snapshot = captured[0]
    assert input_snapshot.identity.damage_identity == FROST_DAMAGE
    assert input_snapshot.identity.multiplier_affinity == ICE_AFFINITY
    assert input_snapshot.static_damage_bonuses.get(ICE_AFFINITY) == pytest.approx(0.03)
    assert input_snapshot.dynamic_damage_bonuses.get(ICE_AFFINITY) == pytest.approx(0.13)
    assert input_snapshot.trigger_buff_level == 2
    assert input_snapshot.trigger_damage_bonuses[2] == pytest.approx(0.23)
    assert input_snapshot.aftershock_attack is True
    assert input_snapshot.aftershock_attack_damage_bonus == pytest.approx(0.32)


def test_defense_private_wrappers_preserve_level_log_and_delegate_to_domain_helpers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    level_calls: list[int] = []
    recipient_calls: list[tuple[Any, ...]] = []
    log_messages: list[str] = []

    def fake_level_coefficient(attacker_level: int) -> int:
        level_calls.append(attacker_level)
        return 794

    def fake_recipient_defense(
        max_defense: float,
        percentage_defense_reduction: float,
        flat_defense_reduction: float,
        static_pen_numeric: float,
        dynamic_pen_numeric: float,
        pen_ratio: float,
        *,
        addon_pen_ratio: float = 0.0,
        addon_pen_numeric: float = 0.0,
    ) -> float:
        recipient_calls.append(
            (
                max_defense,
                percentage_defense_reduction,
                flat_defense_reduction,
                static_pen_numeric,
                dynamic_pen_numeric,
                pen_ratio,
                addon_pen_ratio,
                addon_pen_numeric,
            )
        )
        return 222.0

    monkeypatch.setattr(
        calculator_module,
        "calculate_attacker_level_coefficient",
        fake_level_coefficient,
    )
    monkeypatch.setattr(
        calculator_module,
        "calculate_recipient_defense",
        fake_recipient_defense,
    )
    monkeypatch.setattr(
        calculator_module,
        "report_to_log",
        lambda message, *args, **kwargs: log_messages.append(message),
    )
    enemy = SimpleNamespace(max_DEF=1234.0)

    assert calculator_module._calculate_attacker_level_coefficient(99) == 794
    assert log_messages == ["角色等级99过高，将被设置为60"]
    assert level_calls == [60]

    result = calculator_module._calculate_recipient_defense(
        enemy,
        _static_statement(),
        _dynamic_statement(),
        pen_ratio=0.25,
        addon_pen_ratio=0.02,
        addon_pen_numeric=3.0,
    )

    assert result == pytest.approx(222.0)
    assert recipient_calls == [
        (
            1234.0,
            0.07,
            13.0,
            11.0,
            12.0,
            0.25,
            0.02,
            3.0,
        )
    ]


def test_regular_arrays_and_public_damage_methods_delegate_to_domain_products(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    regular = Calculator.RegularMul.__new__(Calculator.RegularMul)
    regular.base_dmg = 100.0
    regular.dmg_bonus = 1.2
    regular.crit_rate = 0.5
    regular.crit_dmg = 0.8
    regular.crit_expect = 1.4
    regular.defense_mul = 0.7
    regular.res_mul = 1.1
    regular.dmg_vulnerability = 1.3
    regular.stun_vulnerability = 1.4
    regular.special_multiplier_zone = 1.5
    regular.sheer_dmg_bonus = 1.6
    expected_multipliers = RegularDamageMultipliers(
        base_damage=100.0,
        damage_bonus=1.2,
        crit_rate=0.5,
        crit_damage=0.8,
        crit_expectation=1.4,
        defense_multiplier=0.7,
        resistance_multiplier=1.1,
        damage_vulnerability_multiplier=1.3,
        stun_vulnerability_multiplier=1.4,
        special_multiplier=1.5,
        sheer_damage_bonus=1.6,
    )

    array_calls: list[tuple[RegularDamageMultipliers, str]] = []
    product_calls: list[tuple[RegularDamageMultipliers, str]] = []

    def fake_array(
        multipliers: RegularDamageMultipliers,
        *,
        mode: str = "expect",
    ) -> np.ndarray:
        array_calls.append((multipliers, mode))
        return np.array([{"expect": 1.0, "crit": 2.0, "not_crit": 3.0}[mode]])

    def fake_product(
        multipliers: RegularDamageMultipliers,
        *,
        mode: str = "expect",
    ) -> np.float64:
        product_calls.append((multipliers, mode))
        return np.float64({"expect": 10.0, "crit": 20.0, "not_crit": 30.0}[mode])

    monkeypatch.setattr(
        calculator_module,
        "assemble_regular_damage_multiplier_array",
        fake_array,
    )
    monkeypatch.setattr(
        calculator_module,
        "calculate_regular_damage_product",
        fake_product,
    )
    monkeypatch.setattr(calculator_module, "CHECK_SKILL_MUL", False)

    np.testing.assert_allclose(regular.get_array_expect(), np.array([1.0]))
    np.testing.assert_allclose(regular.get_array_crit(), np.array([2.0]))
    np.testing.assert_allclose(regular.get_array_not_crit(), np.array([3.0]))

    calculator = Calculator.__new__(Calculator)
    calculator.regular_multipliers = regular
    calculator.skill_tag = "ADAPTER_TEST"
    calculator.skill_node = SimpleNamespace()

    assert calculator.cal_dmg_expect() == pytest.approx(10.0)
    assert calculator.cal_dmg_crit() == pytest.approx(20.0)
    assert calculator.cal_dmg_not_crit() == pytest.approx(30.0)
    assert array_calls == [
        (expected_multipliers, "expect"),
        (expected_multipliers, "crit"),
        (expected_multipliers, "not_crit"),
        (expected_multipliers, "expect"),
    ]
    assert product_calls == [
        (expected_multipliers, "expect"),
        (expected_multipliers, "crit"),
        (expected_multipliers, "not_crit"),
    ]
