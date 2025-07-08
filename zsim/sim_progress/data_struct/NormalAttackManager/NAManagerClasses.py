from .BaseNAManager import BaseNAManager

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from zsim.sim_progress.Character.character import Character


class YanagiNAManager(BaseNAManager):
    def __init__(self, char_obj, rule_inventory_dict: dict):
        super().__init__(char_obj, rule_inventory_dict)
        self.char: "Character" = char_obj
        self.na_rule_inventory = rule_inventory_dict
        self.RULE_MAP = {
            "default": lambda: self.char.get_special_stats()["当前架势"]
            and not self.char.get_special_stats()["森罗万象状态"],
            "normal_kagen": lambda: (not self.char.get_special_stats()["当前架势"])
            and not self.char.get_special_stats()["森罗万象状态"],
            "shinra_jougen": lambda: self.char.get_special_stats()["当前架势"]
            and self.char.get_special_stats()["森罗万象状态"],
            "shinra_kagen": lambda: (not self.char.get_special_stats()["当前架势"])
            and self.char.get_special_stats()["森罗万象状态"],
        }

    @property
    def first_hit(self) -> str:
        return (
            "1221_NA_1" if self.char.get_special_stats()["当前架势"] else "1221_SNA_1"
        )


class HugoNAManager(BaseNAManager):
    def __init__(self, char_obj, rule_inventory_dict: dict):
        super().__init__(char_obj, rule_inventory_dict)
        self.char = char_obj
        self.na_rule_inventory = rule_inventory_dict
        from zsim.define import HUGO_NA_MODE_LEVEL

        self.RULE_MAP = {
            "default": lambda: HUGO_NA_MODE_LEVEL == 0,
            "balanced_mode": lambda: HUGO_NA_MODE_LEVEL == 1,
            "perfection_mode": lambda: HUGO_NA_MODE_LEVEL == 2,
            "only_full_charge_na": lambda: HUGO_NA_MODE_LEVEL == 3,
        }
