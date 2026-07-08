from __future__ import annotations

from typing import Literal, Mapping

import numpy as np

from zsim.define import ElementType


def calculate_disorder_base_damage(
    *,
    element_type: int,
    base_multiplier: float,
    remaining_tick: float,
    disorder_basic_multiplier_map: Mapping[ElementType | Literal["all"], float],
) -> np.float64:
    """
    计算紊乱基础伤害。

    公式输入是由调用方组装好的快照值；本模块不直接读取 AnomalyBar、Enemy、
    Buff、Simulator、监听器、Schedule 或命令状态。
    """
    t_s = np.float64(remaining_tick / 60)

    match element_type:
        case 0:  # 强击紊乱
            atk = base_multiplier / 7.13
            ratio = np.floor(t_s) * 0.075 + 4.5
        case 1:  # 灼烧紊乱
            atk = base_multiplier / 0.5
            ratio = np.floor(t_s / 0.5) * 0.5 + 4.5
        case 2:  # 霜寒紊乱
            atk = base_multiplier / 5
            ratio = np.floor(t_s) * 0.075 + 4.5
        case 3:  # 感电紊乱
            atk = base_multiplier / 1.25
            ratio = np.floor(t_s) * 1.25 + 4.5
        case 4:  # 侵蚀紊乱
            atk = base_multiplier / 0.625
            ratio = np.floor(t_s / 0.5) * 0.625 + 4.5
        case 5:  # 烈霜紊乱
            atk = base_multiplier / 5
            ratio = np.floor(t_s) * 0.75 + 6
        case 6:  # 玄墨侵蚀紊乱
            atk = base_multiplier / 0.625
            ratio = np.floor(t_s / 0.5) * 0.625 + 4.5
        case _:
            raise AssertionError(f"无效的元素类型 {element_type}")

    disorder_base_ratio_increase = (
        disorder_basic_multiplier_map[element_type] + disorder_basic_multiplier_map["all"]
    )
    return np.float64(atk * (ratio + disorder_base_ratio_increase))


def calculate_disorder_extra_multiplier(
    ano_extra_bonus: Mapping[ElementType | Literal["all", -1], float],
) -> np.float64:
    """紊乱额外增伤 = 1 + disorder_dmg_mul，对应旧 ano_extra_bonus[-1]。"""
    return np.float64(1 + ano_extra_bonus[-1])


def calculate_disorder_stun_multiplier(
    *,
    impact: float,
    snapshot_stun_bonus: float,
    stun_resistance_multiplier: float,
    received_stun_increase_multiplier: float,
    virtual_character_level: int,
) -> np.float64:
    """计算紊乱失衡值，保留旧公式固定 stun_ratio=2 和虚拟等级区。"""
    stun_ratio = 2
    level_multiplier_for_stun = 1 + virtual_character_level * 0.0075
    return np.float64(
        np.prod(
            [
                impact,
                stun_ratio,
                stun_resistance_multiplier,
                snapshot_stun_bonus,
                received_stun_increase_multiplier,
                level_multiplier_for_stun,
            ]
        )
    )


__all__ = [
    "calculate_disorder_base_damage",
    "calculate_disorder_extra_multiplier",
    "calculate_disorder_stun_multiplier",
]
