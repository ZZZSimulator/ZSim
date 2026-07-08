from __future__ import annotations

from dataclasses import dataclass
from typing import Any

RINA_SHOCK_DURATION_EXTENSION_BUFF_INDEX = "Buff-角色-丽娜-组队被动-延长感电"


@dataclass(frozen=True)
class DotInitializationReadContext:
    name_box: list[str]
    exist_buff_dict: dict[str, dict[str, object]]

    @classmethod
    def from_sim_instance(cls, sim_instance: Any) -> "DotInitializationReadContext":
        return cls(
            name_box=sim_instance.init_data.name_box,
            exist_buff_dict=sim_instance.load_data.exist_buff_dict,
        )

    def has_rina_shock_duration_extension(self) -> bool:
        if "丽娜" not in self.name_box:
            return False
        return RINA_SHOCK_DURATION_EXTENSION_BUFF_INDEX in self.exist_buff_dict["丽娜"]
