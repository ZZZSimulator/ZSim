from __future__ import annotations

from typing import TYPE_CHECKING

from zsim.sim_progress import Buff, Preload, Report
from zsim.sim_progress.anomaly_bar import AnomalyBar as AnB
from zsim.sim_progress.anomaly_bar.CopyAnomalyForOutput import (
    DirgeOfDestinyAnomaly as Abloom,
)
from zsim.sim_progress.anomaly_bar.CopyAnomalyForOutput import (
    Disorder,
    PolarityDisorder,
)
from zsim.sim_progress.Buff import ScheduleBuffSettle
from zsim.sim_progress.Character import Character
from zsim.sim_progress.data_struct import (
    ActionStack,
    QuickAssistEvent,
    SchedulePreload,
    ScheduleRefreshData,
    SingleHit,
    SPUpdateData,
    StunForcedTerminationEvent,
)
from zsim.sim_progress.Load.LoadDamageEvent import (
    ProcessFreezLikeDots,
    ProcessHitUpdateDots,
)
from zsim.sim_progress.Load.loading_mission import LoadingMission
from zsim.sim_progress.Preload import SkillNode
from zsim.sim_progress.Update import update_anomaly

from .CalAnomaly import CalAbloom, CalAnomaly, CalDisorder, CalPolarityDisorder
from .Calculator import Calculator, MultiplierData  # noqa: F401

if TYPE_CHECKING:
    from zsim.simulator.simulator_class import Simulator


class ScConditionData:
    """
    用于记录在本tick可能的判断 buff 数据，以方便后续计算伤害
    """

    def __init__(self):
        self.buff_list: list = []
        self.when_crit: bool = False


