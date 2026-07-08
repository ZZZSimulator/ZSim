"""技能事件处理器"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Mapping, Sequence

from zsim.sim_progress import Report
from zsim.sim_progress.calculation.calculator import Calculator
from zsim.sim_progress.Character import Character
from zsim.sim_progress.data_struct import SingleHit
from zsim.sim_progress.data_struct.schedule_dispatch import create_schedule_dispatch_port
from zsim.sim_progress.Load.LoadDamageEvent import (
    ProcessFreezLikeDots,
    ProcessHitUpdateDots,
)
from zsim.sim_progress.Load.loading_mission import LoadingMission
from zsim.sim_progress.Preload import SkillNode

from ..base import BaseEventHandler
from ..context import EventContext

if TYPE_CHECKING:
    from zsim.sim_progress.Buff import Buff
    from zsim.sim_progress.Enemy import Enemy
    from zsim.simulator.dataclasses import ScheduleData
    from zsim.simulator.simulator_class import Simulator

    from ...runtime_command import RuntimeCommandPort


class SkillEventHandler(BaseEventHandler):
    """技能事件处理器"""

    def __init__(self):
        super().__init__("skill")

    def can_handle(self, event: Any) -> bool:
        return isinstance(event, SkillNode | LoadingMission)

    def handle(self, event: SkillNode | LoadingMission, context: EventContext) -> None:
        """处理技能事件"""
        self._validate_event(event, (SkillNode, LoadingMission))
        self._validate_context(context)

        data = self._get_context_data(context)
        tick = self._get_context_tick(context)
        enemy = self._get_context_enemy(context)
        runtime_active_buff_view = self._get_context_runtime_active_buff_view(context)
        runtime_command_port = self._get_context_runtime_command_port(context)
        sim_instance = self._get_context_sim_instance(context)

        execute_tick = self._get_execute_tick(event, context)
        if execute_tick is None or execute_tick > tick:
            return

        self._process_skill_event(
            event=event,
            data=data,
            tick=tick,
            enemy=enemy,
            runtime_active_buff_view=runtime_active_buff_view,
            runtime_command_port=runtime_command_port,
            sim_instance=sim_instance,
        )

    def _get_execute_tick(
        self, event: SkillNode | LoadingMission, context: EventContext
    ) -> int | None:
        """获取事件的执行 tick"""
        if isinstance(event, SkillNode):
            return event.preload_tick
        if isinstance(event, LoadingMission):
            return event.mission_node.preload_tick
        return None

    def _process_skill_event(
        self,
        event: SkillNode | LoadingMission,
        data: ScheduleData,
        tick: int,
        enemy: Enemy,
        runtime_active_buff_view: Mapping[str, Sequence["Buff"]],
        runtime_command_port: "RuntimeCommandPort",
        sim_instance: Simulator,
    ) -> None:
        """处理技能事件的主体流程"""
        skill_node, hit_count = self._extract_skill_info(event)
        char_obj = self._find_character(skill_node.skill.char_name, data.char_obj_list)

        self._calculate_damage(
            skill_node,
            char_obj,
            enemy,
            runtime_active_buff_view,
            hit_count,
            event,
            tick,
        )
        self._update_anomaly_bar_after_skill_event(
            skill_node,
            enemy,
            tick,
            runtime_command_port,
            sim_instance,
        )
        self._settle_buffs(
            tick,
            enemy,
            skill_node,
            runtime_command_port,
        )
        self._update_damage_effects(tick, enemy, data, event)
        self._broadcast_skill_event_to_char(event=event, sim_instance=sim_instance)

    def _broadcast_skill_event_to_char(
        self, event: SkillNode | LoadingMission, sim_instance: Simulator
    ) -> None:
        """广播技能事件到所有角色以触发特殊资源更新"""
        event_to_broadcast = event if isinstance(event, SkillNode) else event.mission_node
        for char_obj in sim_instance.char_data.char_obj_list:
            if hasattr(char_obj, "update_special_resource"):
                char_obj.update_special_resource(event_to_broadcast)

    def _extract_skill_info(self, event: SkillNode | LoadingMission) -> tuple[SkillNode, int]:
        """提取技能节点和命中次数"""
        if isinstance(event, LoadingMission):
            return event.mission_node, event.hitted_count
        return event, 0

    def _find_character(self, char_name: str, char_obj_list: list[Character]) -> Character:
        """查找角色对象"""
        for character in char_obj_list:
            if character.NAME == char_name:
                return character
        raise ValueError(f"角色 {char_name} 未找到")

    def _calculate_damage(
        self,
        skill_node: SkillNode,
        char_obj: Character,
        enemy: Enemy,
        dynamic_buff: Mapping[str, Sequence["Buff"]],
        hit_count: int,
        event: SkillNode | LoadingMission,
        tick: int,
    ) -> None:
        """计算伤害"""
        calculator = Calculator(
            skill_node=skill_node,
            character_obj=char_obj,
            enemy_obj=enemy,
            dynamic_buff=dynamic_buff,
        )

        snapshot = calculator.cal_snapshot()
        stun = calculator.cal_stun()
        damage_expect = calculator.cal_dmg_expect()
        damage_crit = calculator.cal_dmg_crit()

        if isinstance(event, SkillNode):
            proactive = event.active_generation
        else:
            proactive = event.mission_node.active_generation

        hit_result = SingleHit(
            skill_tag=skill_node.skill_tag,
            snapshot=snapshot,
            stun=stun,
            dmg_expect=damage_expect,
            dmg_crit=damage_crit,
            hitted_count=hit_count,
            proactive=proactive,
        )
        hit_result.skill_node = skill_node

        if skill_node.skill.follow_by:
            hit_result.proactive = False

        if skill_node.hit_times == hit_count and skill_node.skill.heavy_attack:
            hit_result.heavy_hit = True

        enemy.hit_received(hit_result, tick)

        Report.report_dmg_result(
            tick=tick,
            element_type=skill_node.element_type,
            skill_tag=skill_node.skill_tag,
            dmg_expect=round(damage_expect, 2),
            dmg_crit=round(damage_crit, 2),
            stun=round(stun, 2),
            buildup=round(snapshot[1], 2),
            **enemy.dynamic.get_status(),
            UUID=skill_node.UUID if skill_node.UUID is not None else "",
            crit_rate=calculator.regular_multipliers.crit_rate,
            crit_dmg=calculator.regular_multipliers.crit_dmg,
        )

    def _update_anomaly_bar_after_skill_event(
        self,
        skill_node: SkillNode,
        enemy: Enemy,
        tick: int,
        runtime_command_port: "RuntimeCommandPort",
        sim_instance: Simulator,
    ) -> None:
        """在技能事件后更新异常条"""
        node = skill_node
        should_update = False

        if not node.skill.anomaly_update_rule:
            if node.loading_mission is None:
                loading_mission = LoadingMission(node)
                loading_mission.mission_start(timenow=sim_instance.tick)
                node.loading_mission = loading_mission
            last_hit = node.loading_mission.get_last_hit()
            if last_hit is not None and tick - 1 < last_hit <= tick:
                should_update = True
        elif node.skill.anomaly_update_rule == -1:
            should_update = True
        elif (
            node.loading_mission is not None
            and node.skill.anomaly_update_rule is not None
            and (
                isinstance(node.skill.anomaly_update_rule, list)
                and node.loading_mission.hitted_count in node.skill.anomaly_update_rule
                or isinstance(node.skill.anomaly_update_rule, int)
                and node.loading_mission.hitted_count == node.skill.anomaly_update_rule
            )
        ):
            should_update = True

        if should_update:
            runtime_command_port.update_anomaly(
                element_type=node.element_type,
                enemy=enemy,
                tick=tick,
                skill_node=node,
            )

    def _settle_buffs(
        self,
        tick: int,
        enemy: Enemy,
        skill_node: SkillNode,
        runtime_command_port: "RuntimeCommandPort",
    ) -> None:
        """处理 Buff 结算"""
        runtime_command_port.settle_buffs(
            tick=tick,
            enemy=enemy,
            skill_node=skill_node,
        )

    def _update_damage_effects(
        self,
        tick: int,
        enemy: Enemy,
        data: ScheduleData,
        event: SkillNode | LoadingMission,
    ) -> None:
        """处理伤害后的附带效果更新"""
        schedule_dispatch_port = create_schedule_dispatch_port(schedule_data=data)
        ProcessHitUpdateDots(tick, enemy.dynamic.dynamic_dot_list, schedule_dispatch_port)
        ProcessFreezLikeDots(
            timetick=tick,
            enemy=enemy,
            schedule_publisher=schedule_dispatch_port,
            event=event,
        )
