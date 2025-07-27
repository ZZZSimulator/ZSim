from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np

from .. import Dot

if TYPE_CHECKING:
    from zsim.sim_progress.anomaly_bar.AnomalyBarClass import AnomalyBar
    from zsim.simulator.simulator_class import Simulator


class Freez(Dot):
    def __init__(self, bar: "AnomalyBar | None" = None, sim_instance: "Simulator | None" = None):
        super().__init__(bar, sim_instance=sim_instance)  # 调用父类Dot的初始化方法
        self.ft = self.DotFeature(sim_instance=sim_instance)

    @dataclass
    class DotFeature(Dot.DotFeature):
        sim_instance: "Simulator | None"
        enemy = None
        update_cd: int | float = np.inf
        index: str | None = "Freez"
        name: str | None = "冻结"
        dot_from: str | None = "enemy"
        effect_rules: int | None = 4
        max_count: int | None = 1
        incremental_step: int | None = 1
        max_duration: int | None = None
        max_effect_times: int = 1

        def __post_init__(self):
            if self.sim_instance is None:
                raise ValueError("sim_instance is None, but it should not be.")

            self.enemy = self.sim_instance.schedule_data.enemy
            self.max_duration = int(240 * (1 + self.enemy.freeze_resistance))

    def start(self, timenow: int):
        self.dy.active = True
        self.dy.start_ticks = timenow
        self.dy.last_effect_ticks = timenow
        if self.ft.max_duration is not None:
            self.dy.end_ticks = self.dy.start_ticks + self.ft.max_duration
        self.history.start_times += 1
        self.history.last_start_ticks = timenow
        self.dy.count = 1
        self.dy.effect_times = 1
        self.dy.ready = True
