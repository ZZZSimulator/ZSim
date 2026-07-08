from __future__ import annotations

from zsim.sim_progress.calculation.inputs.regular import SpecialMultiplierInput


def calculate_special_multiplier(input_snapshot: SpecialMultiplierInput) -> float:
    return 1 + input_snapshot.special_multiplier_zone


def calculate_sheer_damage_bonus(input_snapshot: SpecialMultiplierInput) -> float:
    if input_snapshot.diff_multiplier != 4:
        return 1.0
    return 1 + input_snapshot.sheer_damage_bonus


__all__ = [
    "calculate_sheer_damage_bonus",
    "calculate_special_multiplier",
]
