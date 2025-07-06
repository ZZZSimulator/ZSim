from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from .. import Dot

if TYPE_CHECKING:
    from zsim.simulator.simulator_class import Simulator


class Corruption(Dot):
    def __init__(self, bar=None, sim_instance: "Simulator" = None):
        super().__init__(bar, sim_instance=sim_instance)  # 调用父类Dot的初始化方法
        self.ft = self.DotFeature(sim_instance=sim_instance)

    @dataclass
    class DotFeature(Dot.DotFeature):
        sim_instance: "Simulator"
        char_name_box: list[str] = field(init=False)
        update_cd: int = 30
        index: str = "Corruption"
        name: str = "侵蚀"
        dot_from: str = "enemy"
        effect_rules: int = 2
        max_count: int = 1
        incremental_step: int = 1
        max_duration: int | None = None
        max_effect_times = 30

        def __post_init__(self):
            self.char_name_box = self.sim_instance.init_data.name_box
            self.max_duration: int = 600
            """
            如果某角色在角色列表里，侵蚀和最大生效次数就要发生变化。
            """
            if "某角色" in self.char_name_box:
                self.max_duration: int = 600 + 180
