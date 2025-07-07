from ..Preload import SkillNode
from ..Report import report_to_log
from .character import Character
from .utils.filters import _skill_node_filter


class Zhuyuan(Character):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.shotshells = 0  # 霰弹个数
        if self.cinema >= 1:  # 影画1的额外子弹逻辑
            self.allow_restore = True
            self.QTE_STORED = 6
            self.Q_STORED = 9
            self.shotshells_warehouse: list = []
        else:
            self.allow_restore = False

    def special_resources(self, *args, **kwargs):
        # 输入类型检查
        skill_nodes: list[SkillNode] = _skill_node_filter(*args, **kwargs)
        for node in skill_nodes:
            # 攒子弹逻辑
            if node.skill_tag in [
                "1241_E_EX",
                "1241_E_EX_A",
                "1241_QTE",
                "1241_Q",
                "1241_Assault_Aid",
            ]:
                self.shotshells = min(self.shotshells + 3, 9)
                if self.allow_restore and node.skill_tag in ["1241_QTE", "1241_Q"]:
                    self.shotshells_warehouse.append(node.skill_tag)
            # 消耗子弹逻辑
            if "1241_S" in node.skill_tag:
                if self.shotshells <= 0:
                    report_to_log("[Zhuyuan]: 弹夹为空, 无法使用")
                    print("[Zhuyuan]:弹夹为空, 无法使用")
                self.shotshells = max(self.shotshells - 1, 0)
                if self.shotshells == 0 and self.allow_restore:
                    if self.shotshells_warehouse:
                        popping_shotshells = self.shotshells_warehouse.pop()
                        for shell in self.shotshells_warehouse[:]:
                            if shell == popping_shotshells:
                                self.shotshells_warehouse.remove(shell)
                        if popping_shotshells == "1241_QTE":
                            self.shotshells += self.QTE_STORED
                        elif popping_shotshells == "1241_Q":
                            self.shotshells += self.Q_STORED

    def get_resources(
        self, *args, **kwargs
    ) -> tuple[str | None, int | float | bool | None]:
        return "强化霰弹", self.shotshells

    def get_special_stats(self, *args, **kwargs) -> dict[str | None, object | None]:
        if self.allow_restore:
            stored_shotshells = (
                6 if "1241_QTE" in self.shotshells_warehouse else 0
            ) + (9 if "1241_Q" in self.shotshells_warehouse else 0)
        else:
            stored_shotshells = 0
        return {
            "强化霰弹": self.shotshells,
            "缓存霰弹": stored_shotshells,
            "强化霰弹(含缓存)": self.shotshells + stored_shotshells,
        }
