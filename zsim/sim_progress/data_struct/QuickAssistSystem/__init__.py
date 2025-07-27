from __future__ import annotations

from typing import TYPE_CHECKING

from zsim.sim_progress.Buff import JudgeTools

from .quick_assist_manager import QuickAssistManager

if TYPE_CHECKING:
    from zsim.sim_progress.Character.character import Character
    from zsim.sim_progress.Preload import SkillNode
    from zsim.simulator.simulator_class import Simulator


class QuickAssistSystem:
    """管理整个小队的系统，需要延迟创建。"""

    def __init__(self, char_obj_list: list, sim_instance: Simulator):
        self.sim_instance = sim_instance
        self.char_obj_list: list["Character"] = char_obj_list
        self.quick_assist_manager_group: dict[str, QuickAssistManager] = {}
        for char_obj in self.char_obj_list:
            self.quick_assist_manager_group[char_obj.NAME] = char_obj.dynamic.quick_assist_manager

    def update(self, tick: int, skill_node: "SkillNode", all_name_order_box: dict[str, list[str]]):
        """外部接口，通过传入的skill_node来判断如何激活快速支援。"""
        current_name_order_dict = all_name_order_box[skill_node.char_name]
        if skill_node.skill.aid_direction == 0:
            """skill_node不影响快速支援状态"""
            pass
        elif skill_node.skill.aid_direction == 1:
            """skill_node会触发下一位角色的快速支援"""
            active_char = current_name_order_dict[1]
            active_manager = self.quick_assist_manager_group[active_char]
            self.spawn_event_group(tick, skill_node, active_manager)
        elif skill_node.skill.aid_direction == 2:
            """skill_node会触发上一位角色的快速支援"""
            active_char = current_name_order_dict[2]
            active_manager = self.quick_assist_manager_group[active_char]
            self.spawn_event_group(tick, skill_node, active_manager)
        else:
            raise ValueError(f"无法解析的快速支援方向参数！{skill_node.skill.aid_direction}")

        if skill_node.skill.trigger_buff_level == 7:
            if not self.quick_assist_manager_group[skill_node.char_name].quick_assist_available:
                if skill_node.char_name != "莱特":
                    """这里需要放行莱特，因为莱特会自己触发快速支援。"""
                    raise ValueError(
                        f"在{skill_node.char_name}的快速支援没有亮起的情况下，打出了快速支援！"
                    )
            self.answer_assist(tick, skill_node)

    def answer_assist(self, tick: int, skill_node: "SkillNode"):
        """该函数用于在检测到角色响应了快速支援时，向Eventlist提前抛出结束事件。"""
        char_name = skill_node.char_name
        manager = self.quick_assist_manager_group[char_name]
        end_event = QuickAssistEvent(
            update_tick=tick,
            updated_by=skill_node,
            operation=False,
            manager=manager,
            answer=True,
        )
        event_list = JudgeTools.find_event_list(sim_instance=self.sim_instance)
        event_list.append(end_event)
        # print(f'{skill_node.char_name}响应了快速支援！')

    def spawn_event_group(
        self, tick_now: int, skill_node: "SkillNode", active_manager: QuickAssistManager
    ):
        """创建一个事件对，包含开始事件和结束事件，并将他们添加到event_list里面去。"""
        start_event = QuickAssistEvent(
            update_tick=tick_now,
            updated_by=skill_node,
            operation=True,
            manager=active_manager,
        )
        end_event = QuickAssistEvent(
            update_tick=tick_now,
            updated_by=skill_node,
            operation=False,
            manager=active_manager,
        )
        start_event.manager.assist_event_update_tick = tick_now
        start_event.manager.last_update_node = skill_node
        end_event.manager.assist_event_update_tick = tick_now
        event_list = JudgeTools.find_event_list(sim_instance=self.sim_instance)
        event_list.append(start_event)
        event_list.append(end_event)

    def force_active_quick_assist(self, tick_now: int, skill_node: "SkillNode", char_name: str):
        """强制激活快速支援，主要是服务于外部调用。"""
        self.spawn_event_group(tick_now, skill_node, self.quick_assist_manager_group[char_name])


class QuickAssistEvent:
    """快速支援事件"""

    def __init__(
        self,
        update_tick: int,
        updated_by: "SkillNode",
        operation: bool,
        manager: QuickAssistManager,
        answer: bool = False,
    ):
        self.operation = operation
        self.updated_by = updated_by
        self.manager = manager
        self.exit_mode = answer
        if self.operation:
            self.execute_tick = update_tick + self.updated_by.skill.aid_lag_ticks
        else:
            if self.exit_mode:
                self.execute_tick = update_tick
            else:
                self.execute_tick = (
                    update_tick + self.updated_by.skill.aid_lag_ticks + self.manager.max_duration
                )

    def execute_update(self, tick_now: int, answer: bool = False):
        """事件的自执行方法"""
        if tick_now != self.execute_tick and self.operation:
            raise ValueError(
                f"{self.manager.char.NAME}的本次快速支援的激活更新理应在{self.execute_tick}tick执行，但实际执行于{tick_now}tick"
            )
        if self.operation:
            self.manager.state_change(tick_now, operation="turn_on")
        else:
            self.manager.state_change(tick_now, operation="turn_off", answer=self.exit_mode)
