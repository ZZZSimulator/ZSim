from typing import TYPE_CHECKING

from .BaseListenerClass import BaseListener
from zsim.models.event_enums import ListenerBroadcastSignal as LBS

if TYPE_CHECKING:
    from zsim.simulator.simulator_class import Simulator


class HugoCorePassiveBuffListener(BaseListener):
    """这个监听器的作用是，尝试监听雨果致使怪物失衡的事件，并且触发一次核心被动Buff"""

    def __init__(self, listener_id: str | None = None, sim_instance: "Simulator | None" = None):
        super().__init__(listener_id, sim_instance=sim_instance)
        self.buff_index = "Buff-角色-雨果-核心被动-暗渊回响"

    def listening_event(self, event, signal: LBS, **kwargs):
        """监听到雨果的single_hit后，直接添加Buff"""
        if signal != LBS.STUN:
            return
        from zsim.sim_progress.data_struct import SingleHit

        if not isinstance(event, SingleHit):
            return
        if "1291" not in event.skill_tag:
            return
        self.listener_active()
        from zsim.define import HUGO_REPORT

        if HUGO_REPORT:
            self.sim_instance.schedule_data.change_process_state()
            if event.skill_node is None:
                return
            print(
                f"雨果的失衡事件监听器监听到了雨果的技能{event.skill_tag}（{event.skill_node.skill.skill_text}）使怪物陷入失衡状态，根据核心被动，触发一次【暗渊回响】Buff"
            )

    def listener_active(self):
        """触发核心被动Buff，通过BuffAddStrategy来暴力添加Buff"""
        from zsim.sim_progress.Buff.BuffAddStrategy import buff_add_strategy

        buff_add_strategy(self.buff_index, benifit_list=["雨果"], sim_instance=self.sim_instance)
