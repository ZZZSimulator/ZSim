from typing import TYPE_CHECKING

from zsim.sim_progress.Report import report_to_log

from .character import Character
from .utils.filters import _skill_node_filter

if TYPE_CHECKING:
    from zsim.sim_progress.Preload import SkillNode


class Ellen(Character):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.flash_freeze: int = 0

    def special_resources(self, *args, **kwargs) -> None:
        """模拟艾莲的急冻充能"""
        # 输入类型检查
        skill_nodes: list[SkillNode] = _skill_node_filter(*args, **kwargs)
        for node in skill_nodes:
            if "1191" not in node.skill_tag:
                continue
            if node.skill_tag in ["1191_SNA_1", "1191_SNA_2", "1191_SNA_3"]:
                self.flash_freeze -= 1
                if self.flash_freeze < 0:
                    report_to_log(
                        f"[Character] 释放 {node.skill_tag} 时，{self.NAME}的急冻充能不足，请检查技能树"
                    )
            if self.flash_freeze < 3:
                if node.skill_tag in ["1191_E_EX", "1191_E_EX_A", "1191_RA_NFC"]:
                    self.flash_freeze += 1
                    report_to_log(f"[Character] {self.NAME}的急冻充能被更新为：{self.flash_freeze}")
                if node.skill_tag == "1191_RA_FC":
                    self.flash_freeze += 3
                    report_to_log(f"[Character] {self.NAME}的急冻充能被更新为：{self.flash_freeze}")
            self.flash_freeze = max(self.flash_freeze, 0)
            self.flash_freeze = min(self.flash_freeze, 3)

    def get_resources(self, *args, **kwargs) -> tuple[str | None, int | float | None]:
        return "急冻充能", self.flash_freeze
