from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Protocol

from zsim.sim_progress.data_struct.planned_queue import PlannedEventQueue


class WakeupSource(Protocol):
    """声明某个子系统下一次需要被主循环唤醒的模拟 tick。"""

    name: str

    def next_wakeup_tick(self, current_tick: int) -> int | None:
        """返回严格晚于 current_tick 的下一次唤醒 tick；空闲时返回 None。"""


@dataclass(frozen=True, slots=True)
class FixedTickWakeupSource:
    name: str
    tick: int | None

    def next_wakeup_tick(self, current_tick: int) -> int | None:
        if self.tick is None or self.tick <= current_tick:
            return None
        return self.tick


@dataclass(frozen=True, slots=True)
class StopTickWakeupSource:
    """用于保留模拟终止边界的唤醒源。"""

    tick: int | None
    name: str = "stop-tick"

    def next_wakeup_tick(self, current_tick: int) -> int | None:
        if self.tick is None or self.tick <= current_tick:
            return None
        return self.tick


@dataclass(frozen=True, slots=True)
class ConservativeTickWakeupSource:
    """子系统仍有隐式轮询需求时使用的逐 tick 临时唤醒源。"""

    name: str = "conservative-next-tick"

    def next_wakeup_tick(self, current_tick: int) -> int:
        return current_tick + 1


@dataclass(frozen=True, slots=True)
class PlannedEventQueueWakeupSource:
    planned_queue: PlannedEventQueue
    name: str = "planned-event-queue"

    def next_wakeup_tick(self, current_tick: int) -> int | None:
        return self.planned_queue.next_due_tick(after_tick=current_tick)


class SimulationClock:
    """负责推进模拟 tick，不直接依赖各子系统内部细节。"""

    def next_wakeup_tick(
        self,
        *,
        current_tick: int,
        wakeup_sources: Iterable[WakeupSource],
    ) -> int:
        candidates: list[tuple[int, str]] = []
        for source in wakeup_sources:
            tick = source.next_wakeup_tick(current_tick)
            if tick is None:
                continue
            if tick <= current_tick:
                raise ValueError(
                    f"WakeupSource {source.name!r} returned non-future tick "
                    f"{tick} for current tick {current_tick}"
                )
            candidates.append((tick, source.name))

        if not candidates:
            raise ValueError("SimulationClock 至少需要一个未来的 WakeupSource")

        return min(tick for tick, _ in candidates)
