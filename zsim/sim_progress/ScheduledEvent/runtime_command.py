from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from zsim.sim_progress.Update.UpdateAnomaly import (
    create_anomaly_runtime_context,
)
from zsim.sim_progress.Update.UpdateAnomaly import update_anomaly as _run_update_anomaly


def run_update_anomaly(**kwargs) -> None:
    _run_update_anomaly(**kwargs)


if TYPE_CHECKING:
    from zsim.sim_progress.anomaly_bar import AnomalyBar
    from zsim.sim_progress.data_struct import ActionStack
    from zsim.sim_progress.Enemy import Enemy
    from zsim.sim_progress.Load import LoadingMission
    from zsim.sim_progress.Preload import SkillNode
    from zsim.sim_progress.ScheduledEvent.buff_runtime import (
        BuffRuntimeFacade,
        BuffRuntimeReadPort,
        BuffRuntimeState,
    )
    from zsim.simulator.dataclasses import ScheduleData
    from zsim.simulator.simulator_class import Simulator


class RuntimeCommandPort(ABC):
    """同 tick runtime 写侧边界。"""

    @abstractmethod
    def update_anomaly(
        self,
        *,
        element_type: int,
        enemy: "Enemy",
        tick: int,
        skill_node: "SkillNode",
    ) -> None:
        """执行属性异常更新命令。"""

    @abstractmethod
    def settle_buffs(
        self,
        *,
        tick: int,
        enemy: "Enemy",
        skill_node: "SkillNode | LoadingMission | None" = None,
        anomaly_bar: "AnomalyBar | None" = None,
    ) -> None:
        """执行 Schedule 阶段 Buff 结算命令。"""


class _RuntimeCommandAdapterBase(RuntimeCommandPort):
    def __init__(
        self,
        *,
        data: "ScheduleData",
        action_stack: "ActionStack",
        sim_instance: "Simulator",
        buff_runtime_state: "BuffRuntimeState",
        buff_runtime_view: "BuffRuntimeReadPort | None" = None,
    ) -> None:
        self._data = data
        self._buff_runtime_state = buff_runtime_state
        self._action_stack = action_stack
        self._sim_instance = sim_instance
        self._buff_runtime_view = buff_runtime_view

    def update_anomaly(
        self,
        *,
        element_type: int,
        enemy: "Enemy",
        tick: int,
        skill_node: "SkillNode",
    ) -> None:
        run_update_anomaly(
            element_type=element_type,
            enemy=enemy,
            time_now=tick,
            char_obj_list=self._data.char_obj_list,
            sim_instance=self._sim_instance,
            skill_node=skill_node,
            dynamic_buff_dict=None,
            runtime_context=create_anomaly_runtime_context(
                sim_instance=self._sim_instance,
                enemy=enemy,
                buff_runtime_view=self._buff_runtime_view,
                schedule_data=self._data,
            ),
        )

    def settle_buffs(
        self,
        *,
        tick: int,
        enemy: "Enemy",
        skill_node: "SkillNode | LoadingMission | None" = None,
        anomaly_bar: "AnomalyBar | None" = None,
    ) -> None:
        self._buff_runtime_facade_for_settle(enemy).settle_schedule_buffs(
            tick=tick,
            enemy=enemy,
            sim_instance=self._sim_instance,
            skill_node=skill_node,
            anomaly_bar=anomaly_bar,
        )

    def _buff_runtime_facade_for_settle(self, enemy: "Enemy") -> "BuffRuntimeFacade":
        return self._runtime_state_for_settle(enemy).create_facade()

    def _runtime_state_for_settle(self, enemy: "Enemy") -> "BuffRuntimeState":
        return self._buff_runtime_state

    @staticmethod
    def _enemy_debuff_mirror_for_settle(enemy: "Enemy") -> list:
        enemy_dynamic = getattr(enemy, "dynamic", None)
        enemy_mirror = getattr(enemy_dynamic, "dynamic_debuff_list", None)
        if enemy_mirror is None:
            return []
        return enemy_mirror


class DefaultRuntimeCommandAdapter(_RuntimeCommandAdapterBase):
    """基于本轮模拟 Buff runtime state 的生产路径命令适配器。"""

    def __init__(
        self,
        *,
        data: "ScheduleData",
        action_stack: "ActionStack",
        sim_instance: "Simulator",
        buff_runtime_state: "BuffRuntimeState",
        buff_runtime_view: "BuffRuntimeReadPort | None" = None,
    ) -> None:
        super().__init__(
            data=data,
            action_stack=action_stack,
            sim_instance=sim_instance,
            buff_runtime_state=buff_runtime_state,
            buff_runtime_view=buff_runtime_view,
        )


def create_runtime_command_port(
    *,
    data: "ScheduleData",
    action_stack: "ActionStack",
    sim_instance: "Simulator",
    buff_runtime_state: "BuffRuntimeState",
    buff_runtime_view: "BuffRuntimeReadPort | None" = None,
) -> RuntimeCommandPort:
    """创建同 tick runtime 写侧命令入口。"""
    return DefaultRuntimeCommandAdapter(
        data=data,
        action_stack=action_stack,
        sim_instance=sim_instance,
        buff_runtime_state=buff_runtime_state,
        buff_runtime_view=buff_runtime_view,
    )


__all__ = [
    "RuntimeCommandPort",
    "DefaultRuntimeCommandAdapter",
    "create_runtime_command_port",
]
