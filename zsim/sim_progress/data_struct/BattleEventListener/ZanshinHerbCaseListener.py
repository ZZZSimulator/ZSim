from typing import TYPE_CHECKING

from .BaseListenerClass import BaseListener
from zsim.models.event_enums import ListenerBroadcastSignal as LBS

if TYPE_CHECKING:
    from zsim.simulator.simulator_class import Simulator


class ZanshinHerbCaseListener(BaseListener):
    """这个监听器的作用是记录残心青囊的触发信号"""

    def __init__(self, listener_id: str | None = None, sim_instance: "Simulator | None" = None):
        super().__init__(listener_id, sim_instance=sim_instance)
        self.active_signal: tuple[object, bool] | None = None

    def listening_event(self, event, signal: LBS, **kwargs):
        """监听到失衡事件或是触发了新的异常事件时，记录这个信号。"""
        if signal not in [LBS.STUN, LBS.ANOMALY]:
            return
        self.active_signal = (event, True)

    def listener_active(self):
        """置空信号"""
        self.active_signal = None
