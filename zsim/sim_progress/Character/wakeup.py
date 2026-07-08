from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping


@dataclass(frozen=True, slots=True)
class CharacterResourceThresholds:
    energy: tuple[float, ...] = ()
    special_resource: tuple[float, ...] = ()
    adrenaline: tuple[float, ...] = ()
    decibel: tuple[float, ...] = ()

    def has_any(self) -> bool:
        return bool(self.energy or self.special_resource or self.adrenaline or self.decibel)


@dataclass(frozen=True, slots=True)
class CharacterResourceWakeupSource:
    """推算角色资源下一次可能影响 APL 决策的 tick。"""

    char_obj_list: Iterable[object]
    thresholds_by_cid: Mapping[int, CharacterResourceThresholds] | None = None
    name: str = "character-resource"

    def next_wakeup_tick(self, current_tick: int) -> int | None:
        candidates: list[int] = []
        for char_obj in self.char_obj_list:
            next_resource_tick = getattr(char_obj, "next_resource_wakeup_tick", None)
            if not callable(next_resource_tick):
                continue
            thresholds = self._thresholds_for(char_obj)
            if thresholds is None:
                tick = next_resource_tick(current_tick)
            else:
                tick = next_resource_tick(current_tick, thresholds=thresholds)
            if tick is not None and tick > current_tick:
                candidates.append(tick)
        if not candidates:
            return None
        return min(candidates)

    def _thresholds_for(self, char_obj: object) -> CharacterResourceThresholds | None:
        if not self.thresholds_by_cid:
            return None
        cid = getattr(char_obj, "CID", None)
        try:
            cid_int = int(cid)
        except (TypeError, ValueError):
            return None
        thresholds = self.thresholds_by_cid.get(cid_int)
        if thresholds is None or not thresholds.has_any():
            return None
        return thresholds


__all__ = ["CharacterResourceThresholds", "CharacterResourceWakeupSource"]
