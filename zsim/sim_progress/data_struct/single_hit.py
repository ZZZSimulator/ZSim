from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from zsim.sim_progress.Preload import SkillNode


@dataclass
class SingleHit:
    """单次命中结算后反馈给敌人的数据。"""

    skill_tag: str
    snapshot: tuple[int, np.float64, np.ndarray]
    stun: np.float64
    dmg_expect: np.float64
    dmg_crit: np.float64
    hitted_count: int
    proactive: bool  # 该动作是否为主动技能（主要依靠检测skill_node的follow_by参数）
    heavy_hit = False  # 重攻击标签——默认重攻击是   heavy_attack为True的技能的最后一个Hit
    skill_node: "SkillNode | None" = None

    def effective_anomlay_buildup(self) -> bool:
        """是否是有效积蓄"""
        if self.skill_node is None:
            return False
        return self.skill_node.effective_anomaly_buildup

    @property
    def force_qte_trigger(self) -> bool:
        if self.skill_node is None:
            return False
        skill_node: "SkillNode" = self.skill_node
        return skill_node.force_qte_trigger


@dataclass
class AnomalyHit:
    """单次异常伤害结算后反馈给敌人的数据。"""

    skill_tag: str
    snapshot: tuple[int, np.float64, np.ndarray]
