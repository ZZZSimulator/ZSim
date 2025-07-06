from dataclasses import dataclass
from typing import TYPE_CHECKING

from zsim.sim_progress.anomaly_bar import AnomalyBar

if TYPE_CHECKING:
    from zsim.simulator.simulator_class import Simulator


class Dot:
    def __init__(
        self,
        bar: AnomalyBar = None,
        skill_tag: str | None = None,
        sim_instance: "Simulator" = None,
    ):
        self.sim_instance = sim_instance
        self.ft = self.DotFeature(sim_instance=self.sim_instance)
        self.dy = self.DotDynamic()
        self.history = self.DotHistory()
        # 默认情况下不创建anomlay_data。
        self.anomaly_data = None
        self.skill_node_data = None
        if bar is not None and skill_tag is not None:
            raise ValueError("Dot的构造函数不可以同时传入bar和skill_tag")
        if bar:
            self.anomaly_data = bar
        if skill_tag:
            from zsim.sim_progress.Buff import JudgeTools
            from zsim.sim_progress.Preload.SkillsQueue import spawn_node

            preload_data = JudgeTools.find_preload_data(sim_instance=self.sim_instance)
            tick = JudgeTools.find_tick(sim_instance=self.sim_instance)
            self.skill_node_data = spawn_node(skill_tag, tick, preload_data.skills)

    @dataclass
    class DotFeature:
        """
        这里记录了Dot的固定属性。
        effect_rules属性记录了dot的更新规则。
        更新指的是：更新自身时间、层数、内置CD等属性，同时也有可能是造成伤害。
        0：无更新——只有效果，没有更新机制。
        1：根据时间更新——完全依赖内置CD
        2：命中时更新——依赖内置CD，同时需要外部进行“hit”判断，外部函数或许需要联动LoadingMission和TimeTick
        3：缓存式更新——依赖内置CD，以及Dot.Dynamic中的动态记录模块，来记录伤害积累。
        4：碎冰——只有含有重攻击的技能在end标签处才能触发。
        """

        sim_instance: "Simulator"
        update_cd: int | float = 0
        index: str = None
        name: str = None
        dot_from: str = None
        effect_rules: int = None
        max_count: int = None
        max_duration: int = None
        incremental_step: int = None
        max_effect_times: int = 30
        count_as_skill_hit: bool = False  # dot生效时的伤害能否视作技能的一次命中（从而参与其他的命中类dot的触发）
        complex_exit_logic = False  # 复杂的结束判定

        def __str__(self):
            return str(self.__dict__)

    @dataclass
    class DotDynamic:
        start_ticks: int = 0
        end_ticks: int = 0
        last_effect_ticks: int = 0
        active: bool = None
        count: int = 0
        ready: bool = None
        effect_times: int = 0

    @dataclass
    class DotHistory:
        start_times: int = 0
        end_times: int = 0
        last_start_ticks: int = 0
        last_end_ticks: int = 0
        last_duration: int = 0

    def ready_judge(self, timenow):
        if not self.dy.ready:
            if timenow - self.dy.last_effect_ticks >= self.ft.update_cd:
                self.dy.ready = True

    def end(self, timenow):
        self.dy.active = False
        self.dy.count = 0
        self.history.last_end_ticks = timenow
        self.history.last_duration = timenow - self.dy.start_ticks
        self.history.end_times += 1

    def start(self, timenow):
        self.dy.active = True
        self.dy.start_ticks = timenow
        self.dy.last_effect_ticks = timenow
        if self.ft.max_duration is None:
            raise ValueError(f"{self.ft.index}的最大持续时间为None，请检查初始化！")
        self.dy.end_ticks = self.dy.start_ticks + self.ft.max_duration
        self.history.start_times += 1
        self.history.last_start_ticks = timenow
        self.dy.count = 1
        self.dy.effect_times = 1
        self.dy.ready = False

    def exit_judge(self, **kwargs):
        pass
