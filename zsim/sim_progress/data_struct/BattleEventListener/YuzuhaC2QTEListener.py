from typing import TYPE_CHECKING
from zsim.define import YUZUHA_REPORT

from .BaseListenerClass import BaseListener
from zsim.models.event_enums import ListenerBroadcastSignal as LBS
if TYPE_CHECKING:
    from zsim.sim_progress.Character.character import Character
    from zsim.sim_progress.Character.Yuzuha import Yuzuha
    from zsim.simulator.simulator_class import Simulator


class YuzuhaC2QTEListener(BaseListener):
    """这个监听器的作用是，监听其他角色通过连携技入场。"""
    def __init__(self, listener_id: str = None, sim_instance: "Simulator" = None):
        super().__init__(listener_id, sim_instance=sim_instance)
        self.char: "Yuzuha | None" = None

    def listening_event(self, event_obj, signal: LBS, **kwargs):
        """"""
        if self.char is None:
            self.char = self.sim_instance.char_data.find_char_obj(CID=1411)
        if not signal == LBS.SWITCHING_IN:
            return
        from zsim.sim_progress.Preload import SkillNode
        if not isinstance(event_obj, SkillNode):
            return
        if event_obj.char_name == self.char.NAME:
            return
        if event_obj.skill.trigger_buff_level != 5:
            return
        else:
            self.listener_active()
            if YUZUHA_REPORT:
                self.sim_instance.schedule_data.change_process_state()
                print(f"【柚叶2画】检测到队友 {event_obj.char_name} 通过连携技 {event_obj.skill_tag} 入场，为柚叶恢复1点甜度点")

    def listener_active(self):
        self.char.update_sugar_points(value=1)
