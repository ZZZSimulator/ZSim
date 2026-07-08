from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DamageIdentity:
    """可观测的伤害或异常结果身份。"""

    code: str
    display_name: str


@dataclass(frozen=True, slots=True)
class MultiplierAffinity:
    """公式读取乘区时使用的元素乘区亲和。"""

    code: str
    display_name: str


@dataclass(frozen=True, slots=True)
class AnomalyStateIdentity:
    """计算或状态迁移所代表的敌人异常状态身份。"""

    code: str
    display_name: str


# 公式域意图：伤害身份、乘区亲和、异常状态在计算边界显式分离。
PHYSICAL_DAMAGE = DamageIdentity("physical", "物理")
FIRE_DAMAGE = DamageIdentity("fire", "火")
ICE_DAMAGE = DamageIdentity("ice", "冰")
ELECTRIC_DAMAGE = DamageIdentity("electric", "电")
ETHER_DAMAGE = DamageIdentity("ether", "以太")
FROST_DAMAGE = DamageIdentity("frost", "烈霜")
AURIC_INK_DAMAGE = DamageIdentity("auric_ink", "玄墨")
VORTEX_DAMAGE = DamageIdentity("vortex", "乱流")
HONED_EDGE_DAMAGE = DamageIdentity("honed_edge", "凌刃")

PHYSICAL_AFFINITY = MultiplierAffinity("physical", "物理")
FIRE_AFFINITY = MultiplierAffinity("fire", "火")
ICE_AFFINITY = MultiplierAffinity("ice", "冰")
ELECTRIC_AFFINITY = MultiplierAffinity("electric", "电")
ETHER_AFFINITY = MultiplierAffinity("ether", "以太")

ASSAULT_STATE = AnomalyStateIdentity("assault", "强击")
BURN_STATE = AnomalyStateIdentity("burn", "灼烧")
FROSTBITE_STATE = AnomalyStateIdentity("frostbite", "碎冰")
SHOCK_STATE = AnomalyStateIdentity("shock", "感电")
CORRUPTION_STATE = AnomalyStateIdentity("corruption", "侵蚀")
FROST_STATE = AnomalyStateIdentity("frost", "烈霜碎冰")
AURIC_INK_STATE = AnomalyStateIdentity("auric_ink", "玄墨侵蚀")
