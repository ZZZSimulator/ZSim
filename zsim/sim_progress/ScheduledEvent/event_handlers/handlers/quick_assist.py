"""快速支援事件处理器"""

from typing import Any

from zsim.sim_progress.data_struct import QuickAssistEvent

from ..base import BaseEventHandler
from ..context import EventContext


class QuickAssistEventHandler(BaseEventHandler):
    """快速支援事件处理器"""

    def __init__(self):
        super().__init__("quick_assist")

    def can_handle(self, event: Any) -> bool:
        return isinstance(event, QuickAssistEvent)

    def handle(self, event: QuickAssistEvent, context: EventContext) -> None:
        """处理快速支援事件"""
        tick = self._get_context_tick(context)

        # 检查是否到达执行时间
        if tick < event.execute_tick:
            # 时间未到，将事件重新加入列表
            context.requeue_event(event)
            return

        # 执行事件
        event.execute_update(tick)
