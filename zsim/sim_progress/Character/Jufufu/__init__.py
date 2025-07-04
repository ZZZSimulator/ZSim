from sim_progress.Character.utils.filters import _skill_node_filter
from sim_progress.Character.character import Character
from sim_progress.Preload import SkillNode
from define import JUFUFU_REPORT
from .HuweiManagerClass import HuweiManager


class Jufufu(Character):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.momentum: int = 0   # 威势点数
        self.might: int = 0 if self.cinema < 1 else 100  # 威风点数，一影画及以上进场给100
        self.max_might: int = 200       # 威风点数上限
        self.max_momentum: int = 15     # 威势点数上限
        self.huwei_manager = HuweiManager(self)       # 虎威管理器

    def special_resources(self, *args, **kwargs) -> None:
        """橘福福的特殊资源模块的主函数"""
        skill_nodes: list[SkillNode] = _skill_node_filter(*args, **kwargs)
        tick = self.sim_instance.tick
        # TODO: 虎威管理器 自检。
        for node in skill_nodes:
            # TODO: 检查队友的技能，如果是大招，则触发反哺喧响值逻辑
            # TODO: 检查自己的技能，修改威风数值

            # TODO：发现一个潜在的问题，就是虎威的管理器是在这个阶段进行运行并且向Preload抛出攻击动作的，
            #  但是这意味着虎威抛出的动作在下一个tick才会被Preload受理，这好像有点奇怪？？？
            #  那我在计算CD时必须考虑这个时间差，使其符合测试值，所以虎威必须提前1tick运行。
            #  另外，就算是提前1tick，貌似依旧无法处理第0tick的情况。第0tick如果触发了虎威的自动攻击，
            #  那就只能去第1tick执行了（不过貌似进战斗的时候虎威不会A一下，但是这个还需要测试）
            pass

    def update_might(self, might_change: int, update_from: SkillNode | str):
        """更改威风点数的函数"""
        self.might += might_change
        if self.might < 0:
            print(f"【{update_from.skill_tag if isinstance(update_from, SkillNode) else update_from}】企图消耗{might_change}点威风！{self.NAME}的威风值不足！请检查APL！") if JUFUFU_REPORT else None
            self.might = 0
        if self.might > self.max_might:
            print(f"{self.NAME}的威风点数溢出{self.might - self.max_might}点") if JUFUFU_REPORT else None
            self.might = self.max_might

    def get_resources(self, *args, **kwargs) -> tuple[str | None, int | float | None]:
        return "威风", self.might

    def get_special_stats(self, *args, **kwargs) -> dict:
        pass

