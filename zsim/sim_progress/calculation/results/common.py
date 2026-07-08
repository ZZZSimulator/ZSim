from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from zsim.sim_progress.calculation.inputs.common import (
    AnomalyIdentityProfile,
    DamageIdentityProfile,
)


@dataclass(frozen=True, slots=True, init=False)
class MultiplierVector:
    """公式模块返回的只读乘区标签与数值。"""

    values: tuple[float, ...]
    labels: tuple[str, ...] = ()

    def __init__(
        self,
        values: Iterable[float],
        labels: Iterable[str] = (),
    ) -> None:
        object.__setattr__(self, "values", tuple(values))
        object.__setattr__(self, "labels", tuple(labels))
        if self.labels and len(self.labels) != len(self.values):
            raise ValueError("MultiplierVector labels must match values length")


@dataclass(frozen=True, slots=True)
class DamageScalarResult:
    """带有身份与乘区依据的标量伤害输出。"""

    value: float
    identity: DamageIdentityProfile
    multipliers: MultiplierVector = field(default_factory=lambda: MultiplierVector(()))


@dataclass(frozen=True, slots=True)
class AnomalyScalarResult:
    """显式分离伤害、亲和与状态身份的标量异常输出。"""

    value: float
    identity: AnomalyIdentityProfile
    multipliers: MultiplierVector = field(default_factory=lambda: MultiplierVector(()))
