from typing import TYPE_CHECKING

from ..character import Character
from ..utils.filters import _skill_node_filter
from .AfterShockManager import AfterShockManager

if TYPE_CHECKING:
    from zsim.sim_progress.Preload import SkillNode


class Trigger(Character):
    """扳机的特殊资源"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.after_shock_manager = AfterShockManager(self)
        self.purge = 0  # 决意值
        self.max_purge = 100 if self.cinema < 1 else 125
        self.purge_gain_ratio = 1 if self.cinema < 1 else 1.25
        self.sniper_stance = False  # 狙击姿态

    def special_resources(self, *args, **kwargs) -> None:
        """
        这个函数在preload阶段被调用，主要用于更新协战状态、以及自身的决意值；
        而这里的更新主要是状态的刷新、持续时间的增加以及层数的增加，
        至于抛出协同攻击、层数减少以及决意值消耗，则在Buff阶段进行执行，这边只要留好接口即可；
        接口：应该是char.spawn_after_shock，对内调用self.after_shock_manager的相应方法。
        """
        skill_nodes: list["SkillNode"] = _skill_node_filter(*args, **kwargs)
        tick = kwargs.get("tick", 0)
        for nodes in skill_nodes:
            _skill_tag = nodes.skill_tag
            # 1、筛去不是本角色的技能
            if "1361" not in _skill_tag:
                if nodes.active_generation:
                    self.sniper_stance = False
                continue

            # 2、处理传入的强化E、Q，更新协战状态
            self.after_shock_manager.coordinated_support_manager.update_myself(
                tick, nodes
            )
            if nodes.skill_tag in ["1361_SNA_1", "1361_SNA_2"]:
                if not self.sniper_stance:
                    raise ValueError(f"在非狙击姿态的情况下传入了{nodes.skill_tag}")
                purge_delta = 25 * self.purge_gain_ratio
                self.purge += purge_delta
                if self.purge > self.max_purge:
                    self.purge = self.max_purge
            elif nodes.skill_tag == "1361_SNA_0":
                if self.sniper_stance:
                    raise ValueError("在狙击姿态已经开启的情况下传入了1361_SNA_0")
                self.sniper_stance = True
            elif nodes.skill_tag == "1361_SNA_3":
                if not self.sniper_stance:
                    raise ValueError("在狙击姿态已经关闭的情况下传入了1361_SNA_3")
                self.sniper_stance = False

    def update_purge(self, skill_tag):
        """在Buff阶段更新决意值的函数！"""
        if skill_tag == "1361_CoAttack_A":
            if self.purge < 3:
                print(f"现有决意值不足以触发{skill_tag}！请检查函数逻辑！")
            self.purge = self.purge - 3 if self.purge >= 3 else 0
        elif skill_tag == "1361_CoAttack_1":
            if self.purge < 5:
                print(f"现有决意值不足以触发{skill_tag}！请检查函数逻辑！")
            self.purge = self.purge - 5 if self.purge >= 5 else 0

    def get_resources(self) -> tuple[str | None, int | float | bool | None]:
        return "决意值", self.purge

    def get_special_stats(self, *args, **kwargs) -> dict[str | None, object | None]:
        return {"狙击姿态": self.sniper_stance}
