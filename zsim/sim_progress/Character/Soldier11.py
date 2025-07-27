from zsim.sim_progress.Preload import SkillNode

from .character import Character
from .utils.filters import _skill_node_filter


class Soldier11(Character):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.fire_suppression: int = 0  # 强制的火力镇压
        self.settle_tick: int | None = None

    def special_resources(self, *args, **kwargs) -> None:
        """模拟11号的火力镇压机制"""
        # 输入类型检查
        skill_nodes: list[SkillNode] = _skill_node_filter(*args, **kwargs)
        assert self.sim_instance is not None
        tick: int = self.sim_instance.tick
        for node in skill_nodes:
            if self.settle_tick is not None:
                # 超时重置
                if tick - self.settle_tick >= 480:
                    self.fire_suppression = 0
                    self.settle_tick = None
            # 过滤非11号技能
            if "1041" not in node.skill_tag:
                continue
            # 获取层数逻辑
            if node.skill_tag in ["1041_E_EX", "1041_QTE", "1041_Q"]:
                self.fire_suppression = 8
                self.settle_tick = tick
            # 消耗层数逻辑
            if "SNA" in node.skill_tag and self.fire_suppression > 0:
                self.fire_suppression -= 1

    def get_resources(self, *args, **kwargs) -> tuple[str | None, int | float | None]:
        return "火力镇压", self.fire_suppression
