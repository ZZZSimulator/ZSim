from __future__ import annotations

from collections.abc import Callable, Iterable, MutableSequence
from typing import Any, cast

from zsim.sim_progress.Dot.BaseDot import Dot


class DotRuntimeStateAdapter:
    def __init__(self, dynamic_state: Any) -> None:
        self._dynamic_state = dynamic_state

    @classmethod
    def from_enemy(cls, enemy: Any) -> "DotRuntimeStateAdapter":
        return cls(enemy.dynamic)

    @property
    def _dot_list(self) -> MutableSequence[Dot]:
        return cast(MutableSequence[Dot], self._dynamic_state.dynamic_dot_list)

    def snapshot(self) -> tuple[Dot, ...]:
        return tuple(self._dot_list)

    def find_by_index(self, dot_index: str | None) -> Dot | None:
        for dot in self.snapshot():
            if dot.ft.index == dot_index:
                return dot
        return None

    def find_active_by_index(self, dot_index: str | None) -> Dot | None:
        for dot in self.snapshot():
            if dot.ft.index == dot_index and dot.dy.active:
                return dot
        return None

    def register(self, dot: Dot) -> None:
        self._dot_list.append(dot)

    def register_if_absent(self, dot: Dot) -> bool:
        if self.find_by_index(dot.ft.index) is not None:
            return False
        self.register(dot)
        return True

    def replace_by_index(self, dot: Dot, timenow: int) -> tuple[Dot, ...]:
        replaced: list[Dot] = []
        for existing_dot in self.snapshot():
            if existing_dot.ft.index == dot.ft.index:
                existing_dot.end(timenow)
                self._dot_list.remove(existing_dot)
                replaced.append(existing_dot)
        self.register(dot)
        return tuple(replaced)

    def remove_matching(self, predicate: Callable[[Dot], bool]) -> tuple[Dot, ...]:
        return self.remove_all(dot for dot in self.snapshot() if predicate(dot))

    def remove_all(self, dots: Iterable[Dot]) -> tuple[Dot, ...]:
        removed: list[Dot] = []
        for dot in dots:
            self._dot_list.remove(dot)
            removed.append(dot)
        return tuple(removed)
