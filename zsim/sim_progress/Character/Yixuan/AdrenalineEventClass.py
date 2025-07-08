from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from zsim.define import YIXUAN_REPORT

if TYPE_CHECKING:
    from zsim.sim_progress.Character.Yixuan import Yixuan
    from zsim.sim_progress.Preload import SkillNode
    from zsim.simulator.simulator_class import Simulator


class BaseAdrenalineEvent(ABC):
    """管理单个闪能事件的基类"""

    @abstractmethod
    def __init__(self, char_instance: "Yixuan", comment: str = None):
        self.char = char_instance
        self.comment = comment
        self.active: bool = False
        self.max_duration: int = 0
        self.last_active_tick: int = 0
        self.regenerate_value_sum: float = 0
        self.index = ""
        self.active_times: int = 0

    @abstractmethod
    def update_status(self, skill_node: "SkillNode"):
        """更新自身状态，但不包含生效逻辑——char接收Preload的skill_node时调用"""
        pass

    def check_myself(self):
        """
        在Buff阶段调用，检查自身是否处于激活状态，若自身激活，则调用effect_apply
        """
        simulator: "Simulator" = self.char.sim_instance
        if self.active:
            self.apply_effect()
            if simulator.tick >= self.last_active_tick + self.max_duration:
                self.active = False
                if YIXUAN_REPORT:
                    print(
                        f"第{self.active_times}次【{self.index}】结束了！总计为仪玄恢复了{self.regenerate_value_sum: .2f}点闪能！"
                    )
                    self.char.sim_instance.schedule_data.change_process_state()
                self.regenerate_value_sum = 0

    @abstractmethod
    def apply_effect(self):
        """事件生效一次的方法"""
        pass


class AuricArray(BaseAdrenalineEvent):
    """来自仪玄玄墨极阵释放过程中的回能效果的管理器对象"""

    def __init__(self, char_instance: "Yixuan", comment: str = None):
        super().__init__(char_instance, comment)
        self.index = "玄墨极阵回能效果"
        self.comment = "来自玄墨极阵的回能Buff，【普通攻击：玄墨极阵】期间会持续回复闪能，每秒7点，持续3秒"
        self.active = False
        self.max_duration: int = 180
        self.last_active_tick: int = 0
        self.regenerate_value = 7 / 60
        self.active_times: int = 0
        self.regenerate_value_sum = 0

    def update_status(self, skill_node: "SkillNode"):
        """当检测到玄墨极阵的skill_node时，更新自身状态，"""
        simulator: "Simulator" = self.char.sim_instance
        if skill_node:
            if skill_node.char_name != self.char.NAME:
                return
            if skill_node.skill_tag == "1371_SNA_B_1":
                if self.active:
                    raise ValueError(
                        f"仪玄在展开玄墨极阵时，检测到上一个开始于{self.last_active_tick}tick的玄墨极阵的回能Buff尚未结束，仪玄不可能在短时间内打出两次玄墨极阵，请检查逻辑！"
                    )
                self.active = True
                self.active_times += 1
                self.last_active_tick = simulator.tick
                """激活的当前tick也需要恢复闪能，但是并不是在本方法内部执行的，而是通过Buff触发器统一在Load阶段执行。"""
                if YIXUAN_REPORT:
                    print(
                        f"检测到技能{skill_node.skill_tag}（玄墨极阵）！【{self.index}】激活"
                    )
                    self.char.sim_instance.schedule_data.change_process_state()

    def apply_effect(self):
        """事件生效，恢复一次闪能值"""
        self.char.update_adrenaline(self.regenerate_value)
        self.regenerate_value_sum += self.regenerate_value


class AuricInkUndercurrent(BaseAdrenalineEvent):
    """仪玄组队被动中，队友释放大招时的回能事件的管理器对象"""

    def __init__(self, char_instance: "Yixuan", comment: str = None):
        super().__init__(char_instance, comment)
        self.index = "组队被动回能效果"
        self.comment = "来自组队被动的回能Buff，队友释放大招后，仪玄会持续每秒恢复2点闪能，持续10秒"
        self.active = False
        self.max_duration: int = 600
        self.last_active_tick: int = 0
        self.regenerate_value_per_tick = 2 / 60
        self.active_times: int = 0
        self.regenerate_value_sum = 0

    def update_status(self, skill_node: "SkillNode"):
        """当检测到队友大招时，更新自身状态，"""
        simulator: "Simulator" = self.char.sim_instance
        if skill_node:
            # 过滤自己的技能
            if skill_node.char_name == self.char.NAME:
                return
            if skill_node.skill.trigger_buff_level == 6:
                self.active = True
                self.active_times += 1
                self.last_active_tick = simulator.tick
                if YIXUAN_REPORT:
                    print(
                        f"检测到队友释放大招：{skill_node.skill_tag}！【{self.index}】激活"
                    )
                    self.char.sim_instance.schedule_data.change_process_state()

    def apply_effect(self):
        """事件生效，恢复一次闪能值"""
        self.char.update_adrenaline(self.regenerate_value_per_tick)
        self.regenerate_value_sum += self.regenerate_value_per_tick
