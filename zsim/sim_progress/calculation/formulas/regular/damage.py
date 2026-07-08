from __future__ import annotations

from collections.abc import Callable
from typing import Literal

import numpy as np

from zsim.sim_progress.calculation.inputs.regular import (
    RegularBaseAttributeInput,
    RegularCritInput,
    RegularDamageBonusInput,
    RegularDamageInput,
    RegularDamageMultipliers,
)
from zsim.sim_progress.calculation.results.common import MultiplierVector
from zsim.sim_progress.calculation.results.regular import RegularDamageResult

REGULAR_DAMAGE_MULTIPLIER_LABELS = (
    "base_damage",
    "damage_bonus",
    "crit_multiplier",
    "defense_multiplier",
    "resistance_multiplier",
    "damage_vulnerability_multiplier",
    "stun_vulnerability_multiplier",
    "special_multiplier",
    "sheer_damage_bonus",
)


def calculate_non_sheer_base_attribute(
    base_attribute: int,
    *,
    attack: float,
    field_attack_percentage: float,
    flat_attack: float,
    hp: float,
    field_hp_percentage: float,
    flat_hp: float,
    defense: float,
    field_defense_percentage: float,
    flat_defense: float,
    anomaly_proficiency: float,
    field_anomaly_proficiency: float,
    flat_anomaly_proficiency: float,
) -> float:
    if base_attribute == 0:
        return attack * (1 + field_attack_percentage) + flat_attack
    if base_attribute == 1:
        return hp * (1 + field_hp_percentage) + flat_hp
    if base_attribute == 2:
        return defense * (1 + field_defense_percentage) + flat_defense
    if base_attribute == 3:
        return anomaly_proficiency * (1 + field_anomaly_proficiency) + flat_anomaly_proficiency
    raise AssertionError("无效的基础属性")


def calculate_sheer_base_attribute(
    conversion_rates: tuple[tuple[int, float], ...],
    *,
    base_attribute_reader: Callable[[int], float],
    field_sheer_attack_percentage: float,
    flat_sheer_attack: float,
) -> float:
    base_sheer_attack = 0.0
    for key, value in conversion_rates:
        if key not in (0, 1, 2, 3):
            raise ValueError(f"Unsupported sheer attack conversion key: {key}")
        if value <= 0:
            continue
        base_sheer_attack += base_attribute_reader(key) * value
    if field_sheer_attack_percentage != 0:
        raise ValueError(
            "Nonzero field_sheer_attack_percentage is not supported by the current legacy formula"
        )
    return base_sheer_attack + flat_sheer_attack


def calculate_base_attribute(input_snapshot: RegularBaseAttributeInput) -> float:
    def read_non_sheer(base_attribute: int) -> float:
        return calculate_non_sheer_base_attribute(
            base_attribute,
            attack=input_snapshot.attack,
            field_attack_percentage=input_snapshot.field_attack_percentage,
            flat_attack=input_snapshot.flat_attack,
            hp=input_snapshot.hp,
            field_hp_percentage=input_snapshot.field_hp_percentage,
            flat_hp=input_snapshot.flat_hp,
            defense=input_snapshot.defense,
            field_defense_percentage=input_snapshot.field_defense_percentage,
            flat_defense=input_snapshot.flat_defense,
            anomaly_proficiency=input_snapshot.anomaly_proficiency,
            field_anomaly_proficiency=input_snapshot.field_anomaly_proficiency,
            flat_anomaly_proficiency=input_snapshot.flat_anomaly_proficiency,
        )

    if input_snapshot.diff_multiplier in (0, 1, 2, 3):
        return read_non_sheer(input_snapshot.diff_multiplier)
    if input_snapshot.diff_multiplier == 4:
        return calculate_sheer_base_attribute(
            input_snapshot.sheer_attack_conversion_rates,
            base_attribute_reader=read_non_sheer,
            field_sheer_attack_percentage=input_snapshot.field_sheer_attack_percentage,
            flat_sheer_attack=input_snapshot.flat_sheer_attack,
        )
    raise AssertionError("无效的基础属性")


def calculate_base_damage(
    damage_ratio: float,
    attribute: float,
    *,
    extra_damage_ratio: float,
    base_damage_increase_percentage: float,
    base_damage_increase: float,
) -> float:
    return ((damage_ratio + extra_damage_ratio) * attribute) * (
        1 + base_damage_increase_percentage
    ) + base_damage_increase


def calculate_regular_base_damage(input_snapshot: RegularBaseAttributeInput) -> float:
    attribute = calculate_base_attribute(input_snapshot)
    damage_ratio = input_snapshot.damage_ratio / input_snapshot.hit_times
    return calculate_base_damage(
        damage_ratio,
        attribute,
        extra_damage_ratio=input_snapshot.extra_damage_ratio,
        base_damage_increase_percentage=input_snapshot.base_damage_increase_percentage,
        base_damage_increase=input_snapshot.base_damage_increase,
    )


