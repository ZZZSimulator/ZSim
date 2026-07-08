from __future__ import annotations

import copy
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any, ClassVar

from .AnomalyBarClass import AnomalyBar

if TYPE_CHECKING:
    from zsim.sim_progress.Preload import SkillNode
    from zsim.simulator.simulator_class import Simulator


class _CopiedAnomalyBase(AnomalyBar):
    _CONSTRUCTOR_OWNED_FIELDS: ClassVar[tuple[str, ...]] = ()

    def __init__(
        self,
        anomaly_bar: AnomalyBar,
        *,
        active_by: "SkillNode | str | None" = None,
        sim_instance: "Simulator | None" = None,
    ) -> None:
        if not isinstance(anomaly_bar, AnomalyBar):
            raise TypeError(f"{anomaly_bar} 不是 AnomalyBar 类型")

        source_uuid = anomaly_bar.UUID
        copied_payload = self._copy_source_payload(anomaly_bar)
        self._install_copied_payload(copied_payload)
        self.source_uuid = source_uuid
        self._apply_explicit_overrides(active_by=active_by, sim_instance=sim_instance)

    @staticmethod
    def _copy_source_payload(anomaly_bar: AnomalyBar) -> AnomalyBar:
        return copy.deepcopy(anomaly_bar)

    def _install_copied_payload(self, copied_payload: AnomalyBar) -> None:
        self.__dict__ = copied_payload.__dict__.copy()

    def _apply_explicit_overrides(
        self,
        *,
        active_by: "SkillNode | str | None",
        sim_instance: "Simulator | None",
    ) -> None:
        if sim_instance is not None:
            self.sim_instance = sim_instance
        if active_by is not None:
            self._set_active_by(active_by)

    @property
    def activate_by(self) -> Any:
        return getattr(self, "_activate_by", self.activated_by)

    @activate_by.setter
    def activate_by(self, value: Any) -> None:
        self._activate_by = self._normalize_active_by(value)

    def _set_active_by(self, active_by: "SkillNode | str") -> None:
        self.activated_by = self._normalize_formula_owner(active_by)
        self._activate_by = self._normalize_active_by(active_by)

    def _normalize_active_by(self, active_by: "SkillNode | str") -> Any:
        if hasattr(active_by, "skill"):
            return active_by
        if not isinstance(active_by, str):
            return active_by
        if not active_by.isdigit():
            return active_by
        char_obj = self.sim_instance.char_data.find_char_obj(CID=int(active_by))
        if char_obj is None:
            return active_by
        return SimpleNamespace(
            char_name=char_obj.NAME,
            skill_tag=active_by,
            skill=SimpleNamespace(char_obj=char_obj),
        )

    def _normalize_formula_owner(self, active_by: "SkillNode | str") -> Any:
        normalized = self._normalize_active_by(active_by)
        if hasattr(normalized, "skill"):
            return normalized
        return self.activated_by


class NewAnomaly(_CopiedAnomalyBase):
    _CONSTRUCTOR_OWNED_FIELDS: ClassVar[tuple[str, ...]] = ()


class Disorder(_CopiedAnomalyBase):
    _CONSTRUCTOR_OWNED_FIELDS: ClassVar[tuple[str, ...]] = ("is_disorder",)

    def __init__(
        self,
        anomaly_bar: AnomalyBar,
        *,
        active_by: "SkillNode | str | None" = None,
        sim_instance: "Simulator | None" = None,
    ) -> None:
        super().__init__(anomaly_bar, active_by=active_by, sim_instance=sim_instance)
        self.is_disorder = True

    def _set_active_by(self, active_by: "SkillNode | str") -> None:
        self._activate_by = self._normalize_active_by(active_by)


class PolarityDisorder(Disorder):
    _CONSTRUCTOR_OWNED_FIELDS: ClassVar[tuple[str, ...]] = (
        *Disorder._CONSTRUCTOR_OWNED_FIELDS,
        "polarity_disorder_ratio",
        "additional_dmg_ap_ratio",
    )

    def __init__(
        self,
        anomaly_bar: AnomalyBar,
        polarity_ratio: float,
        *,
        active_by: "SkillNode | str | None" = None,
        sim_instance: "Simulator | None" = None,
    ) -> None:
        super().__init__(anomaly_bar, active_by=active_by, sim_instance=sim_instance)
        self.polarity_disorder_ratio = polarity_ratio
        self.additional_dmg_ap_ratio = 32


class DirgeOfDestinyAnomaly(NewAnomaly):
    _CONSTRUCTOR_OWNED_FIELDS: ClassVar[tuple[str, ...]] = ("anomaly_dmg_ratio",)

    def __init__(
        self,
        anomaly_bar: AnomalyBar,
        *,
        active_by: "SkillNode | str | None" = None,
        sim_instance: "Simulator | None" = None,
    ) -> None:
        super().__init__(anomaly_bar, active_by=active_by, sim_instance=sim_instance)
        self.anomaly_dmg_ratio = 1.0
