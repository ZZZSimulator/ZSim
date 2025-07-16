from zsim.sim_progress.Preload import SkillNode
from zsim.models.event_enums import PostInitObjectType as PIOT, SpecialStateUpdateSignal as SSUS
from zsim.define import YUZUHA_REPORT
from ..character import Character
from ..utils.filters import _skill_node_filter
from typing import TYPE_CHECKING
from ...data_struct.SchedulePreload import schedule_preload_event_factory


if TYPE_CHECKING:
    from zsim.simulator.simulator_class import Simulator
    from zsim.sim_progress.data_struct.enemy_special_state_manager.special_classes import SweetScare


class Yuzuha(Character):
    def __init__(self, **kwargs):
        """柚叶的特殊资源"""
        super().__init__(**kwargs)
        self.sweet_scare: SweetScare | None = None
        self.sugar_points: int = 3      # 甜度点
        self.max_sugar_points: int = 6
        self.hard_candy_shot_tag = "1411_CoAttack_A"

    def special_resources(self, *args, **kwargs) -> None:
        skill_nodes: list[SkillNode] = _skill_node_filter(*args, **kwargs)
        for node in skill_nodes:
            sim_instance: "Simulator" = self.sim_instance
            sim_instance.schedule_data.enemy.special_state_manager.broadcast_and_update(signal=SSUS.CHARACTER, skill_node=node)
            if node.char_name != self.NAME:
                continue
            if node.skill.labels is not None and "sugar_points" in node.skill.labels:
                sugar_points = node.skill.labels["sugar_points"]
                self.update_sugar_points(value=sugar_points)
                if YUZUHA_REPORT:
                    self.sim_instance.schedule_data.change_process_state()
                    print(f"{self.NAME}释放了技能{node.skill_tag}，{"获得" if sugar_points > 0 else "消耗"}了{abs(sugar_points)}甜度点！当前甜度点为{self.sugar_points}")
            if node.skill.trigger_buff_level == 6:
                from zsim.sim_progress.data_struct.sp_update_data import ScheduleRefreshData
                report_namelist = []
                for char_obj in sim_instance.char_data.char_obj_list:
                    if char_obj.NAME == self.NAME:
                        continue
                    report_namelist.append(char_obj.NAME)
                    schedule_refresh_event = ScheduleRefreshData(
                        sp_target=(char_obj.NAME, ),
                        sp_value=25,
                    )
                    event_list = sim_instance.schedule_data.event_list
                    event_list.append(schedule_refresh_event)
                else:
                    if YUZUHA_REPORT:
                        sim_instance.schedule_data.change_process_state()
                        print(f"【柚叶回能】：柚叶发动大招，为{[_name for _name in report_namelist]}恢复25点能量值")

    def POST_INIT_DATA(self, sim_insatnce: "Simulator"):
        """柚叶的后置初始化函数，用于后置创建甜蜜惊吓特殊状态"""
        enemy = sim_insatnce.schedule_data.enemy
        self.sweet_scare = enemy.special_state_manager.special_state_factory(state_type=PIOT.SweetScare)

    def update_sugar_points(self, value: int):
        """更新甜度点"""
        if value < 0 and abs(self.sugar_points) < abs(value):
            if YUZUHA_REPORT:
                sim_instance: "Simulator" = self.sim_instance
                sim_instance.schedule_data.change_process_state()
                print(f"【甜度点警告】：甜度点不足！当前甜度点为{self.sugar_points}， 甜度点消耗值为：{abs(value)}")
            self.sugar_points = 0
            return
        self.sugar_points += value
        if self.sugar_points > self.max_sugar_points:
            self.sugar_points = self.max_sugar_points

    def spawn_hard_candy_shot(self, update_signal: "SkillNode" = None):
        """生成一次硬糖射击"""
        # self.update_sugar_points(value=-1)
        skill_tag_list = [self.hard_candy_shot_tag]
        preload_tick_list = [self.sim_instance.tick]
        schedule_preload_event_factory(
            skill_tag_list=skill_tag_list,
            preload_tick_list=preload_tick_list,
            preload_data=self.sim_instance.preload.preload_data,
            apl_priority_list=[-1],
            sim_instance=self.sim_instance
        )
        if YUZUHA_REPORT:
            self.sim_instance.schedule_data.change_process_state()
            print(f"【硬糖射击】{update_signal.skill_tag if update_signal is not None else None}触发了一次硬糖射击！")

    def get_resources(self, *args, **kwargs) -> tuple[str | None, int | float | None]:
        return "甜度点", self.sugar_points

    def get_special_stats(self, *args, **kwargs) -> dict[str | None, object | None]:
        pass
