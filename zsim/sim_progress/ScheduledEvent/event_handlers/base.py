from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Mapping, Sequence

from ..buff_runtime import BuffRuntimeReadPort
from ..runtime_command import RuntimeCommandPort
from .context import EventContext

if TYPE_CHECKING:
    from zsim.sim_progress.Buff import Buff
    from zsim.sim_progress.Enemy import Enemy
    from zsim.simulator.dataclasses import ScheduleData


class EventHandlerABC(ABC):
    """事件处理器抽象基类"""

    @abstractmethod
    def can_handle(self, event: Any) -> bool:
        """
        判断是否可以处理指定类型的事件

        Args:
            event: 待处理的事件对象

        Returns:
            bool: 如果可以处理该类型事件则返回 True，否则返回 False
        """
        pass

    @abstractmethod
    def handle(self, event: Any, context: EventContext) -> None:
        """
        处理事件

        Args:
            event: 待处理的事件对象
            context: 事件处理上下文，包含所需的数据和环境信息

        Raises:
            NotImplementedError: 如果子类未实现此方法
        """
        pass

    @property
    @abstractmethod
    def event_type(self) -> str:
        """
        返回处理器支持的事件类型名称

        Returns:
            str: 事件类型名称
        """
        pass


class BaseEventHandler(EventHandlerABC):
    """基础事件处理器，提供通用功能"""

    def __init__(self, event_type: str):
        self._event_type = event_type

    @property
    def event_type(self) -> str:
        return self._event_type

    def _get_context_data(self, context: EventContext) -> ScheduleData:
        """从上下文中获取 ScheduleData"""
        return context.get_data()

    def _get_context_tick(self, context: EventContext) -> int:
        """从上下文中获取当前 tick"""
        return context.get_tick()

    def _get_context_enemy(self, context: EventContext) -> Enemy:
        """从上下文中获取敌人对象"""
        return context.get_enemy()

    def _get_context_buff_runtime_view(self, context: EventContext) -> BuffRuntimeReadPort:
        """从上下文中获取 Buff runtime 只读视图"""
        return context.get_buff_runtime_view()

    def _get_context_runtime_command_port(self, context: EventContext) -> RuntimeCommandPort:
        """从上下文中获取 Buff runtime 写命令入口"""
        return context.get_runtime_command_port()

    def _get_context_runtime_active_buffs(
        self, context: EventContext, beneficiary: str
    ) -> Sequence["Buff"]:
        """从上下文中获取某个受益者的 runtime active Buff 只读列表"""
        return self._get_context_buff_runtime_view(context).get_active_buffs(beneficiary)

    def _get_context_active_buffs(
        self, context: EventContext, beneficiary: str
    ) -> Sequence["Buff"]:
        """从上下文中获取某个受益者的 active Buff 只读列表"""
        return self._get_context_runtime_active_buffs(context, beneficiary)

    def _get_context_runtime_active_buff_view(
        self, context: EventContext
    ) -> Mapping[str, Sequence["Buff"]]:
        """从上下文中获取所有受益者的 runtime active Buff 只读视图"""
        return self._get_context_buff_runtime_view(context).get_active_buff_view()

    def _get_context_active_buff_view(
        self, context: EventContext
    ) -> Mapping[str, Sequence["Buff"]]:
        """从上下文中获取所有受益者的 active Buff 只读视图"""
        return self._get_context_runtime_active_buff_view(context)

    def _get_context_runtime_exist_buff_snapshot(
        self, context: EventContext, beneficiary: str
    ) -> Mapping[str, "Buff"]:
        """从上下文中获取某个受益者的 runtime snapshot Buff 只读视图"""
        return self._get_context_buff_runtime_view(context).get_exist_buff_snapshot(beneficiary)

    def _get_context_exist_buff_snapshot(
        self, context: EventContext, beneficiary: str
    ) -> Mapping[str, "Buff"]:
        """从上下文中获取某个受益者的 snapshot Buff 只读视图"""
        return self._get_context_runtime_exist_buff_snapshot(context, beneficiary)

    def _get_context_runtime_exist_buff_snapshot_view(
        self, context: EventContext
    ) -> Mapping[str, Mapping[str, "Buff"]]:
        """从上下文中获取所有受益者的 runtime snapshot Buff 只读视图"""
        return self._get_context_buff_runtime_view(context).get_exist_buff_snapshot_view()

    def _get_context_exist_buff_snapshot_view(
        self, context: EventContext
    ) -> Mapping[str, Mapping[str, "Buff"]]:
        """从上下文中获取所有受益者的 snapshot Buff 只读视图"""
        return self._get_context_runtime_exist_buff_snapshot_view(context)

    def _get_context_action_stack(self, context: EventContext):
        """从上下文中获取动作栈"""
        return context.get_action_stack()

    def _get_context_sim_instance(self, context: EventContext):
        """从上下文中获取模拟器实例"""
        return context.get_sim_instance()

    def _validate_event(
        self, event: Any, expected_type: type | tuple[type, ...] | None = None
    ) -> None:
        """
        验证事件参数

        Args:
            event: 待验证的事件对象
            expected_type: 期望的事件类型，如果为 None 则只验证非 None

        Raises:
            TypeError: 当事件类型不符合期望时
            ValueError: 当事件为 None 时
        """
        if event is None:
            raise ValueError("事件对象不能为空")

        if expected_type is not None and not isinstance(event, expected_type):
            if isinstance(expected_type, tuple):
                expected_names = [t.__name__ for t in expected_type]
                raise TypeError(
                    f"期望事件类型为 {expected_names} 之一，实际得到 {type(event).__name__}"
                )
            raise TypeError(
                f"期望事件类型为 {expected_type.__name__}，实际得到 {type(event).__name__}"
            )

    def _validate_context(self, context: EventContext) -> None:
        """
        验证上下文数据

        Args:
            context: 待验证的上下文对象

        Raises:
            ValueError: 当上下文无效时
        """
        if not isinstance(context, EventContext):  # type: ignore
            raise TypeError("上下文必须是 EventContext 类型")

    def _handle_error(self, error: Exception, operation: str, event: Any = None) -> None:
        """
        统一错误处理方法

        Args:
            error: 发生的异常
            operation: 操作描述
            event: 相关事件对象，可选

        Raises:
            RuntimeError: 包装后的异常信息
        """
        error_msg = f"在 {operation} 时发生错误: {error}"
        if event is not None:
            error_msg = f"在处理事件 {type(event)} 时发生错误: {error}"

        raise RuntimeError(error_msg) from error
