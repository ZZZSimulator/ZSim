from zsim.sim_progress.Buff import Buff
from zsim.sim_progress.Dot import BaseDot
from zsim.sim_progress.Enemy import Enemy
from zsim.sim_progress.Report import report_buff_to_queue, report_to_log


def update_dynamic_bufflist(
    DYNAMIC_BUFF_DICT: dict, timetick, exist_buff_dict: dict, enemy: Enemy
):
    """
    该函数用于更新当前正处于活跃状态的Buff，
    并且根据时间或是其他规则判断这些Buff是否应该结束。
    结束的Buff会被移除。
    注意，该函数的运行位置会导致所有Buff于Ntick末尾消失的Buff在N+1tick的开头处理，
    当然这大部分情况下不会影响正确性。
    """
    update_anomaly_bar(timetick, enemy)
    for charname in exist_buff_dict:
        sub_exist_buff_dict = exist_buff_dict[charname]
        remove_buff_list = []
        for _ in DYNAMIC_BUFF_DICT[charname]:
            CheckBuff(_, charname)
            if not _.ft.simple_exit_logic:
                # 首先处理那些通过xexit逻辑模块来控制结束与否的buff。
                shoud_exit = _.logic.xexit()
                if not shoud_exit:
                    # 如果buff存在，再记录一次层数。
                    report_buff_to_queue(
                        charname, timetick, _.ft.index, _.dy.count, True, level=4
                    )
                else:
                    remove_buff_list.append(_)
            else:
                if _.ft.alltime:
                    # 对于alltime的buff，自然是每个tick都存在，所以每个tick都记录。
                    report_buff_to_queue(
                        charname, timetick, _.ft.index, _.dy.count, True, level=4
                    )
                    continue
                if _.ft.individual_settled:
                    if len(_.dy.built_in_buff_box) <= 0 or timetick >= _.dy.endticks:
                        # 层数为0或是到点了，都会导致buff结束，
                        remove_buff_list.append(_)
                        continue
                    else:
                        process_individual_buff(_, timetick)
                        # 先更新层数，再report。
                        report_buff_to_queue(
                            charname, timetick, _.ft.index, _.dy.count, True, level=4
                        )
                else:
                    if timetick > _.dy.endticks:
                        # 层数不独立的buff，时间到点了就要结束。
                        remove_buff_list.append(_)
                        continue
                    else:
                        # 没结束的buffreport一下层数。
                        report_buff_to_queue(
                            charname, timetick, _.ft.index, _.dy.count, True, level=4
                        )
        else:
            # 统一执行KickOut函数，移除buff
            for removed_buff in remove_buff_list:
                KickOutBuff(
                    DYNAMIC_BUFF_DICT,
                    removed_buff,
                    charname,
                    enemy,
                    sub_exist_buff_dict,
                    timetick,
                )

    update_dot(enemy, timetick)
    return DYNAMIC_BUFF_DICT


def process_individual_buff(_, timetick):
    """
    针对层数独立结算的buff的tuple的独立结算。去除过期的tuple
    """
    for tuples in _.dy.built_in_buff_box[:]:
        if tuples[1] <= timetick:
            _.dy.built_in_buff_box.remove(tuples)
            _.dy.count = len(_.dy.built_in_buff_box)


def KickOutBuff(
    DYNAMIC_BUFF_DICT: dict,
    buff: Buff,
    charname: str,
    enemy,
    sub_exist_buff_dict: dict,
    timetick: int,
):
    buff.end(timetick, sub_exist_buff_dict)
    DYNAMIC_BUFF_DICT[charname].remove(buff)
    report_to_log(
        f"[Buff END]:{timetick}:{buff.ft.index}结束，已从动态列表移除", level=4
    )
    if buff.ft.is_debuff:
        enemy.dynamic.dynamic_debuff_list.remove(buff)


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
                report_to_log(
                    f"[Dot END]:{timetick}:{_.ft.index}结束，已从动态列表移除", level=4
                )
        else:
            resulrt = _.exit_judge(enemy=enemy)
            if resulrt:
                _.end(timetick)
                enemy.dynamic.dynamic_dot_list.remove(_)
                report_to_log(
                    f"[Dot END]:{timetick}:{_.ft.index}结束，已从动态列表移除", level=4
                )


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
