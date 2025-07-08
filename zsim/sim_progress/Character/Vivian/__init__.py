from ..utils.filters import _skill_node_filter
from ..character import Character
from .FeatherManager import FeatherManager
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from zsim.sim_progress.Preload import SkillNode


class Vivian(Character):
    """薇薇安的特殊资源模块"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.feather_manager = FeatherManager(
            self
        )  # 羽毛管理器（飞羽、护羽的获取、切换）
        self.state_level = 0  # 状态等级，0是无状态，1是开伞，2是飘浮

    @property
    def noblewoman_state(self) -> bool:  # 判定当前是否为开伞状态（淑女仪态）
        return self.state_level == 1

    @property
    def fluttering_frock_state(self) -> bool:  # 判定当前是否为飘浮状态（裙裾浮游）
        return self.state_level == 2

    def __check_node(self, skill_node: "SkillNode") -> None:
        """检查传入的SkillNode，是否符合当前的状态。"""
        skill_tag = skill_node.skill_tag
        if skill_tag not in ["1331_SNA_0", "1331_SNA_1", "1331_SNA_2"]:
            return
        if skill_tag == "1331_SNA_0":
            if not self.fluttering_frock_state:
                raise ValueError(
                    f"薇薇安的SNA_0的作用是从飘浮状态退回开伞状态，而当前状态等级为{self.state_level}，无法释放{skill_tag}"
                )
        elif skill_tag == "1331_SNA_1":
            if not self.noblewoman_state:
                raise ValueError(
                    f"薇薇安的SNA_1只能在开伞状态下释放，而当前状态等级为{self.state_level}，无法释放{skill_tag}"
                )
        elif skill_tag == "1331_SNA_2":
            if not self.fluttering_frock_state:
                raise ValueError(
                    f"薇薇安的SNA_2只能在飘浮状态下释放，而当前状态等级为{self.state_level}，无法释放{skill_tag}"
                )

    def special_resources(self, *args, **kwargs) -> None:
        # 输入类型检查
        skill_nodes: list[SkillNode] = _skill_node_filter(*args, **kwargs)
        for node in skill_nodes:
            if "1331" not in node.skill_tag:
                continue
            self.__check_node(node)
            if node.skill_tag in ["1331_SNA_0", "1331_BH_Aid", "1331_NA_4"]:
                # 进入开伞状态
                self.state_level = 1
            elif node.skill_tag == "1331_SNA_2":
                # 退回最初状态
                self.state_level = 0
            elif node.skill_tag in [
                "1331_SNA_1",
                "1331_E_EX",
                "1331_CA",
                "1331_QTE",
                "1331_Q",
                "1331_Assault_Aid",
            ]:
                # 直接飘浮
                self.state_level = 2
            else:
                return

    def get_resources(self) -> tuple[str, int]:
        return "护羽", self.feather_manager.guard_feather

    def get_special_stats(self, *args, **kwargs) -> dict[str, int | float | bool]:
        return {
            "护羽数量": self.feather_manager.guard_feather,
            "飞羽数量": self.feather_manager.flight_feather,
            "裙裾浮游": self.fluttering_frock_state,
            "淑女仪态": self.noblewoman_state,
        }