class ScheduledEvent:
    """
    计划事件方法类

    主逻辑链 self.event_start()：
    1、读取计划事件列表，将其中所有的buff示例排到列表最靠前的位置。self.sort_events()
    2、遍历事件列表，从开始到结束，将每一个事件派发到分支逻辑链内进行处理
    """

    def __init__(
        self,
        dynamic_buff: dict,
        data,
        tick: int,
        exist_buff_dict: dict,
        action_stack: ActionStack,
        *,
        loading_buff: dict | None = None,
        sim_instance: Simulator,
    ):
        self.data = data  # ScheduleData in __main__
        self.data.dynamic_buff = dynamic_buff
        # self.judge_required_info_dict = data.judge_required_info_dict
        self.action_stack = action_stack

        if loading_buff is None:
            loading_buff = {}
        elif not isinstance(loading_buff, dict):
            raise ValueError(f"loading_buff参数必须为字典，但你输入了{loading_buff}")

        if not isinstance(tick, int):
            raise ValueError(f"tick参数必须为整数，但你输入了{tick}")

        # 更新Data
        self.tick = tick
        self.data.loading_buff = loading_buff
        self.exist_buff_dict = exist_buff_dict
        self.enemy = self.data.enemy

        self.execute_tick_key_map = {
            SkillNode: "preload_tick",
            QuickAssistEvent: "execute_tick",
            SchedulePreload: "execute_tick",
        }
        self.sim_instance: Simulator = sim_instance

    def event_start(self):
        """Schedule主逻辑"""
        # 更新角色面板
        for char in self.data.char_obj_list:
            char: Character
            sp_update_data = SPUpdateData(
                char_obj=char, dynamic_buff=self.data.dynamic_buff
            )
            char.update_sp_and_decibel(sp_update_data)
            if hasattr(char, "refresh_myself"):
                char.refresh_myself()
        self.process_event()

    def process_event(self):
        """处理当前所有事件"""
        if self.data.event_list:
            self.solve_buff()  # 先处理优先级高的buff
            # 筛选出可处理的事件，并且按照优先级排序，然后开始遍历执行。
            _processable_event_list = self.select_processable_event()
            # 其余事件挨个处理
            for _ in range(len(_processable_event_list)):
                event = _processable_event_list.pop(0)
                # 添加buff
                if isinstance(event, Buff.Buff):
                    raise NotImplementedError(
                        f"{type(event)}，目前不应存在于 event_list"
                    )
                elif isinstance(event, Preload.SkillNode | LoadingMission):
                    if event.preload_tick <= self.tick:
                        self.skill_event(event)
                        """
                        在2025.4.14的更新中，在skill_event分支新增了下面这个函数，
                        这是经过改良后的新的更新异常条的节点。
                        具体原因见函数内部，这里不过多赘述。
                        """
                        self.update_anomaly_bar_after_skill_event(event)
                        ScheduleBuffSettle(
                            self.tick,
                            self.exist_buff_dict,
                            self.enemy,
                            self.data.dynamic_buff,
                            self.action_stack,
                            skill_node=event,
                            sim_instance=self.sim_instance,
                        )
                        ProcessHitUpdateDots(
                            self.tick,
                            self.enemy.dynamic.dynamic_dot_list,
                            self.data.event_list,
                        )
                        ProcessFreezLikeDots(
                            timetick=self.tick,
                            enemy=self.enemy,
                            event_list=self.data.event_list,
                            event=event,
                        )
                    else:
                        raise ValueError(
                            f"event_start主循环正在尝试处理一个名为{event.skill_tag}的未来事件"
                        )
                elif isinstance(event, Abloom):
                    self.abloom_event(event)
                elif isinstance(event, PolarityDisorder):
                    self.polarity_disorder_event(event)
                elif isinstance(event, Disorder):
                    # print(f'检测到{event.element_type}属性的紊乱，快照为：{event.current_ndarray}')
                    self.disorder_event(event)
                elif isinstance(event, AnB):
                    self.anomaly_event(event)
                    ScheduleBuffSettle(
                        self.tick,
                        self.exist_buff_dict,
                        self.enemy,
                        self.data.dynamic_buff,
                        self.action_stack,
                        anomaly_bar=event,
                        sim_instance=self.sim_instance,
                    )
                elif isinstance(event, ScheduleRefreshData):
                    self.refresh_event(event)
                elif isinstance(event, QuickAssistEvent):
                    self.quick_assist_event(event)
                elif isinstance(event, SchedulePreload):
                    self.preload_event(event)
                elif isinstance(event, StunForcedTerminationEvent):
                    self.stun_forced_termination_event(event)
                else:
                    raise NotImplementedError(
                        f"{type(event)}，目前不应存在于 event_list"
                    )
                # 代码运行到这一行意味着事件已经被处理完毕，所以要将其从event_list中删除
                self.data.event_list.remove(event)
            # 计算过程中如果又有新的事件生成，则继续循环
            if self.data.event_list:
                if not self.check_all_event():
                    self.process_event()

    def check_all_event(self):
        """检查所有残留事件是否到期，只要有一个残留事件已经到期，直接返回False，激活递归。"""
        for event in self.data.event_list:
            # 获取事件类型对应的tick属性名
            execute_tick = self.get_executee_tick(event)
            if execute_tick is None:
                return False
            if execute_tick > self.tick:  # 严格大于当前tick才视为未到期
                continue
            else:
                return False
        return True

    def get_executee_tick(self, event) -> int | None:
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
                -> Schedule，AnomalyBar满，
            --(第N+1 Tick)--
                -> update_anomaly(异常条满，更新异常)
                -> Buff事件触发器检测（已经错过了触发窗口，所以触发器不触发）
            
        而在新的结构下，事件更新顺序为：
            --(第N Tick)-- 
                -> Schedule，AnomalyBar满，
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
            if self.tick - 1 < _node.loading_mission.get_last_hit() <= self.tick:
                should_update = True
        else:
            if _node.skill.anomaly_update_rule == -1:
                should_update = True
            else:
                if (
                    _node.loading_mission.hitted_count
                    in _node.skill.anomaly_update_rule
                ):
                    should_update = True
        if should_update:
            update_anomaly(
                _node.skill.element_type,
                self.enemy,
                self.tick,
                self.data.event_list,
                self.data.char_obj_list,
                skill_node=_node,
                dynamic_buff_dict=self.data.dynamic_buff,
                sim_instance=self.sim_instance,
            )

    def solve_buff(self) -> None:
        """提前处理Buff实例"""
        Buff.buff_add(
            self.tick, self.data.loading_buff, self.data.dynamic_buff, self.data.enemy
        )
        buff_events = []
        other_events = []
        for event in self.data.event_list[:]:
            if isinstance(event, Buff.Buff):
                buff_events.append(event)
            else:
                other_events.append(event)
        self.data.event_list = buff_events + other_events

    def skill_event(self, _event: Preload.SkillNode | LoadingMission) -> None:
        """SkillNode处理分支逻辑"""
        if isinstance(_event, LoadingMission):
            event = _event.mission_node
            hitted_count = _event.hitted_count
        else:
            event = _event
            hitted_count = 0
            """
            注意，主动动作的skill_node，都会在Load阶段被打包成LoadingMission的数据结构传入，所以具有非0的hitted_count，
            而其他阶段通过暴力手段添加进event_list的大概率都是未经打包的Skill_node，它们往往与hitted_count所关联的系统没有联动，所以此处强制设置为0
            目前，hitted_count参数只服务于enemy下面的QTE次数计算。未来若有其他需求，那么本函数则需要重构（迟早的事）
            """
        char_obj = None
        for character in self.data.char_obj_list:
            if character.NAME == event.skill.char_name:
                char_obj = character
        if char_obj is None:
            assert False, f"{event.skill.char_name} not found in char_obj_list"
        # 计算伤害的对象
        cal_obj = Calculator(
            skill_node=event,
            character_obj=char_obj,
            enemy_obj=self.data.enemy,
            dynamic_buff=self.data.dynamic_buff,
        )
        snapshot = cal_obj.cal_snapshot()
        stun = cal_obj.cal_stun()
        dmg_expect = cal_obj.cal_dmg_expect()
        dmg_crit = cal_obj.cal_dmg_crit()
        hit_result = SingleHit(
            skill_tag=event.skill_tag,
            snapshot=snapshot,
            stun=stun,
            dmg_expect=dmg_expect,
            dmg_crit=dmg_crit,
            hitted_count=hitted_count,
            proactive=_event.active_generation
            if isinstance(_event, SkillNode)
            else _event.mission_node.active_generation,
        )
        hit_result.skill_node = event
        if event.skill.follow_by:
            hit_result.proactive = False
        if event.hit_times == hitted_count and event.skill.heavy_attack:
            # 重攻击标签！
            hit_result.heavy_hit = True
        self.enemy.hit_received(hit_result, self.tick)

        Report.report_dmg_result(
            tick=self.tick,
            element_type=event.skill.element_type,
            skill_tag=event.skill_tag,
            dmg_expect=round(dmg_expect, 2),
            dmg_crit=round(dmg_crit, 2),
            stun=round(stun, 2),
            buildup=round(snapshot[1], 2),
            **self.data.enemy.dynamic.get_status(),
            UUID=event.UUID,
            crit_rate=cal_obj.regular_multipliers.crit_rate,
            crit_dmg=cal_obj.regular_multipliers.crit_dmg,
        )
        # enemy_dynamic=self.data.enemy.dynamic.__str__()

    def anomaly_event(self, event: AnB) -> None:
        """普通异常伤害处理分支逻辑"""
        cal_obj = CalAnomaly(
            anomaly_obj=event,
            enemy_obj=self.data.enemy,
            dynamic_buff=self.data.dynamic_buff,
            sim_instance=self.sim_instance,
        )
        dmg_anomaly = cal_obj.cal_anomaly_dmg()
        # TODO：异常伤害无法被enemy接收到，Enemy的血量更新是有问题的。
        Report.report_dmg_result(
            tick=self.tick,
            element_type=event.element_type,
            dmg_expect=round(dmg_anomaly, 2),
            is_anomaly=True,
            dmg_crit=round(dmg_anomaly, 2),
            stun=0,
            buildup=0,
            **self.data.enemy.dynamic.get_status(),
            UUID=event.UUID,
        )

    def disorder_event(self, event: Disorder):
        """紊乱处理分支逻辑"""
        cal_obj = CalDisorder(
            disorder_obj=event,
            enemy_obj=self.data.enemy,
            dynamic_buff=self.data.dynamic_buff,
            sim_instance=self.sim_instance,
        )
        dmg_disorder = cal_obj.cal_anomaly_dmg()
        stun = cal_obj.cal_disorder_stun()
        # TODO：紊乱伤害无法被enemy接收到，Enemy的血量更新是有问题的。
        self.data.enemy.update_stun(stun)
        Report.report_dmg_result(
            tick=self.tick,
            element_type=event.element_type,
            dmg_expect=round(dmg_disorder, 2),
            dmg_crit=round(dmg_disorder, 2),
            is_anomaly=True,
            is_disorder=True,
            stun=round(stun, 2),
            buildup=0,
            **self.data.enemy.dynamic.get_status(),
            UUID=event.UUID,
        )

    def polarity_disorder_event(self, event: PolarityDisorder):
        """极性紊乱处理分支逻辑"""
        cal_obj = CalPolarityDisorder(
            disorder_obj=event,
            enemy_obj=self.data.enemy,
            dynamic_buff=self.data.dynamic_buff,
            sim_instance=self.sim_instance,
        )
        dmg_disorder = cal_obj.cal_anomaly_dmg()
        Report.report_dmg_result(
            tick=self.tick,
            element_type=event.element_type,
            skill_tag="极性紊乱",
            dmg_expect=round(dmg_disorder, 2),
            dmg_crit=round(dmg_disorder, 2),
            is_anomaly=True,
            is_disorder=True,
            stun=0,
            buildup=0,
            **self.data.enemy.dynamic.get_status(),
            UUID=event.UUID,
        )

    def abloom_event(self, event: Abloom):
        """薇薇安异放处理分支逻辑"""
        cal_obj = CalAbloom(
            abloom_obj=event,
            enemy_obj=self.data.enemy,
            dynamic_buff=self.data.dynamic_buff,
            sim_instance=self.sim_instance,
        )
        dmg_anomaly = cal_obj.cal_anomaly_dmg()
        # TODO：异常伤害无法被enemy接收到，Enemy的血量更新是有问题的。
        Report.report_dmg_result(
            tick=self.tick,
            element_type=event.element_type,
            skill_tag="异放",
            dmg_expect=round(dmg_anomaly, 2),
            is_anomaly=True,
            dmg_crit=round(dmg_anomaly, 2),
            stun=0,
            buildup=0,
            **self.data.enemy.dynamic.get_status(),
            UUID=event.UUID,
        )

    def refresh_event(self, event: ScheduleRefreshData):
        """强制更新角色数据"""
        char_mapping = {
            character.NAME: character for character in self.data.char_obj_list
        }
        target: str = ""
        try:
            for target in event.sp_target:
                if target != "":
                    char_mapping[target].update_sp(event.sp_value)
            for target in event.decibel_target:
                if target != "":
                    char_mapping[target].update_decibel(event.decibel_value)
        except KeyError:
            raise ValueError(
                f"[Schedule] target: {target} not found in char_obj_list, check the alloc."
            )

    def quick_assist_event(self, event: QuickAssistEvent):
        """用于处理快速支援类方法的函数！"""
        if self.tick < event.execute_tick:
            # 发现现在处理还太早，塞回去。
            self.data.event_list.append(event)
            return
        event.execute_update(self.tick)

    def preload_event(self, event: SchedulePreload):
        """用于处理SchedulePreload事件的函数！"""
        if self.tick < event.execute_tick:
            # 发现现在处理还太早，塞回去。
            self.data.event_list.append(event)
            return
        event.execute_myself()

    def stun_forced_termination_event(self, event: StunForcedTerminationEvent):
        """用于处理被强制终止的异常事件的函数！"""
        if self.tick < event.execute_tick:
            # 发现现在处理还太早，塞回去。
            self.data.event_list.append(event)
            return
        event.execute_myself()

    def select_processable_event(self):
        """筛选当前可执行的事件，并且按照优先级排序，获取不到优先级的默认为0，"""
        _output_event_list = []
        for _event in self.data.event_list:
            execute_tick = self.get_executee_tick(_event)
            if execute_tick is None or execute_tick <= self.tick:
                """说明事件不存在execute_tick或已到期，需要被立刻执行。"""
                schedule_priority = getattr(_event, "schedule_priority", 0)
                # 使用bisect模块进行高效插入
                import bisect

                priorities = [
                    getattr(e, "schedule_priority", 0) for e in _output_event_list
                ]
                insert_pos = bisect.bisect_right(priorities, schedule_priority)
                _output_event_list.insert(insert_pos, _event)
        return _output_event_list


if __name__ == "__main__":
    pass
