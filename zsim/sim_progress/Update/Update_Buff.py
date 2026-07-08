from typing import TYPE_CHECKING

from zsim.sim_progress.Buff import Buff
from zsim.sim_progress.Dot import BaseDot
from zsim.sim_progress.Enemy import Enemy
from zsim.sim_progress.Report import report_buff_to_queue as _report_buff_to_queue
from zsim.sim_progress.Report import report_to_log

if TYPE_CHECKING:
    from zsim.sim_progress.ScheduledEvent.buff_runtime import BuffRuntimeFacade


def report_buff_to_queue(*args, **kwargs):
    return _report_buff_to_queue(*args, **kwargs)


def update_time_related_effect(
    timetick,
    enemy: Enemy,
    *,
    runtime_facade: "BuffRuntimeFacade",
):
    """
    更新一些和时间相关的效果，异常条、Buff、Dot
    """
    update_anomaly_bar(timetick, enemy)
    active_store = update_buff(timetick, runtime_facade=runtime_facade)
    update_dot(enemy, timetick)
    return active_store


def update_buff(
    timetick,
    *,
    runtime_facade: "BuffRuntimeFacade",
):
    """
    该函数用于更新当前正处于活跃状态的Buff，
    并且根据时间或是其他规则判断这些Buff是否应该结束。
    结束的Buff会被移除。
    注意，该函数的运行位置会导致所有Buff于Ntick末尾消失的Buff在N+1tick的开头处理，
    当然这大部分情况下不会影响正确性。
    """
    return runtime_facade.sweep_active_buffs(tick=timetick)


def next_dot_or_anomaly_wakeup_tick(enemy: Enemy, current_tick: int) -> int | None:
    """读取 Dot/异常状态下一次可能发生生命周期变化的 tick。"""
    candidates: list[int] = []
    for dot in enemy.dynamic.dynamic_dot_list:
        if not isinstance(dot, BaseDot.Dot):
            raise TypeError(f"Enemy的dot列表中的{dot}不是Dot类！")
        if dot.ft.complex_exit_logic:
            candidates.append(current_tick + 1)
            continue
        end_tick = int(dot.dy.end_ticks)
        candidates.append(end_tick if end_tick > current_tick else current_tick + 1)

    for bar in enemy.anomaly_bars_dict.values():
        if not getattr(bar, "active", False):
            continue
        max_duration = getattr(bar, "max_duration", None)
        if max_duration is None:
            candidates.append(current_tick + 1)
            continue
        expire_tick = int(bar.last_active + max_duration + 1)
        candidates.append(expire_tick if expire_tick > current_tick else current_tick + 1)

    future_candidates = [tick for tick in candidates if tick > current_tick]
    if not future_candidates:
        return None
    return min(future_candidates)


def CheckBuff(_, charname):
    """
    检查buff的参数情况。
    """
    if not isinstance(_, Buff):
        raise TypeError(f"{_}不是Buff类！")
    if _.ft.is_debuff and charname != "enemy":
        raise ValueError(f"{_.ft.index}是debuff但是却进入了{charname}的buff池！")
    if (not _.ft.is_debuff) and charname == "enemy":
        raise ValueError(f"{_.ft.index}是buff但是却在enemy的debuff池中！")


def update_dot(enemy: Enemy, timetick):
    for _ in enemy.dynamic.dynamic_dot_list[:]:
        if not isinstance(_, BaseDot.Dot):
            raise TypeError(f"Enemy的dot列表中的{_}不是Dot类！")
        if not _.ft.complex_exit_logic:
            if timetick >= _.dy.end_ticks:
                _.end(timetick)
                enemy.dynamic.dynamic_dot_list.remove(_)
                report_to_log(f"[Dot END]:{timetick}:{_.ft.index}结束，已从动态列表移除", level=4)
        else:
            exit_result = _.exit_judge(enemy=enemy)
            # 不是所有的dot的退出函数都有返回，这里必须处理退出函数不返回内容的情况
            if exit_result is None:
                raise ValueError("复杂退出逻辑Dot的退出函数必须返回有效布尔值")
            if exit_result:
                _.end(timetick)
                enemy.dynamic.dynamic_dot_list.remove(_)
                report_to_log(f"[Dot END]:{timetick}:{_.ft.index}结束，已从动态列表移除", level=4)


def update_anomaly_bar(time_now: int, enemy: Enemy):
    for element_type, bar in enemy.anomaly_bars_dict.items():
        result = bar.check_myself(time_now)
        if result:
            setattr(
                enemy.dynamic,
                enemy.trans_anomaly_effect_to_str[element_type],
                bar.active,
            )
            enemy.dynamic.active_anomaly_bar_dict[element_type] = None
