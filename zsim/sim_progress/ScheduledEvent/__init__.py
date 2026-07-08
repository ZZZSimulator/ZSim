from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from zsim.sim_progress import Buff
from zsim.sim_progress.Character import Character
from zsim.sim_progress.data_struct import (
    ActionStack,
    PolarizedAssaultEvent,
    QuickAssistEvent,
    SchedulePreload,
    SPUpdateData,
)
from zsim.sim_progress.data_struct.planned_queue import (
    PlannedEventQueue,
    ensure_planned_event_queue,
)
from zsim.sim_progress.Load.loading_mission import LoadingMission
from zsim.sim_progress.Preload import SkillNode

from .buff_runtime import BuffRuntimeState, create_buff_runtime_read_port
from .event_handlers import EventContext, create_default_event_handler_factory
from .event_handlers.handlers.factory import EventHandlerFactory
from .runtime_command import create_runtime_command_port

if TYPE_CHECKING:
    from zsim.simulator.dataclasses import ScheduleData
    from zsim.simulator.simulator_class import Simulator

    from .buff_runtime import BuffRuntimeReadPort
    from .runtime_command import RuntimeCommandPort


class ScConditionData:
    """
    用于记录在本tick可能的判断 buff 数据，以方便后续计算伤害
    """

    def __init__(self):
        self.buff_list: list = []
        self.when_crit: bool = False


@dataclass(frozen=True, slots=True)
class _ScheduledEventRuntimePorts:
    """ScheduledEvent 内部 runtime 读写端口组。"""

    buff_runtime_view: "BuffRuntimeReadPort"
    runtime_command_port: "RuntimeCommandPort"


class ScheduledEventRuntimePortFactory:
    """根据当前 tick 的输入创建 ScheduledEvent runtime 读写端口。"""

    def create(
        self,
        *,
        data: "ScheduleData",
        action_stack: ActionStack,
        buff_runtime_state: BuffRuntimeState,
        buff_runtime_view: "BuffRuntimeReadPort",
        sim_instance: "Simulator",
    ) -> _ScheduledEventRuntimePorts:
        return _ScheduledEventRuntimePorts(
            buff_runtime_view=buff_runtime_view,
            runtime_command_port=create_runtime_command_port(
                data=data,
                action_stack=action_stack,
                sim_instance=sim_instance,
                buff_runtime_state=buff_runtime_state,
                buff_runtime_view=buff_runtime_view,
            ),
        )


_SCHEDULED_EVENT_RUNTIME_PORT_FACTORY = ScheduledEventRuntimePortFactory()


