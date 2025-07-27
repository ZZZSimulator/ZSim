from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from .. import Dot

if TYPE_CHECKING:
    from zsim.sim_progress.anomaly_bar.AnomalyBarClass import AnomalyBar
    from zsim.simulator.simulator_class import Simulator


class AuricInkCorruption(Dot):
    def __init__(self, bar: "AnomalyBar | None", sim_instance: "Simulator | None"):
        super().__init__(bar, sim_instance=sim_instance)  # 调用父类Dot的初始化方法
        self.ft = self.DotFeature(sim_instance=sim_instance)

    @dataclass
    class DotFeature(Dot.DotFeature):
        sim_instance: "Simulator | None"
        char_name_box: list[str] = field(init=False)
        update_cd: int | float = 30
        index: str | None = "AuricInkCorruption"
        name: str | None = "玄墨侵蚀"
        dot_from: str | None = "enemy"
        effect_rules: int | None = 2
        max_count: int | None = 1
        incremental_step: int | None = 1
        max_duration: int | None = 600
        max_effect_times = 30

        def __post_init__(self):
            if self.sim_instance is None:
                raise ValueError("sim_instance is None, but it should not be.")

            self.char_name_box = self.sim_instance.init_data.name_box
            """
            如果某角色在角色列表里，侵蚀和最大生效次数就要发生变化。
            """
            if "某角色" in self.char_name_box:
                self.max_duration = 600 + 180
