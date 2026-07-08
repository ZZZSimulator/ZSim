"""
事件处理器工厂模块

该模块定义了事件处理的工厂类，用于管理各种类型的事件处理器。
"""

from collections.abc import Iterable
from typing import Any

from ..base import EventHandlerABC


class EventHandlerFactory:
    """事件处理器工厂类"""

    def __init__(self):
        self._handlers: dict[str, EventHandlerABC] = {}
        self._handler_cache: dict[type, EventHandlerABC] = {}
        self._cache_hits = 0
        self._cache_misses = 0

    def register_handler(self, handler: EventHandlerABC) -> None:
        """
        注册事件处理器

        Args:
            handler: 事件处理器实例

        Raises:
            ValueError: 如果已存在相同事件类型的处理器
        """
        event_type = handler.event_type
        if event_type in self._handlers:
            raise ValueError(f"事件类型 '{event_type}' 的处理器已存在")
        self._handlers[event_type] = handler
        self.clear_cache()

    def replace_handlers(self, handlers: Iterable[EventHandlerABC]) -> None:
        """替换已注册的处理器集合，并重置查找缓存。"""
        self.clear_handlers()
        for handler in handlers:
            self.register_handler(handler)

    def get_handler(self, event: Any) -> EventHandlerABC | None:
        """
        获取适合处理指定事件的处理器（带缓存）

        Args:
            event: 待处理的事件对象

        Returns:
            EventHandler | None: 如果找到合适的处理器则返回，否则返回None
        """
        # 检查缓存
        event_type = type(event)
        if event_type in self._handler_cache:
            self._cache_hits += 1
            return self._handler_cache[event_type]

        # 缓存未命中，查找处理器
        for handler in self._handlers.values():
            if handler.can_handle(event):
                self._handler_cache[event_type] = handler
                self._cache_misses += 1
                return handler

        self._cache_misses += 1
        return None

    def get_handler_by_type(self, event_type: str) -> EventHandlerABC | None:
        """
        根据事件类型获取处理器

        Args:
            event_type: 事件类型名称

        Returns:
            EventHandler | None: 如果找到处理器则返回，否则返回None
        """
        return self._handlers.get(event_type)

    def list_handlers(self) -> list[str]:
        """
        获取所有已注册的处理器类型列表

        Returns:
            list[str]: 处理器类型名称列表
        """
        return list(self._handlers.keys())

    def clear_handlers(self) -> None:
        """清除所有已注册的处理器"""
        self._handlers.clear()
        self.clear_cache()

    def get_cache_stats(self) -> dict[str, int | float]:
        """
        获取缓存统计信息

        Returns:
            dict[str, int]: 包含缓存命中率和统计信息的字典
        """
        total_requests = self._cache_hits + self._cache_misses
        hit_rate = (self._cache_hits / total_requests * 100) if total_requests > 0 else 0

        return {
            "cache_hits": self._cache_hits,
            "cache_misses": self._cache_misses,
            "total_requests": total_requests,
            "hit_rate_percent": round(hit_rate, 2),
        }

    def reset_cache_stats(self) -> None:
        """重置缓存统计信息"""
        self._cache_hits = 0
        self._cache_misses = 0

    def clear_cache(self) -> None:
        """清除处理器缓存"""
        self._handler_cache.clear()
        self.reset_cache_stats()


# 全局处理器工厂实例
event_handler_factory = EventHandlerFactory()

__all__ = ["EventHandlerFactory", "event_handler_factory"]
