from __future__ import annotations

import numpy as np


def calculate_polarity_disorder_base_damage(
    *,
    base_disorder_damage: float,
    yanagi_ap: float,
    polarity_disorder_ratio: float,
    additional_dmg_ap_ratio: float,
) -> np.float64:
    """计算极性紊乱最终基础伤害，保留柳异常精通追加项。"""
    return np.float64(
        (base_disorder_damage * polarity_disorder_ratio) + (yanagi_ap * additional_dmg_ap_ratio)
    )


__all__ = ["calculate_polarity_disorder_base_damage"]
