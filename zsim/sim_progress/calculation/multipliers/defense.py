from __future__ import annotations

from zsim.sim_progress.calculation.inputs.regular import DefenseMultiplierInput

LEVEL_COEFFICIENTS = (
    0,
    50,
    54,
    58,
    62,
    66,
    71,
    76,
    82,
    88,
    94,
    100,
    107,
    114,
    121,
    129,
    137,
    145,
    153,
    162,
    172,
    181,
    191,
    201,
    211,
    222,
    233,
    245,
    258,
    268,
    281,
    293,
    306,
    319,
    333,
    347,
    362,
    377,
    393,
    409,
    421,
    436,
    452,
    469,
    485,
    502,
    519,
    537,
    556,
    573,
    592,
    612,
    629,
    649,
    669,
    689,
    709,
    730,
    751,
    772,
    794,
)


def calculate_pen_ratio(
    static_pen_ratio: float,
    dynamic_pen_ratio: float,
    *,
    addon_pen_ratio: float = 0.0,
) -> float:
    return static_pen_ratio + dynamic_pen_ratio + addon_pen_ratio


def calculate_recipient_defense(
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
    recipient_defense = max_defense * (1 - percentage_defense_reduction) - flat_defense_reduction
    pen_numeric = static_pen_numeric + dynamic_pen_numeric + addon_pen_numeric
    return max(
        0.0,
        recipient_defense * (1 - pen_ratio - addon_pen_ratio) - pen_numeric,
    )


def calculate_attacker_level_coefficient(attacker_level: int) -> int:
    clamped_level = min(60, max(0, attacker_level))
    return LEVEL_COEFFICIENTS[clamped_level]


def calculate_defense_multiplier(input_snapshot: DefenseMultiplierInput) -> float:
    if input_snapshot.base_attribute == 4:
        return 1.0
    attacker_coefficient = calculate_attacker_level_coefficient(input_snapshot.attacker_level)
    pen_ratio = calculate_pen_ratio(
        input_snapshot.static_pen_ratio,
        input_snapshot.dynamic_pen_ratio,
    )
    effective_defense = calculate_recipient_defense(
        input_snapshot.max_defense,
        input_snapshot.percentage_defense_reduction,
        input_snapshot.flat_defense_reduction,
        input_snapshot.static_pen_numeric,
        input_snapshot.dynamic_pen_numeric,
        pen_ratio,
    )
    return attacker_coefficient / (effective_defense + attacker_coefficient)


__all__ = [
    "LEVEL_COEFFICIENTS",
    "calculate_attacker_level_coefficient",
    "calculate_defense_multiplier",
    "calculate_pen_ratio",
    "calculate_recipient_defense",
]
