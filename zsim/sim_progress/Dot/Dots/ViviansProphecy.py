from dataclasses import dataclass
from typing import TYPE_CHECKING

from zsim.sim_progress.Buff import JudgeTools
from zsim.sim_progress.Preload.SkillsQueue import spawn_node

from .. import Dot

if TYPE_CHECKING:
    from zsim.sim_progress.anomaly_bar.AnomalyBarClass import AnomalyBar
    from zsim.simulator.simulator_class import Simulator


class ViviansProphecy(Dot):
    def __init__(self, bar: "AnomalyBar | None" = None, sim_instance: "Simulator | None" = None):
        super().__init__(bar=bar, sim_instance=sim_instance)  # 调用父类Dot的初始化方法
        self.ft = self.DotFeature(sim_instance=sim_instance)
        if sim_instance is None:
            raise ValueError("sim_instance is None, but it should not be.")

        self.preload_data = JudgeTools.find_preload_data(sim_instance=sim_instance)
        tick = JudgeTools.find_tick(sim_instance=sim_instance)
        self.skill_node_data = spawn_node("1331_Core_Passive", tick, self.preload_data.skills)

    @dataclass
    class DotFeature(Dot.DotFeature):
        sim_instance: "Simulator | None"
        update_cd: int | float = 33
        index: str | None = "ViviansProphecy"
        name: str | None = "薇薇安的预言"
        dot_from: str | None = "薇薇安"
        effect_rules: int | None = 1
        max_count: int | None = 999999
        incremental_step: int | None = 1
        max_duration: int | None = 999999
        complex_exit_logic = True

    def exit_judge(self, **kwargs):
        """薇薇安的预言 dot的退出逻辑：敌人只要处于异常状态，就不会退出。"""
        enemy = kwargs.get("enemy", None)
        if enemy is None:
            return
        from zsim.sim_progress.Enemy import Enemy

        if not isinstance(enemy, Enemy):
            raise TypeError("enemy参数必须是Enemy类的实例")
        if not enemy.dynamic.is_under_anomaly():
            self.dy.active = False
