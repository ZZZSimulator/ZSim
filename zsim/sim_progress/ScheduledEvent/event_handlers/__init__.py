"""
事件处理器模块

该模块定义了事件处理的工厂类，用于管理各种类型的事件处理器。
"""

from .base import EventHandlerABC
from .context import EventContext
from .handlers import (
    create_default_event_handler_factory,
    event_handler_factory,
    register_all_handlers,
)

__all__ = [
    "EventHandlerABC",
    "create_default_event_handler_factory",
    "event_handler_factory",
    "register_all_handlers",
    "EventContext",
]
