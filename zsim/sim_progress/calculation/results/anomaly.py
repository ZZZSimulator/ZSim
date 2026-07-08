from __future__ import annotations

from dataclasses import dataclass

from zsim.sim_progress.calculation.inputs.common import AnomalyIdentityProfile
from zsim.sim_progress.calculation.results.common import MultiplierVector


@dataclass(frozen=True, slots=True)
class AnomalyDamageResult:
    """带有乘区依据的标量异常伤害输出。"""

    value: float
    identity: AnomalyIdentityProfile
    multipliers: MultiplierVector
    scaling_factor: float
    cancelled_snapshot_impact: float
    cancelled_snapshot_stun_bonus: float


__all__ = [
    "AnomalyDamageResult",
]