class ScheduledEvent:
    """
    计划事件方法类

    主逻辑链 self.event_start()：
    1、读取计划事件列表，将其中所有的buff示例排到列表最靠前的位置。self.sort_events()
    2、遍历事件列表，从开始到结束，将每一个事件派发到分支逻辑链内进行处理
    """

    @classmethod
    def from_runtime_state(
        cls,
        *,
        schedule_data: "ScheduleData",
        tick: int,
        action_stack: ActionStack,
        buff_runtime_state: BuffRuntimeState,
        sim_instance: "Simulator",
    ) -> "ScheduledEvent":
        """基于本轮模拟 Buff runtime 的生产路径构造入口。"""
        return cls(
            schedule_data,
            tick,
            action_stack,
            buff_runtime_state=buff_runtime_state,
            sim_instance=sim_instance,
        )

    def __init__(
        self,
        data,
        tick: int,
        action_stack: ActionStack,
        *,
        buff_runtime_state: BuffRuntimeState,
        sim_instance: Simulator,
    ):
        self.data: "ScheduleData" = data
        self.data.dynamic_buff = buff_runtime_state.active_store_owner().mutable_stores()
        self.data.processed_times = 0
        # self.judge_required_info_dict = data.judge_required_info_dict
        self.action_stack = action_stack

        if not isinstance(tick, int):
            raise ValueError(f"tick参数必须为整数，但你输入了{tick}")

        # 更新Data
        self.tick = tick
        self.data.loading_buff = buff_runtime_state.pending_queue_owner().mutable_queues()
        self.enemy = self.data.enemy
        self.buff_runtime_state = buff_runtime_state
        self.sim_instance: Simulator = sim_instance
        self._record_buff_runtime_rebuild_count("scheduled_event")
        runtime_ports = self._create_runtime_ports()
        self.buff_runtime_view = runtime_ports.buff_runtime_view
        self.runtime_command_port = runtime_ports.runtime_command_port

        self.execute_tick_key_map = {
            SkillNode: "preload_tick",
            QuickAssistEvent: "execute_tick",
            SchedulePreload: "execute_tick",
            PolarizedAssaultEvent: "execute_tick",
        }
        self._event_handler_factory = self._get_event_handler_factory()
        # 确保事件处理器已注册
        self._ensure_handlers_registered()

    def _get_event_handler_factory(self) -> EventHandlerFactory:
        factory = getattr(self.sim_instance, "_scheduled_event_handler_factory", None)
        if isinstance(factory, EventHandlerFactory):
            return factory
        factory = create_default_event_handler_factory()
        try:
            setattr(self.sim_instance, "_scheduled_event_handler_factory", factory)
        except Exception:
            pass
        return factory

    def _ensure_handlers_registered(self) -> None:
        """确保所有事件处理器已注册"""
        if not self._event_handler_factory.list_handlers():
            self._event_handler_factory = create_default_event_handler_factory()
            try:
                setattr(
                    self.sim_instance,
                    "_scheduled_event_handler_factory",
                    self._event_handler_factory,
                )
            except Exception:
                pass
            logging.info("事件处理器注册完成")
        else:
            logging.debug("事件处理器已经注册")

    def _record_buff_runtime_rebuild_count(self, counter_name: str) -> None:
        record_count = getattr(self.sim_instance, "_record_buff_runtime_rebuild_count", None)
        if callable(record_count):
            record_count(counter_name)

    def _create_runtime_ports(self) -> _ScheduledEventRuntimePorts:
        """集中创建 Schedule 事件处理所需的 runtime 读写端口。"""
        self._record_buff_runtime_rebuild_count("scheduled_event_runtime_ports")
        assert self.buff_runtime_state is not None
        buff_runtime_view = self.buff_runtime_state.create_read_port()
        return _SCHEDULED_EVENT_RUNTIME_PORT_FACTORY.create(
            data=self.data,
            action_stack=self.action_stack,
            buff_runtime_state=self.buff_runtime_state,
            buff_runtime_view=buff_runtime_view,
            sim_instance=self.sim_instance,
        )

    def _create_event_context(self) -> EventContext:
        """
        创建事件处理上下文

        Returns:
            EventContext: 包含事件处理所需数据的上下文对象
        """
        return EventContext(
            data=self.data,
            tick=self.tick,
            enemy=self.enemy,
            buff_runtime_view=self.buff_runtime_view,
            runtime_command_port=self.runtime_command_port,
            action_stack=self.action_stack,
            sim_instance=self.sim_instance,
        )

    @property
    def _planned_event_queue(self) -> PlannedEventQueue:
        return ensure_planned_event_queue(self.data)

    def event_start(self):
        """Schedule主逻辑"""
        # 更新角色面板
        for char in self.data.char_obj_list:
            char: Character
            sp_update_data = SPUpdateData(
                char_obj=char,
                runtime_view=self.buff_runtime_view,
                sim_instance=self.sim_instance,
            )
            char.update_sp_and_decibel(sp_update_data)
            if hasattr(char, "refresh_myself"):
                char.refresh_myself()
        self.process_event()

    def process_event(self):
        """
        处理当前所有事件

        使用事件处理器模式来处理各种类型的事件，替代原有的大型if-elif链。
        提高代码的可读性和可维护性。
        """
        if not self._planned_event_queue.has_events():
            return

        # 先处理优先级高的buff
        self.solve_buff()

        # 筛选出可处理的事件，并按照优先级排序
        planned_queue = self._planned_event_queue
        processable_events = self.select_processable_event(planned_queue)

        # 使用事件处理器处理事件
        for event in processable_events:
            try:
                self._process_single_event(event)
                # 事件处理完毕，从列表中移除
                planned_queue.remove(event)
                self.data.processed_times += 1
            except Exception as e:
                raise RuntimeError(f"处理事件 {type(event)} 时发生错误: {e}") from e

        # 如果计算过程中又有新的事件生成，则继续循环
        if self._planned_event_queue.has_events() and not self.check_all_event():
            self.process_event()

    def _process_single_event(self, event: Any) -> None:
        """
        处理单个事件

        Args:
            event: 待处理的事件对象

        Raises:
            NotImplementedError: 当事件类型不被支持时
            RuntimeError: 当事件处理器无法找到时
            Exception: 事件处理过程中的其他错误
        """
        # 特殊处理Buff事件
        if isinstance(event, Buff.Buff):
            raise NotImplementedError(f"{type(event)}，目前不应存在于 event_list")

        # 事件处理上下文
        context = self._create_event_context()

        # 获取事件处理器
        handler = self._event_handler_factory.get_handler(event)
        if handler is None:
            error_msg = f"无法找到适合处理事件类型 {type(event)} 的处理器"
            logging.error(error_msg)
            logging.debug(f"可用的事件处理器: {self._event_handler_factory.list_handlers()}")
            raise RuntimeError(error_msg)

        # 处理事件
        try:
            handler.handle(event, context)
        except Exception as e:
            logging.error(f"处理事件 {type(event).__name__} 时发生错误: {e}", exc_info=True)
            raise

    def check_all_event(self):
        """检查所有残留事件是否到期，只要有一个残留事件已经到期，直接返回False，激活递归。"""
        for event in self._planned_event_queue.snapshot():
            # 获取事件类型对应的tick属性名
            execute_tick = self.get_execute_tick(event)
            if execute_tick is None:
                return False
            if execute_tick > self.tick:  # 严格大于当前tick才视为未到期
                continue
            else:
                return False
        return True

    def get_execute_tick(self, event) -> int | None:
        """获取事件的执行tick，获取不到则返回None"""
        tick_attr = self.execute_tick_key_map.get(type(event), None)
        if tick_attr is None:
            """获取不到属性时，说明该event并不具备计划事件的需求，所以这种事件是必须在当前tick被清空的，直接返回None"""
            return None
        execute_tick = getattr(event, tick_attr, None)
        if execute_tick is None:
            raise AttributeError(f"{type(event)} 没有属性 {tick_attr}")
        return execute_tick

    def update_anomaly_bar_after_skill_event(self, event):
        """在Schedule阶段，处理完一个SkillEvent后，都要进行一次异常条更新。"""
        """
        将异常值更新移动到Schedule阶段的主要原因：原有的Buff更新、异常/紊乱结算的顺序不合理；
        原有顺序：
        Preload -> Load -> update_anomaly() -> Buff(第一轮) ->  Schedule -> Buff(第二轮)
        现有顺序：
        Preload -> Load -> Buff(第一轮) ->  Schedule -> update_anomaly() -> Buff(第二轮)

        由于update_anomaly()函数是根据现有积蓄值来判断是否触发属性异常的，
        所以在运行过程中，只有先把积蓄值打满的下一次update_anomaly()才会触发属性异常，
        无论是哪种结构，enemy的receive_hit()函数都会在Schedule阶段执行，
        故任何早于Schedule阶段的update_anomaly都只能更新到上个tick的属性异常，
        所以，原有结构中，第Ntick打满的异常条，会在第N+1 tick被激活，

        一般情况下，这种迟滞1tick的激活行为不会对模拟的结果造成影响，
        (长难句警告！！)--但若是某个Buff事件的激活 依赖于发生在 技能last_hit标签处的属性异常更新--
        那么在老的结构下，事件的更新顺序为
            --(第N Tick)--
                -> update_anomaly(此时的异常条还没打满[来自于上个tick]所以第Ntick的运行无结果)
                -> Buff事件触发器检测（异常条更新状态没有改变，所以触发器不触发）
                -> Schedule，异常条满，
            --(第N+1 Tick)--
                -> update_anomaly(异常条满，更新异常)
                -> Buff事件触发器检测（已经错过了触发窗口，所以触发器不触发）

        而在新的结构下，事件更新顺序为：
            --(第N Tick)--
                -> Schedule，异常条满，
                -> update_anomaly(异常条满，更新异常)
                -> Buff事件触发器检测（将该Buff改为Schedule处理类型）

        上述结构的改变就能够彻底规避来自于结构的触发误差——来自柳极性紊乱触发器的启发
        """
        if isinstance(event, SkillNode):
            _node = event
        elif isinstance(event, LoadingMission):
            _node = event.mission_node
        else:
            raise TypeError("无法解析的事件类型")
        """接下来要通过技能的异常更新特性，判断当前Tick的技能是否能够更新异常
        由于调用函数的位置是ScheduleEvent，所以一定是Hit事件发生时，
        所以，直接调用loading_mission.hitted_count数量就可以获得当前正在被结算的Hit次数。"""
        should_update = False
        if not _node.skill.anomaly_update_rule:
            if _node.loading_mission is None:
                _loading_mission = LoadingMission(_node)
                _loading_mission.mission_start(timenow=self.sim_instance.tick)
                _node.loading_mission = _loading_mission
            last_hit = _node.loading_mission.get_last_hit()
            if last_hit is not None and self.tick - 1 < last_hit <= self.tick:
                should_update = True
        else:
            if _node.skill.anomaly_update_rule == -1:
                should_update = True
            else:
                if (
                    _node.loading_mission is not None
                    and _node.skill.anomaly_update_rule is not None
                    and (
                        isinstance(_node.skill.anomaly_update_rule, list)
                        and _node.loading_mission.hitted_count in _node.skill.anomaly_update_rule
                        or isinstance(_node.skill.anomaly_update_rule, int)
                        and _node.loading_mission.hitted_count == _node.skill.anomaly_update_rule
                    )
                ):
                    should_update = True
        if should_update:
            self.runtime_command_port.update_anomaly(
                element_type=_node.element_type,
                enemy=self.enemy,
                tick=self.tick,
                skill_node=_node,
            )

    def solve_buff(self) -> None:
        """提前处理Buff实例"""
        # Buff.buff_add(
        #     self.tick, self.data.loading_buff, self.data.dynamic_buff, self.data.enemy
        # )
        buff_events = []
        other_events = []
        for event in self._planned_event_queue.snapshot():
            if isinstance(event, Buff.Buff):
                buff_events.append(event)
            else:
                other_events.append(event)
        self._planned_event_queue.replace(buff_events + other_events)

    def select_processable_event(self, planned_queue: PlannedEventQueue | None = None) -> list[Any]:
        """筛选当前可执行的事件，并且按照优先级排序，获取不到优先级的默认为0，"""
        _output_event_list: list[Any] = []
        if planned_queue is None:
            planned_queue = self._planned_event_queue
        for _event in planned_queue.snapshot():
            execute_tick = self.get_execute_tick(_event)
            if execute_tick is None or execute_tick <= self.tick:
                """说明事件不存在execute_tick或已到期，需要被立刻执行。"""
                schedule_priority = getattr(_event, "schedule_priority", 0)
                # 使用bisect模块进行高效插入
                import bisect

                priorities = [getattr(e, "schedule_priority", 0) for e in _output_event_list]
                insert_pos = bisect.bisect_right(priorities, schedule_priority)
                _output_event_list.insert(insert_pos, _event)
        return _output_event_list


if __name__ == "__main__":
    pass
