from typing import TYPE_CHECKING

from .BaseListenerClass import BaseListener
from zsim.models.event_enums import ListenerBroadcastSignal as LBS
if TYPE_CHECKING:
    from zsim.simulator.simulator_class import Simulator


class HeartstringNocturneListener(BaseListener):
    """监听入场事件，并且直接添加心弦夜响Buff"""

    def __init__(self, listener_id: str = None, sim_instance: "Simulator" = None):
        super().__init__(listener_id, sim_instance=sim_instance)
        self.active_signal = None

    def listening_event(self, event, signal: LBS, **kwargs):
        """监听到角色入场事件，传递入场信号。"""
        if signal != LBS.ENTER_BATTLE:
            return
        from zsim.sim_progress.Preload import SkillNode

        if not isinstance(event, SkillNode):
            raise ValueError("entr_battle_event的事件对象必须是SkillNode类型！")
        self.active_signal = (event, True)

    def listener_active(self):
        self.active_signal = None