def calculate_regular_damage_bonus(input_snapshot: RegularDamageBonusInput) -> float:
    element_damage_bonus = input_snapshot.static_damage_bonuses.get(
        input_snapshot.identity.multiplier_affinity
    ) + input_snapshot.dynamic_damage_bonuses.get(input_snapshot.identity.multiplier_affinity)
    if input_snapshot.trigger_buff_level == 10:
        trigger_damage_bonus = 0.0
    elif 0 <= input_snapshot.trigger_buff_level < len(input_snapshot.trigger_damage_bonuses):
        trigger_damage_bonus = input_snapshot.trigger_damage_bonuses[
            input_snapshot.trigger_buff_level
        ]
    else:
        raise AssertionError("无效的 trigger_level")

    label_damage_bonus = (
        input_snapshot.aftershock_attack_damage_bonus if input_snapshot.aftershock_attack else 0.0
    )
    return (
        1
        + element_damage_bonus
        + trigger_damage_bonus
        + label_damage_bonus
        + input_snapshot.all_damage_bonus
    )


def calculate_full_crit_rate(input_snapshot: RegularCritInput) -> float:
    return (
        input_snapshot.static_crit_rate
        + input_snapshot.dynamic_crit_rate
        + input_snapshot.field_crit_rate
        + input_snapshot.crit_rate_received_increase
    )


def calculate_personal_crit_rate(input_snapshot: RegularCritInput) -> float:
    return (
        input_snapshot.static_crit_rate
        + input_snapshot.dynamic_crit_rate
        + input_snapshot.field_crit_rate
    )


def calculate_personal_crit_damage(input_snapshot: RegularCritInput) -> float:
    return (
        input_snapshot.static_crit_damage
        + input_snapshot.dynamic_crit_damage
        + input_snapshot.field_crit_damage
    )


def calculate_full_crit_damage(input_snapshot: RegularCritInput) -> float:
    label_crit_damage_bonus = (
        input_snapshot.aftershock_attack_crit_damage_bonus
        if input_snapshot.aftershock_attack
        else 0.0
    )
    crit_damage = (
        input_snapshot.static_crit_damage
        + input_snapshot.dynamic_crit_damage
        + input_snapshot.field_crit_damage
        + label_crit_damage_bonus
        + input_snapshot.received_crit_damage_bonus
    )
    return min(5, crit_damage)


def calculate_crit_expectation(crit_rate: float, crit_damage: float) -> float:
    return 1 + min(1, crit_rate) * crit_damage


def _crit_multiplier(
    multipliers: RegularDamageMultipliers,
    mode: Literal["expect", "crit", "not_crit"],
) -> float:
    if mode == "expect":
        return multipliers.crit_expectation
    if mode == "crit":
        return 1 + multipliers.crit_damage
    if mode == "not_crit":
        return 1.0
    raise ValueError(f"Unsupported regular damage mode: {mode}")


def assemble_regular_damage_multiplier_array(
    multipliers: RegularDamageMultipliers,
    *,
    mode: Literal["expect", "crit", "not_crit"] = "expect",
) -> np.ndarray:
    return np.array(
        [
            multipliers.base_damage,
            multipliers.damage_bonus,
            _crit_multiplier(multipliers, mode),
            multipliers.defense_multiplier,
            multipliers.resistance_multiplier,
            multipliers.damage_vulnerability_multiplier,
            multipliers.stun_vulnerability_multiplier,
            multipliers.special_multiplier,
            multipliers.sheer_damage_bonus,
        ],
        dtype=np.float64,
    )


def assemble_regular_damage_multiplier_vector(
    multipliers: RegularDamageMultipliers,
    *,
    mode: Literal["expect", "crit", "not_crit"] = "expect",
) -> MultiplierVector:
    return MultiplierVector(
        assemble_regular_damage_multiplier_array(multipliers, mode=mode),
        REGULAR_DAMAGE_MULTIPLIER_LABELS,
    )


def calculate_regular_damage_product(
    multipliers: RegularDamageMultipliers,
    *,
    mode: Literal["expect", "crit", "not_crit"] = "expect",
) -> np.float64:
    return np.float64(np.prod(assemble_regular_damage_multiplier_array(multipliers, mode=mode)))


def calculate_regular_damage(
    input_snapshot: RegularDamageInput,
    *,
    mode: Literal["expect", "crit", "not_crit"] = "expect",
) -> RegularDamageResult:
    final_multipliers = assemble_regular_damage_multiplier_vector(
        input_snapshot.multipliers,
        mode=mode,
    )
    return RegularDamageResult(
        value=np.float64(np.prod(final_multipliers.values)),
        identity=input_snapshot.identity,
        multipliers=final_multipliers,
        mode=mode,
    )


__all__ = [
    "REGULAR_DAMAGE_MULTIPLIER_LABELS",
    "assemble_regular_damage_multiplier_array",
    "assemble_regular_damage_multiplier_vector",
    "calculate_base_attribute",
    "calculate_base_damage",
    "calculate_crit_expectation",
    "calculate_full_crit_damage",
    "calculate_full_crit_rate",
    "calculate_non_sheer_base_attribute",
    "calculate_personal_crit_damage",
    "calculate_personal_crit_rate",
    "calculate_regular_base_damage",
    "calculate_regular_damage",
    "calculate_regular_damage_bonus",
    "calculate_regular_damage_product",
    "calculate_sheer_base_attribute",
]
