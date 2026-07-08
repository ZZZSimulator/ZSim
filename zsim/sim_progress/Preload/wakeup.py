from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING

from zsim.sim_progress.Preload.PreloadEngine import SwapCancelValidateEngine

if TYPE_CHECKING:
    from zsim.sim_progress.Preload.PreloadClass import PreloadClass
    from zsim.sim_progress.Preload.SkillsQueue import SkillNode


@dataclass(frozen=True, slots=True)
class PreloadWakeupSource:
    """推算下一次 Preload/APL 可观察到的动作边界。"""

    preload: "PreloadClass"
    name: str = "preload-action"

    def next_wakeup_tick(self, current_tick: int) -> int | None:
        data = self.preload.preload_data
        candidates: list[int] = []

        if data.preload_action_list_before_confirm:
            for pending_skill in data.preload_action_list_before_confirm:
                pending_tick = pending_skill[3] if len(pending_skill) > 3 else None
                if pending_tick is not None and pending_tick > current_tick:
                    candidates.append(int(pending_tick))
                else:
                    candidates.append(current_tick + 1)

        for stack in data.personal_node_stack.values():
            for node in stack:
                self._collect_node_wakeups(node, current_tick, candidates)
            self._collect_char_change_cd_wakeup(stack, current_tick, candidates)

        for node in data.current_node_stack:
            self._collect_node_wakeups(node, current_tick, candidates)

        if not data.personal_node_stack:
            candidates.append(current_tick + 1)

        future_candidates = [tick for tick in candidates if tick > current_tick]
        if not future_candidates:
            return None
        return min(future_candidates)

    @staticmethod
    def _collect_node_wakeups(
        node: "SkillNode",
        current_tick: int,
        candidates: list[int],
    ) -> None:
        if node.preload_tick > current_tick:
            candidates.append(node.preload_tick)
        if node.end_tick > current_tick:
            candidates.append(node.end_tick)
        for hit_tick in getattr(node, "tick_list", ()) or ():
            wakeup_tick = math.ceil(hit_tick)
            if wakeup_tick > current_tick:
                candidates.append(wakeup_tick)
        skill_labels = getattr(node.skill, "labels", None)
        if skill_labels is not None and "additional_damage" in skill_labels:
            return
        swap_tick = (
            node.preload_tick
            + node.skill.swap_cancel_ticks
            + SwapCancelValidateEngine.spawn_lag_time(node)
        )
        if swap_tick > current_tick:
            candidates.append(swap_tick)

    @staticmethod
    def _collect_char_change_cd_wakeup(
        stack: object,
        current_tick: int,
        candidates: list[int],
    ) -> None:
        peek = getattr(stack, "peek", None)
        if callable(peek):
            latest_node = peek()
        else:
            stack_items = list(stack)  # type: ignore[arg-type]
            latest_node = stack_items[-1] if stack_items else None
        if latest_node is None:
            return
        end_tick = getattr(latest_node, "end_tick", None)
        if end_tick is None:
            return
        change_cd_tick = int(end_tick) + 60
        if change_cd_tick > current_tick:
            candidates.append(change_cd_tick)


__all__ = ["PreloadWakeupSource"]
