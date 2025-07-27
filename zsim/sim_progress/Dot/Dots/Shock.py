from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from .. import Dot

if TYPE_CHECKING:
    from zsim.sim_progress.anomaly_bar.AnomalyBarClass import AnomalyBar
    from zsim.simulator.simulator_class import Simulator


class Shock(Dot):
    def __init__(self, bar: "AnomalyBar | None" = None, sim_instance: "Simulator | None" = None):
        super().__init__(bar, sim_instance=sim_instance)  # 调用父类Dot的初始化方法
        self.ft = self.DotFeature(sim_instance=sim_instance)

    @dataclass
    class DotFeature(Dot.DotFeature):
        sim_instance: "Simulator | None"
        char_name_box: list[str] = field(init=False)
        exist_buff_dict: dict[str, dict[str, object]] = field(init=False)
        update_cd: int | float = 60
        index: str | None = "Shock"
        name: str | None = "感电"
        dot_from: str | None = "enemy"
        effect_rules: int | None = 2
        max_count: int | None = 1
        incremental_step: int | None = 1
        """
        如果丽娜在角色列表里，灼烧和最大生效次数就要发生变化。
        """
        max_duration: int | None = None
        max_effect_times: int = 30

        def __post_init__(self):
            if self.sim_instance is None:
                raise ValueError("sim_instance is None, but it should not be.")

            self.char_name_box = self.sim_instance.init_data.name_box
            self.exist_buff_dict = self.sim_instance.load_data.exist_buff_dict
            if "丽娜" in self.char_name_box:
                if "Buff-角色-丽娜-组队被动-延长感电" in self.exist_buff_dict["丽娜"]:
                    self.max_duration = 600 + 180
                else:
                    self.max_duration = 600
            else:
                self.max_duration = 600
