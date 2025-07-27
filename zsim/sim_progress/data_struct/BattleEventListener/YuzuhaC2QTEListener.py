from typing import TYPE_CHECKING

from zsim.define import YUZUHA_REPORT
from zsim.models.event_enums import ListenerBroadcastSignal as LBS

from .BaseListenerClass import BaseListener

if TYPE_CHECKING:
    from zsim.sim_progress.Character.Yuzuha import Yuzuha
    from zsim.sim_progress.Preload import SkillNode
    from zsim.simulator.simulator_class import Simulator


class YuzuhaC2QTEListener(BaseListener):
    """这个监听器的作用是，监听其他角色通过连携技入场。"""

    def __init__(self, listener_id: str | None = None, sim_instance: "Simulator | None" = None):
        super().__init__(listener_id, sim_instance=sim_instance)
        self.char: "Yuzuha | None" = None

    def listening_event(self, event, signal: LBS, skill_node: "SkillNode | None" = None, **kwargs):
        """"""
        if self.char is None:
            from zsim.sim_progress.Character.Yuzuha import Yuzuha

            char_obj = self.sim_instance.char_data.find_char_obj(CID=1411)
            if not isinstance(char_obj, Yuzuha):
                return
            self.char = char_obj
        if (
            signal != LBS.SWITCHING_IN
            or not isinstance(skill_node, SkillNode)
            or skill_node.char_name == self.char.NAME
            or skill_node.skill.trigger_buff_level != 5
        ):
            return
        else:
            self.listener_active()
            if YUZUHA_REPORT:
                self.sim_instance.schedule_data.change_process_state()
                print(
                    f"【柚叶2画】检测到队友 {skill_node.char_name} 通过连携技 {skill_node.skill_tag} 入场，为柚叶恢复1点甜度点"
                )

    def listener_active(self):
        assert self.char is not None
        self.char.update_sugar_points(value=1)
