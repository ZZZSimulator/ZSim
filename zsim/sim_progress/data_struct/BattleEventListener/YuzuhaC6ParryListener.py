from typing import TYPE_CHECKING
from zsim.define import YUZUHA_REPORT

from .BaseListenerClass import BaseListener
from zsim.models.event_enums import ListenerBroadcastSignal as LBS
if TYPE_CHECKING:
    from zsim.simulator.simulator_class import Simulator


class YuzuhaC6ParryListener(BaseListener):
    """这个监听器的作用是，监听自身的招架事件"""
    def __init__(self, listener_id: str = None, sim_instance: "Simulator" = None):
        super().__init__(listener_id, sim_instance=sim_instance)
        self.char: "Yuzuha | None" = None

    def listening_event(self, event_obj, signal: LBS, **kwargs):
        """获取“招架”类的广播信号。"""
        if self.char is None:
            self.char = self.sim_instance.char_data.find_char_obj(CID=1411)
        if signal != LBS.PARRY:
            return
        from zsim.sim_progress.Preload import SkillNode
        if not isinstance(event_obj, SkillNode):
            return
        if event_obj.skill_tag not in ["1411_knock_back_cause_parry", "1411_SNA_3"]:
            return
        else:
            self.listener_active()
            if YUZUHA_REPORT:
                self.sim_instance.schedule_data.change_process_state()
                print(f"【柚叶6画】检测到 柚叶 通过技能 {event_obj.skill_tag} 招架/格挡了敌人的攻击，为 柚叶 恢复1点甜度点")

    def listener_active(self):
        self.char.update_sugar_points(value=1)
