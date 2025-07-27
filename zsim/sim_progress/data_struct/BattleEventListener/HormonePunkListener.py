from typing import TYPE_CHECKING

from .BaseListenerClass import BaseListener
from zsim.models.event_enums import ListenerBroadcastSignal as LBS

if TYPE_CHECKING:
    from zsim.simulator.simulator_class import Simulator


class HormonePunkListener(BaseListener):
    """这个监听器的作用是监听佩戴者的进场。"""

    def __init__(self, listener_id: str | None = None, sim_instance: "Simulator | None" = None):
        super().__init__(listener_id, sim_instance=sim_instance)
        self.active_signal: tuple[object, bool] | None = None

    def listening_event(self, event, signal: LBS, **kwargs):
        """监听到佩戴者的进场后，记录更新信号"""
        if signal not in [LBS.SWITCHING_IN, LBS.ENTER_BATTLE]:
            return
        from zsim.sim_progress.Character.character import Character

        if not isinstance(event, Character):
            return
        self.active_signal = (event, True)

    def listener_active(self):
        pass
