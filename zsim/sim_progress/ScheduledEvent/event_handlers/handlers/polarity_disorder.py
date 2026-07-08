"""极性紊乱事件处理器"""

from typing import Any

from zsim.models.event_enums import ListenerBroadcastSignal as LBS
from zsim.sim_progress import Report
from zsim.sim_progress.anomaly_bar.CopyAnomalyForOutput import PolarityDisorder
from zsim.sim_progress.calculation.anomaly_calculator import CalPolarityDisorder

from ..base import BaseEventHandler
from ..context import EventContext


class PolarityDisorderEventHandler(BaseEventHandler):
    """极性紊乱事件处理器"""

    def __init__(self):
        super().__init__("polarity_disorder")

    def can_handle(self, event: Any) -> bool:
        return type(event) is PolarityDisorder

    def handle(self, event: PolarityDisorder, context: EventContext) -> None:
        """处理极性紊乱事件"""
        enemy = self._get_context_enemy(context)
        active_buff_view = self._get_context_active_buff_view(context)
        sim_instance = self._get_context_sim_instance(context)
        tick = self._get_context_tick(context)

        # 广播极性紊乱事件
        sim_instance.listener_manager.broadcast_event(event=event, signal=LBS.DISORDER_SETTLED)

        # 计算极性紊乱伤害
        calculator = CalPolarityDisorder(
            disorder_obj=event,
            enemy_obj=enemy,
            dynamic_buff=active_buff_view,
            sim_instance=sim_instance,
        )

        damage_disorder = calculator.cal_anomaly_dmg()

        Report.report_dmg_result(
            tick=tick,
            element_type=event.element_type,
            skill_tag="极性紊乱",
            dmg_expect=round(damage_disorder, 2),
            dmg_crit=round(damage_disorder, 2),
            is_anomaly=True,
            is_disorder=True,
            stun=0,
            buildup=0,
            **enemy.dynamic.get_status(),
            UUID=event.UUID if event.UUID is not None else "",
        )
