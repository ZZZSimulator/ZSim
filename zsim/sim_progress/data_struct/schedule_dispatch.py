from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, Iterable

from zsim.sim_progress.data_struct.planned_queue import ensure_planned_event_queue

if TYPE_CHECKING:
    from zsim.simulator.dataclasses import ScheduleData
    from zsim.simulator.simulator_class import Simulator


class ScheduleDispatchPort(ABC):
    """计划事件发布接口，只负责计划事件入队。"""

    @abstractmethod
    def publish_scheduled(self, event: Any) -> None:
        """发布单个计划事件。"""

    def publish_scheduled_batch(self, events: Iterable[Any]) -> None:
        """按输入顺序发布多条计划事件。"""
        for event in events:
            self.publish_scheduled(event)


class ScheduledEventEmitter:
    """面向生产者的计划事件发射器，内部通过派发端口入队。"""

    def __init__(self, dispatch_port: ScheduleDispatchPort) -> None:
        self._dispatch_port = dispatch_port

    def emit_scheduled(self, event: Any) -> None:
        self._dispatch_port.publish_scheduled(event)

    def emit_scheduled_batch(self, events: Iterable[Any]) -> None:
        for event in events:
            self.emit_scheduled(event)


class ScheduledEventEmitterProvider:
    """创建新的计划事件发射器，不向调用方暴露派发端口构造细节。"""

    def __init__(self, dispatch_port_factory: Callable[[], ScheduleDispatchPort]) -> None:
        self._dispatch_port_factory = dispatch_port_factory

    @classmethod
    def from_sim_instance(
        cls,
        sim_instance: "Simulator",
    ) -> "ScheduledEventEmitterProvider":
        return cls(lambda: create_schedule_dispatch_port(sim_instance=sim_instance))

    @classmethod
    def from_sim_instance_getter(
        cls,
        sim_instance_getter: Callable[[], "Simulator | None"],
    ) -> "ScheduledEventEmitterProvider":
        return cls(lambda: create_schedule_dispatch_port(sim_instance=sim_instance_getter()))

    @classmethod
    def from_schedule_data(
        cls,
        schedule_data: "ScheduleData",
    ) -> "ScheduledEventEmitterProvider":
        return cls(lambda: create_schedule_dispatch_port(schedule_data=schedule_data))

    def create_emitter(self) -> ScheduledEventEmitter:
        return ScheduledEventEmitter(self._dispatch_port_factory())


class _ScheduleQueueOwner(ABC):
    """封装计划事件派发端口背后的底层队列写入。"""

    @abstractmethod
    def enqueue(self, event: Any) -> None:
        """向持有的队列追加一个计划事件。"""


class _ScheduleDataQueueOwner(_ScheduleQueueOwner):
    def __init__(self, schedule_data: "ScheduleData") -> None:
        self._schedule_data = schedule_data

    def enqueue(self, event: Any) -> None:
        # 发布时重新解析队列持有者，确保队列重绑定后仍能写入最新对象。
        ensure_planned_event_queue(self._schedule_data).enqueue(event)


class _QueueBackedScheduleDispatchPort(ScheduleDispatchPort):
    def __init__(self, queue_owner: _ScheduleQueueOwner) -> None:
        self._queue_owner = queue_owner

    def publish_scheduled(self, event: Any) -> None:
        self._queue_owner.enqueue(event)


def create_schedule_dispatch_port(
    *,
    sim_instance: "Simulator | None" = None,
    schedule_data: "ScheduleData | None" = None,
) -> ScheduleDispatchPort:
    """创建计划事件发布入口，但不向生产者暴露原始 `event_list`。"""
    if schedule_data is None:
        if sim_instance is None:
            raise ValueError("sim_instance 和 schedule_data 不能同时为空")
        schedule_data = sim_instance.schedule_data
    return _QueueBackedScheduleDispatchPort(_ScheduleDataQueueOwner(schedule_data))


__all__ = [
    "ScheduleDispatchPort",
    "ScheduledEventEmitter",
    "ScheduledEventEmitterProvider",
    "create_schedule_dispatch_port",
]
