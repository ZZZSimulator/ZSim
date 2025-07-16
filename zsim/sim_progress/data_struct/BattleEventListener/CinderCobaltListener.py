from typing import TYPE_CHECKING
from zsim.models.event_enums import ListenerBroadcastSignal as LBS
from .BaseListenerClass import BaseListener

if TYPE_CHECKING:
    from zsim.simulator.simulator_class import Simulator


class CinderCobaltListener(BaseListener):
    """这个监听器的作用是监听佩戴者的进场。"""

    def __init__(self, listener_id: str = None, sim_instance: "Simulator" = None):
        super().__init__(listener_id, sim_instance=sim_instance)
        self.active_signal: tuple[object, bool] | None = None

    def listening_event(self, event_obj, signal: LBS, **kwargs):
        """监听到佩戴者的进场后，记录更新信号"""
        if signal not in [LBS.SWITCHING_IN, LBS.ENTER_BATTLE]:
            return
        from zsim.sim_progress.Character import Character

        if not isinstance(event_obj, Character):
            return
        self.active_signal = (event_obj, True)

    def listener_active(self):
        pass
