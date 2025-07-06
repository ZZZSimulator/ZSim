from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np

from .. import Dot

if TYPE_CHECKING:
    from zsim.simulator.simulator_class import Simulator


class Freez(Dot):
    def __init__(self, bar=None, sim_instance: "Simulator" = None):
        super().__init__(bar, sim_instance=sim_instance)  # 调用父类Dot的初始化方法
        self.ft = self.DotFeature(sim_instance=sim_instance)

    @dataclass
    class DotFeature(Dot.DotFeature):
        sim_instance: "Simulator"
        enemy = None
        update_cd: int | float = np.inf
        index: str = "Freez"
        name: str = "冻结"
        dot_from: str = "enemy"
        effect_rules: int = 4
        max_count: int = 1
        incremental_step: int = 1
        max_duration: int | float | None = None
        max_effect_times = 1

        def __post_init__(self):
            self.enemy = self.sim_instance.schedule_data.enemy
            self.max_duration = 240 * (1 + self.enemy.freeze_resistance)

    def start(self, timenow):
        self.dy.active = True
        self.dy.start_ticks = timenow
        self.dy.last_effect_ticks = timenow
        self.dy.end_ticks = self.dy.start_ticks + self.ft.max_duration
        self.history.start_times += 1
        self.history.last_start_ticks = timenow
        self.dy.count = 1
        self.dy.effect_times = 1
        self.dy.ready = True
