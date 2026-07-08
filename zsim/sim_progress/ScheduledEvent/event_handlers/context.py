"""
事件处理上下文模型

该模块定义了事件处理上下文的 dataclass，用于替代字典形式的上下文数据。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Mapping, Sequence

from zsim.sim_progress.data_struct.schedule_dispatch import create_schedule_dispatch_port

from ..buff_runtime import BuffRuntimeReadPort
from ..runtime_command import RuntimeCommandPort

if TYPE_CHECKING:
    from zsim.sim_progress.Buff import Buff
    from zsim.sim_progress.data_struct import ActionStack
    from zsim.sim_progress.Enemy import Enemy
    from zsim.sim_progress.Preload.SkillsQueue import SkillNode
    from zsim.simulator.dataclasses import ScheduleData
    from zsim.simulator.simulator_class import Simulator


@dataclass
class EventContext:
    """
    事件处理上下文模型

    包含事件处理所需的全部数据和对象，使用 dataclass 提供类型安全和简洁语法。
    """

    data: ScheduleData
    tick: int
    enemy: Enemy
    buff_runtime_view: BuffRuntimeReadPort
    runtime_command_port: RuntimeCommandPort
    action_stack: ActionStack[SkillNode]
    sim_instance: Simulator

    def get_data(self) -> ScheduleData:
        """获取调度数据对象"""
        return self.data

    def requeue_event(self, event: Any) -> None:
        """将未到执行时间的事件重新加入当前 Schedule 队列。"""
        create_schedule_dispatch_port(schedule_data=self.data).publish_scheduled(event)

    def get_tick(self) -> int:
        """获取当前时间刻"""
        return self.tick

    def get_enemy(self) -> Enemy:
        """获取敌人对象"""
        return self.enemy

    def get_buff_runtime_view(self) -> BuffRuntimeReadPort:
        """获取 Buff runtime 只读视图"""
        return self.buff_runtime_view

    def get_runtime_command_port(self) -> RuntimeCommandPort:
        """获取 Buff runtime 写命令入口"""
        return self.runtime_command_port

    def get_runtime_active_buffs(self, beneficiary: str) -> Sequence["Buff"]:
        """获取指定受益者的 runtime active Buff 只读列表"""
        return self.buff_runtime_view.get_active_buffs(beneficiary)

    def get_active_buffs(self, beneficiary: str) -> Sequence["Buff"]:
        """获取指定受益者的 active Buff 只读列表"""
        return self.get_runtime_active_buffs(beneficiary)

    def get_runtime_active_buff_view(self) -> Mapping[str, Sequence["Buff"]]:
        """获取所有受益者的 runtime active Buff 只读视图"""
        return self.buff_runtime_view.get_active_buff_view()

    def get_active_buff_view(self) -> Mapping[str, Sequence["Buff"]]:
        """获取所有受益者的 active Buff 只读视图"""
        return self.get_runtime_active_buff_view()

    def get_runtime_exist_buff_snapshot(self, beneficiary: str) -> Mapping[str, "Buff"]:
        """获取指定受益者的 runtime snapshot Buff 只读视图"""
        return self.buff_runtime_view.get_exist_buff_snapshot(beneficiary)

    def get_exist_buff_snapshot(self, beneficiary: str) -> Mapping[str, "Buff"]:
        """获取指定受益者的 snapshot Buff 只读视图"""
        return self.get_runtime_exist_buff_snapshot(beneficiary)

    def get_runtime_exist_buff_snapshot_view(self) -> Mapping[str, Mapping[str, "Buff"]]:
        """获取所有受益者的 runtime snapshot Buff 只读视图"""
        return self.buff_runtime_view.get_exist_buff_snapshot_view()

    def get_exist_buff_snapshot_view(self) -> Mapping[str, Mapping[str, "Buff"]]:
        """获取所有受益者的 snapshot Buff 只读视图"""
        return self.get_runtime_exist_buff_snapshot_view()

    def get_action_stack(self) -> ActionStack[SkillNode]:
        """获取动作栈"""
        return self.action_stack

    def get_sim_instance(self) -> Simulator:
        """获取模拟器实例"""
        return self.sim_instance
