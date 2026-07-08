"""眩晕强制终止事件处理器"""

from typing import Any

from zsim.sim_progress.data_struct import StunForcedTerminationEvent

from ..base import BaseEventHandler
from ..context import EventContext


class StunForcedTerminationEventHandler(BaseEventHandler):
    """眩晕强制终止事件处理器"""

    def __init__(self):
        super().__init__("stun_forced_termination")

    def can_handle(self, event: Any) -> bool:
        return type(event) is StunForcedTerminationEvent

    def handle(self, event: StunForcedTerminationEvent, context: EventContext) -> None:
        """处理眩晕强制终止事件"""
        tick = self._get_context_tick(context)

        # 检查是否到达执行时间
        if tick < event.execute_tick:
            # 时间未到，将事件重新加入列表
            context.requeue_event(event)
            return

        # 执行事件
        event.execute_myself()
