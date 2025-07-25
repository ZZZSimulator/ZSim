from typing import TYPE_CHECKING

from zsim.define import YIXUAN_REPORT

from .BaseListenerClass import BaseListener
from zsim.models.event_enums import ListenerBroadcastSignal as LBS
if TYPE_CHECKING:
    from zsim.sim_progress.Character.character import Character
    from zsim.sim_progress.Character.Yixuan import Yixuan
    from zsim.simulator.simulator_class import Simulator


class YixuanAnomalyListener(BaseListener):
    """这个监听器的作用是，尝试监听仪玄的玄墨异常触发事件，并且恢复自身闪能，10点（内置CD10秒）。"""

    def __init__(self, listener_id: str = None, sim_instance: "Simulator" = None):
        super().__init__(listener_id, sim_instance=sim_instance)
        self.char: "Yixuan | None" = None
        self.last_active_tick: int = 0
        self.cd: int = 600  # 内置CD
        self.recover_value: int = 10  # 监听器激活时为仪玄恢复的闪能值

    @property
    def ready(self) -> bool:
        return (
            True
            if self.last_active_tick == 0
            else self.last_active_tick + self.cd <= self.sim_instance.tick
        )

    def listening_event(self, event_obj, signal: LBS, **kwargs):
        """监听到新的anomlay创建后，检查属性类型，通过判定则恢复闪能。"""
        if self.char is None:
            char_obj: "Yixuan | Character | None" = (
                self.sim_instance.char_data.find_char_obj(CID=1371)
            )
            self.char = char_obj
        if signal != LBS.ANOMALY:
            return
        from zsim.sim_progress.anomaly_bar import AnomalyBar

        if not isinstance(event_obj, AnomalyBar):
            raise TypeError(
                f"仪玄的属性异常监听器接收到了anomlay_event的信号，但是传入的event_obj却为{type(event_obj)}类型，请检查监听器广播函数调用！"
            )
        if event_obj:
            from zsim.define import ANOMALY_MAPPING
            if YIXUAN_REPORT:
                print(
                    f"监听到新的属性异常：{ANOMALY_MAPPING[event_obj.element_type]}！尝试激活监听事件——仪玄闪能恢复！"
                )
                self.sim_instance.schedule_data.change_process_state()
            self.listener_active()

    def listener_active(self):
        """监听事件激活，检测内置Cd，通过后为仪玄恢复闪能值。"""
        if not self.ready:
            if YIXUAN_REPORT:
                print(
                    f"仪玄在{self.last_active_tick}tick时已经通过该效果恢复过一次闪能值了，所以此时该效果的内置CD尚未就绪！"
                )
                self.sim_instance.schedule_data.change_process_state()
            return
        else:
            from zsim.sim_progress.Character.Yixuan import Yixuan

            if not isinstance(self.char, Yixuan):
                raise TypeError
            self.char.update_adrenaline(self.recover_value)
            if YIXUAN_REPORT:
                print(
                    f"玄墨监听器事件激活！成功为仪玄恢复{self.recover_value}点闪能！"
                )
                self.sim_instance.schedule_data.change_process_state()
            self.last_active_tick = self.sim_instance.tick
