from __future__ import annotations

from dataclasses import dataclass

from zsim.sim_progress.calculation.inputs.common import AnomalyIdentityProfile


@dataclass(frozen=True, slots=True)
class AnomalyDamageSnapshot:
    """异常伤害公式需要的旧版异常伤害快照值。"""

    base_damage: float
    damage_bonus: float
    anomaly_mastery_multiplier: float
    anomaly_damage_bonus: float
    snapshot_impact: float
    snapshot_stun_bonus: float


@dataclass(frozen=True, slots=True)
class AnomalyDamageMultipliers:
    """在 runtime 绑定公式外部组装的显式非快照乘区。"""

    level_multiplier: float
    active_crit_multiplier: float
    defense_multiplier: float
    resistance_multiplier: float
    vulnerability_multiplier: float
    stun_vulnerability_multiplier: float
    special_multiplier: float


@dataclass(frozen=True, slots=True)
class AnomalyDamageInput:
    """单次异常伤害计算的只读输入快照。"""

    identity: AnomalyIdentityProfile
    snapshot: AnomalyDamageSnapshot
    multipliers: AnomalyDamageMultipliers
    scaling_factor: float


__all__ = [
    "AnomalyDamageInput",
    "AnomalyDamageMultipliers",
    "AnomalyDamageSnapshot",
]
