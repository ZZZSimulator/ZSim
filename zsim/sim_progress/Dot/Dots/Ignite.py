from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from .. import Dot

if TYPE_CHECKING:
    from zsim.sim_progress.anomaly_bar.AnomalyBarClass import AnomalyBar
    from zsim.simulator.simulator_class import Simulator


class Ignite(Dot):
    """
    灼烧dot，固定时间，内置CD0.5s
    """

    def __init__(self, bar: "AnomalyBar | None" = None, sim_instance: "Simulator | None" = None):
        super().__init__(bar, sim_instance=sim_instance)  # 调用父类Dot的初始化方法
        self.ft = self.DotFeature(
            sim_instance=sim_instance
        )  # 用Ignite的DotFeature替代默认的DotFeature

    # 你可以在这里添加特定于Ignite的行为或方法
    @dataclass
    class DotFeature(Dot.DotFeature):
        sim_instance: "Simulator | None"
        char_name_box: list[str] = field(init=False)
        update_cd: int | float = 30
        index: str | None = "Ignite"
        name: str | None = "灼烧"
        dot_from: str | None = "enemy"
        effect_rules: int | None = 1
        max_count: int | None = 1
        incremental_step: int | None = 1
        max_duration: int | None = None
        max_effect_times: int = 30

        def __post_init__(self):
            if self.sim_instance is None:
                raise ValueError("sim_instance is None, but it should not be.")

            self.char_name_box = self.sim_instance.global_stats.name_box
            """
            如果柏妮思在角色列表里，灼烧和最大生效次数就要发生变化。
            """
            if "柏妮思" in self.char_name_box:
                self.max_duration = 600 + 180
            else:
                self.max_duration = 600
