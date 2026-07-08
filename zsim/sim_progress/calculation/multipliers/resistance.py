from __future__ import annotations

from zsim.sim_progress.calculation.inputs.regular import ResistanceMultiplierInput


def calculate_resistance_multiplier(input_snapshot: ResistanceMultiplierInput) -> float:
    element_resistance = (
        input_snapshot.target_resistances.get(input_snapshot.affinity)
        - input_snapshot.damage_resistance_decreases.get(input_snapshot.affinity)
        - input_snapshot.resistance_penetrations.get(input_snapshot.affinity)
    )
    return (
        1
        - element_resistance
        + input_snapshot.all_damage_resistance_decrease
        + input_snapshot.all_resistance_penetration
        + input_snapshot.snapshot_resistance_penetration
    )


__all__ = [
    "calculate_resistance_multiplier",
]
