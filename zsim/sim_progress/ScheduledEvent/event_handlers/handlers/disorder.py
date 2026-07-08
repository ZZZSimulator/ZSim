"""紊乱事件处理器"""

from typing import Any

from zsim.define import ANOMALY_MAPPING
from zsim.models.event_enums import ListenerBroadcastSignal as LBS
from zsim.sim_progress import Report
from zsim.sim_progress.anomaly_bar.CopyAnomalyForOutput import Disorder
from zsim.sim_progress.calculation.anomaly_calculator import CalDisorder

from ..base import BaseEventHandler
from ..context import EventContext


class DisorderEventHandler(BaseEventHandler):
    """紊乱事件处理器"""

    def __init__(self):
        super().__init__("disorder")

    def can_handle(self, event: Any) -> bool:
        return type(event) is Disorder

    def handle(self, event: Disorder, context: EventContext) -> None:
        """处理紊乱事件"""
        enemy = self._get_context_enemy(context)
        active_buff_view = self._get_context_active_buff_view(context)
        sim_instance = self._get_context_sim_instance(context)
        tick = self._get_context_tick(context)

        # 广播紊乱事件
        sim_instance.listener_manager.broadcast_event(event=event, signal=LBS.DISORDER_SETTLED)

        # 计算紊乱伤害
        calculator = CalDisorder(
            disorder_obj=event,
            enemy_obj=enemy,
            dynamic_buff=active_buff_view,
            sim_instance=sim_instance,
        )

        damage_disorder = calculator.cal_anomaly_dmg()
        stun = calculator.cal_disorder_stun()

        # 更新敌人眩晕值
        enemy.update_stun(stun)

        Report.report_dmg_result(
            tick=tick,
            element_type=event.element_type,
            skill_tag=ANOMALY_MAPPING[event.element_type],
            dmg_expect=round(damage_disorder, 2),
            dmg_crit=round(damage_disorder, 2),
            is_anomaly=True,
            is_disorder=True,
            stun=round(stun, 2),
            buildup=0,
            **enemy.dynamic.get_status(),
            UUID=event.UUID if event.UUID is not None else "",
        )
