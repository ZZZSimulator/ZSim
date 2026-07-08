from __future__ import annotations

from dataclasses import dataclass

from zsim.sim_progress.calculation.inputs.common import DamageIdentityProfile
from zsim.sim_progress.calculation.results.common import MultiplierVector


@dataclass(frozen=True, slots=True)
class RegularDamageResult:
    """带有乘区依据的标量常规伤害输出。"""

    value: float
    identity: DamageIdentityProfile
    multipliers: MultiplierVector
    mode: str


__all__ = [
    "RegularDamageResult",
]
