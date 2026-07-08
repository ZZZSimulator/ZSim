from __future__ import annotations

from dataclasses import dataclass

from zsim.sim_progress.calculation.identities import (
    AnomalyStateIdentity,
    DamageIdentity,
    MultiplierAffinity,
)


@dataclass(frozen=True, slots=True)
class FormulaLevelContext:
    """公式快照通用的等级输入。"""

    source_level: int
    target_level: int


@dataclass(frozen=True, slots=True)
class FormulaSourceContext:
    """不依赖实时 Character、SkillNode 或 runtime 对象的公式来源身份。"""

    source_name: str
    skill_tag: str


@dataclass(frozen=True, slots=True)
class DamageIdentityProfile:
    """伤害身份，以及用于读取公式加成的乘区亲和。"""

    damage_identity: DamageIdentity
    multiplier_affinity: MultiplierAffinity


@dataclass(frozen=True, slots=True)
class AnomalyIdentityProfile:
    """异常公式身份，显式分离伤害身份、乘区亲和与异常状态。"""

    damage_identity: DamageIdentity
    multiplier_affinity: MultiplierAffinity
    anomaly_state_identity: AnomalyStateIdentity
