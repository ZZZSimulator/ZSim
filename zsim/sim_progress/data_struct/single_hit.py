from dataclasses import dataclass
import numpy as np


@dataclass
class SingleHit:
    """Feedback to enemy for a single hit."""

    skill_tag: str
    snapshot: tuple[int, np.float64, np.ndarray]
    stun: np.float64
    dmg_expect: np.float64
    dmg_crit: np.float64
    hitted_count: int
    proactive: bool  # 该动作是否为主动技能（主要依靠检测skill_node的follow_by参数）
    heavy_hit = False  # 重攻击标签——默认重攻击是   heavy_attack为True的技能的最后一个Hit
    skill_node = None

    def effective_anomlay_buildup(self) -> bool:
        """是否是有效积蓄"""
        return self.skill_node.effective_anomaly_buildup


@dataclass
class AnomalyHit:
    """Feedback to enemy for a single anomaly hit."""

    skill_tag: str
    snapshot: tuple[int, np.float64, np.ndarray]
