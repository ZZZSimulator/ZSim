from zsim.sim_progress.Preload import SkillNode

# import Enemy
from zsim.sim_progress.Report import report_to_log

from .. import Dot
from .loading_mission import LoadingMission


def SpawnDamageEvent(mission: LoadingMission | Dot.Dot, event_list: list):
    """
    负责往event_list中添加伤害生成事件，添加的内容是实例：
    要么是SkillNode的实例，要么是Dot的实例。
    """
    if isinstance(mission, LoadingMission):
        if mission.hitted_count > mission.mission_node.hit_times:
            raise ValueError(
                f"{mission.mission_tag}目前是第{mission.hitted_count}，最多{mission.mission_node.hit_times}"
            )
        mission.hitted_count += 1
        event_list.append(mission)
    elif isinstance(mission, Dot.Dot):
        if (
            mission.dy.effect_times > mission.ft.max_effect_times
            and not mission.ft.complex_exit_logic
        ):
            raise ValueError("该Dot任务已经完成，应当被删除！")
        if mission.anomaly_data is not None:
            event_list.append(mission.anomaly_data)
        else:
            event_list.append(mission.skill_node_data)


def ProcessTimeUpdateDots(timetick: int, dot_list: list, event_list: list):
    """
    处理effect_rules == 1的Dot对象，始终检查是否应触发。
    """
    for dot in dot_list:
        if not isinstance(dot, Dot.Dot):
            raise TypeError(f"{dot}不是Dot类！")

        # 只处理 effect_rules == 1 的 Dot
        if dot.ft.effect_rules == 1:
            dot.ready_judge(timetick)
            if dot.dy.ready:
                dot.dy.last_effect_ticks = timetick
                dot.dy.ready = False
                dot.dy.effect_times += 1
                SpawnDamageEvent(dot, event_list)


def ProcessHitUpdateDots(timetick: int, dot_list: list, event_list: list):
    """
    处理effect_rules == 2的Dot对象，只在Mission触发或是Schedule进行检查。
    """
    for dot in dot_list:
        if not isinstance(dot, Dot.Dot):
            raise TypeError(f"{dot}不是Dot类！")

        # 只处理 effect_rules == 2 的 Dot
        if dot.ft.effect_rules == 2:
            dot.ready_judge(timetick)
            if dot.dy.ready:
                SpawnDamageEvent(dot, event_list)
                dot.dy.ready = False
                dot.dy.last_effect_ticks = timetick
                dot.dy.effect_times += 1


def ProcessFreezLikeDots(timetick: int, enemy, event_list: list, event):
    """
    所有碎冰类逻辑的dot都用此函数结算。
    """
    dot_list = enemy.dynamic.dynamic_dot_list
    skill_tag: str
    is_heavy_attack: bool
    if isinstance(event, LoadingMission):
        skill_tag = event.mission_tag
        if not event.is_heavy_hit(timetick):
            is_heavy_attack = False
        else:
            is_heavy_attack = True
    elif isinstance(event, SkillNode):
        skill_tag = event.skill_tag
        if not event.is_heavy_hit(timetick):
            is_heavy_attack = False
        else:
            is_heavy_attack = True
    else:
        raise TypeError(
            f"ProcessFreezLikeDots函数接收到的{event}不是LoadingMission或是SkillNode类！"
        )
    if not is_heavy_attack:
        if "1291_CorePassive" not in skill_tag:
            return
    for dot in dot_list[:]:
        if not isinstance(dot, Dot.Dot):
            raise TypeError(f"{dot}不是Dot类！")
        if dot.ft.effect_rules != 4:
            continue
        dot.ready_judge(timetick)
        if dot.dy.ready:
            print(f"{skill_tag}结算了碎冰！")
            SpawnDamageEvent(dot, event_list)
            dot.dy.ready = False
            dot.dy.last_effect_ticks = timetick
            dot.dy.effect_times += 1
            dot_list.remove(dot)
            enemy.dynamic.frozen = False
            return True


def DamageEventJudge(
    timetick: int,
    load_mission_dict: dict,
    enemy,
    event_list: list,
    char_obj_list: list,
    **kwargs,
):
    """
    DamageEvent的Judge函数：轮询load_mission_dict以及enemy.dynamic_dot_list，判断是否应生成Hit事件。
    并且当Hit时间生成时，将对应的实例添加到event_list中。
    当前可能产生Hit的mission类型共有两种，第一种是动作类，第二种是Dot类。
        1-动作类：
            首先应该查询mission.mission_dict，并且查询所有的键值，检查是否有键值需要在本tick处理。
            如果有，则应该将mission.mission_node传递给Schedule Event List。
        2-Dot类：
            首先应明确是固定随时间变化的Dot，还是命中后才产生伤害的Dot。这一条件以Dot.effect_rules来区分。
            如果effect_rules = 1，则表明是仅根据时间和内置CD来产生伤害的，则应该每个Tick都随着本函数执行一次判断；
            如果effect_rules = 2，则表明是根据命中来产生伤害的，则应该和动作类mission一起判断。
    同时，本函数还会在子任务是end的时候检查enemy的积蓄值。如果积蓄值满，则会触发异常（update_anomaly函数）
    """
    # 处理 Load.Mission 任务
    # dynamic_buff_dict = kwargs.get("dynamic_buff_dict", None)
    process_overtime_mission(timetick, load_mission_dict)
    for mission in load_mission_dict.values():
        if not isinstance(mission, LoadingMission | Dot.Dot):
            raise TypeError(f"{mission}不是LoadingMission或是Dot类！")
        if mission.is_hit_now(timetick):
            SpawnDamageEvent(mission, event_list)
            # 当Mission触发时，检查 effect_rules == 2 的 Dot
            # ProcessHitUpdateDots(timetick, enemy.dynamic.dynamic_dot_list, event_list)
    # 始终检查 effect_rules == 1 的 Dot
    ProcessTimeUpdateDots(timetick, enemy.dynamic.dynamic_dot_list, event_list)
    # TODO：预留接口：处理effect_rules == 3 的buff（但是涉及快照）


def process_overtime_mission(tick: int, Load_mission_dict: dict):
    """去除过期任务！"""
    to_remove = []
    for key, mission in Load_mission_dict.items():
        if not isinstance(mission, LoadingMission):
            continue
        mission.check_myself(tick)
        if not mission.mission_active_state:
            if key not in to_remove:
                to_remove.append(key)
    for key in to_remove:
        report_to_log(
            f"[Skill LOAD]:{tick}:{Load_mission_dict[key].mission_tag}已经结束,已从Load中移除",
            level=2,
        )
        Load_mission_dict.pop(key)
    # for mission_key, mission in Load_mission_dict.items():
    #     if mission_key == '1331_CoAttack_A':
    #         print(mission_key, mission.mission_node.preload_tick, mission.mission_node.end_tick)
