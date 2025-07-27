from zsim.models.event_enums import SpecialStateUpdateSignal as SSUS
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from zsim.sim_progress.Enemy import Enemy
    from .special_state_manager_class import SpecialStateManager


class EnemySpecialState(ABC):
    """管理敌人特殊状态的数据结构基类"""

    @abstractmethod
    def __init__(self, enemy_instance: "Enemy", manager_instance: "SpecialStateManager", **kwargs):
        self.enemy = enemy_instance
        self.manager = manager_instance
        self.active: bool = False  # 激活状态
        self.last_update_tick: int = 0  # 最近更新时间
        self.max_duration: int = 0  # 持续时间
        self.description: str | None = None  # 说明

    @abstractmethod
    def start(self):
        """开始函数"""
        pass

    @abstractmethod
    def update(self, update_signal: SSUS, **kwargs):
        """
        状态更新函数！无论是在Preload内部传给Enemy，还是在Enemy的receive hit阶段，
        都需要调用此函数并且使用不同的信号来区分业务逻辑；
        """
        pass

    @abstractmethod
    def end(self):
        """结束函数！"""
        pass
