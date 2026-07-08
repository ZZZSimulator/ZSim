from __future__ import annotations

from typing import Iterable

import numpy as np

from zsim.sim_progress.calculation.inputs.anomaly import (
    AnomalyDamageInput,
    AnomalyDamageMultipliers,
    AnomalyDamageSnapshot,
)
from zsim.sim_progress.calculation.results.anomaly import AnomalyDamageResult
from zsim.sim_progress.calculation.results.common import MultiplierVector

ANOMALY_DAMAGE_MULTIPLIER_LABELS = (
    "base_damage",
    "damage_bonus",
    "anomaly_mastery_multiplier",
    "level_multiplier",
    "anomaly_damage_bonus",
    "active_crit_multiplier",
    "defense_multiplier",
    "resistance_multiplier",
    "vulnerability_multiplier",
    "snapshot_impact",
    "snapshot_stun_bonus",
    "stun_vulnerability_multiplier",
    "special_multiplier",
)


def assemble_anomaly_damage_multiplier_vector(
    snapshot: AnomalyDamageSnapshot,
    multipliers: AnomalyDamageMultipliers,
) -> MultiplierVector:
    """组装异常最终伤害乘区，顺序必须与旧公式保持一致。"""
    return MultiplierVector(
        values=(
            snapshot.base_damage,
            snapshot.damage_bonus,
            snapshot.anomaly_mastery_multiplier,
            multipliers.level_multiplier,
            snapshot.anomaly_damage_bonus,
            multipliers.active_crit_multiplier,
            multipliers.defense_multiplier,
            multipliers.resistance_multiplier,
            multipliers.vulnerability_multiplier,
            snapshot.snapshot_impact,
            snapshot.snapshot_stun_bonus,
            multipliers.stun_vulnerability_multiplier,
            multipliers.special_multiplier,
        ),
        labels=ANOMALY_DAMAGE_MULTIPLIER_LABELS,
    )


def calculate_anomaly_damage_expectation(
    final_multipliers: Iterable[float],
    *,
    snapshot_impact: float,
    snapshot_stun_bonus: float,
    scaling_factor: float,
) -> np.float64:
    """计算异常伤害期望，保留旧公式中的冲击力与失衡值增幅抵消。"""
    return np.float64(
        np.prod(tuple(final_multipliers)) / (snapshot_impact * snapshot_stun_bonus) * scaling_factor
    )


def calculate_anomaly_damage(input_snapshot: AnomalyDamageInput) -> AnomalyDamageResult:
    final_multipliers = assemble_anomaly_damage_multiplier_vector(
        input_snapshot.snapshot,
        input_snapshot.multipliers,
    )
    value = calculate_anomaly_damage_expectation(
        final_multipliers.values,
        snapshot_impact=input_snapshot.snapshot.snapshot_impact,
        snapshot_stun_bonus=input_snapshot.snapshot.snapshot_stun_bonus,
        scaling_factor=input_snapshot.scaling_factor,
    )
    return AnomalyDamageResult(
        value=value,
        identity=input_snapshot.identity,
        multipliers=final_multipliers,
        scaling_factor=input_snapshot.scaling_factor,
        cancelled_snapshot_impact=input_snapshot.snapshot.snapshot_impact,
        cancelled_snapshot_stun_bonus=input_snapshot.snapshot.snapshot_stun_bonus,
    )


def apply_anomaly_damage_ratio(
    final_multipliers: MultiplierVector,
    *,
    anomaly_damage_ratio: float,
) -> MultiplierVector:
    """应用紊乱绽放异常伤害倍率，等价于旧公式乘区 0 的倍率调整。"""
    if not final_multipliers.values:
        raise ValueError("异常伤害乘区向量不能为空")
    values = (
        np.float64(final_multipliers.values[0]) * anomaly_damage_ratio,
        *final_multipliers.values[1:],
    )
    return MultiplierVector(values=values, labels=final_multipliers.labels)


__all__ = [
    "ANOMALY_DAMAGE_MULTIPLIER_LABELS",
    "apply_anomaly_damage_ratio",
    "assemble_anomaly_damage_multiplier_vector",
    "calculate_anomaly_damage",
    "calculate_anomaly_damage_expectation",
]
