from abc import ABC, abstractmethod
from zsim.models.event_enums import ListenerBroadcastSignal as LBS
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from zsim.simulator.simulator_class import Simulator


class BaseListener(ABC):
    @abstractmethod
    def __init__(self, listener_id: str | None = None, sim_instance: "Simulator | None" = None):
        assert sim_instance is not None
        self.sim_instance: "Simulator" = sim_instance
        self.listener_id: str | None = listener_id
        self.schedule = None

    @abstractmethod
    def listening_event(self, event, signal: LBS, **kwargs):
        """监听事件的函数"""
        pass

    @abstractmethod
    def listener_active(self):
        """当监听到预期事件时，监听器的激活函数"""
        pass
