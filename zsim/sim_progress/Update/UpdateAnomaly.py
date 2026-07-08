import importlib
from copy import deepcopy
from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable

from zsim.define import ELEMENT_TYPE_MAPPING
from zsim.models.event_enums import ListenerBroadcastSignal as LBS
from zsim.sim_progress.anomaly_bar import AnomalyBar
from zsim.sim_progress.anomaly_bar.CopyAnomalyForOutput import (
    Disorder,
    NewAnomaly,
    PolarityDisorder,
)
from zsim.sim_progress.Buff.BuffAddStrategy import buff_add_strategy
from zsim.sim_progress.data_struct.schedule_dispatch import create_schedule_dispatch_port
from zsim.sim_progress.Dot.BaseDot import Dot
from zsim.sim_progress.Dot.runtime_state import DotRuntimeStateAdapter

if TYPE_CHECKING:
    from zsim.sim_progress.Buff import Buff
    from zsim.sim_progress.data_struct.schedule_dispatch import ScheduleDispatchPort
    from zsim.sim_progress.Preload import SkillNode
    from zsim.sim_progress.ScheduledEvent.buff_runtime import BuffRuntimeReadPort
    from zsim.simulator.dataclasses import ScheduleData
    from zsim.simulator.simulator_class import Simulator

anomlay_dot_dict = {
    0: "Assault",
    1: "Ignite",
    2: "Freez",
    3: "Shock",
    4: "Corruption",
    5: "Freez",
    6: "AuricInkCorruption",
}

FREEZE_DISORDER_DOT_INDEXES = {"Freez", "Freezdot"}


@dataclass(frozen=True)
class AnomalyRuntimeContext:
    dispatch_port: "ScheduleDispatchPort"
    listener_broadcaster: Callable[..., None]
    dot_runtime_state: DotRuntimeStateAdapter
    buff_runtime_view: "BuffRuntimeReadPort | None"
    sim_instance: "Simulator"


def create_anomaly_runtime_context(
    *,
    sim_instance: "Simulator",
    enemy,
    buff_runtime_view: "BuffRuntimeReadPort | None" = None,
    schedule_data: "ScheduleData | None" = None,
) -> AnomalyRuntimeContext:
    if schedule_data is not None and not hasattr(sim_instance, "schedule_data"):
        setattr(sim_instance, "schedule_data", schedule_data)
    return AnomalyRuntimeContext(
        dispatch_port=create_schedule_dispatch_port(
            sim_instance=sim_instance,
            schedule_data=schedule_data,
        ),
        listener_broadcaster=sim_instance.listener_manager.broadcast_event,
        dot_runtime_state=DotRuntimeStateAdapter.from_enemy(enemy),
        buff_runtime_view=buff_runtime_view,
        sim_instance=sim_instance,
    )


def spawn_output(anomaly_bar, mode_number, sim_instance: "Simulator", **kwargs):
    """
    该函数用于抛出一个新的属性异常类
    """
    if not isinstance(anomaly_bar, AnomalyBar):
        raise TypeError(f"{anomaly_bar}不是AnomalyBar类！")
    skill_node = kwargs.get("skill_node", None)
    listener_broadcaster = kwargs.get("listener_broadcaster", None)

    if mode_number == 0:
        # 先处理快照，使其除以总权值。
        anomaly_bar.anomaly_settled()
        output = NewAnomaly(anomaly_bar, active_by=skill_node, sim_instance=sim_instance)
    elif mode_number == 1:
        output = Disorder(anomaly_bar, active_by=skill_node, sim_instance=sim_instance)
    elif mode_number == 2:
        polarity_ratio = kwargs.get("polarity_ratio", None)
        if polarity_ratio is None:
            raise ValueError(
                "在调用spawn_output函数的模式二（mode_number=2）、企图生成一个极性紊乱对象时，并未传入必须的参数polarity_ratio！"
            )
        output = PolarityDisorder(
            anomaly_bar, polarity_ratio, active_by=skill_node, sim_instance=sim_instance
        )
    else:
        raise ValueError("在调用spawn_output函数时，未正确生成一个AnomalyBar实例！")
    # 广播事件
    if mode_number in [1, 2]:
        if listener_broadcaster is None:
            listener_broadcaster = sim_instance.listener_manager.broadcast_event
        listener_broadcaster(event=output, signal=LBS.DISORDER_SPAWN)
    return output


def _publish_scheduled_event(dispatch_port: "ScheduleDispatchPort", event) -> None:
    dispatch_port.publish_scheduled(event)


def _record_decibel_update(sim_instance: "Simulator", skill_node: "SkillNode", key: str) -> None:
    sim_instance.decibel_manager.update(skill_node=skill_node, key=key)


def _activate_anomaly_state(
    *,
    bar: AnomalyBar,
    element_type: int,
    enemy,
    time_now: int,
    dynamic_buff_dict: dict[str, list["Buff"]] | None,
    skill_node: "SkillNode",
    buff_runtime_view: "BuffRuntimeReadPort | None",
) -> AnomalyBar:
    bar.change_info_cause_active(
        time_now,
        dynamic_buff_dict=dynamic_buff_dict,
        skill_node=skill_node,
        buff_runtime_view=buff_runtime_view,
    )
    enemy.update_max_anomaly(element_type)

    active_bar = deepcopy(bar)
    enemy.dynamic.active_anomaly_bar_dict[element_type] = active_bar
    return active_bar


def _broadcast_active_anomaly(
    listener_broadcaster: Callable[..., None],
    active_bar: AnomalyBar,
) -> None:
    listener_broadcaster(event=active_bar, signal=LBS.ANOMALY)
    if active_bar.element_type in [0]:
        listener_broadcaster(event=active_bar, signal=LBS.ASSAULT_SPAWN)


def _set_active_anomaly_flag(enemy, element_type: int, active: bool) -> None:
    setattr(enemy.dynamic, enemy.trans_anomaly_effect_to_str[element_type], active)


def _publish_new_anomaly_if_required(
    dispatch_port: "ScheduleDispatchPort",
    enemy,
    element_type: int,
    new_anomaly,
) -> None:
    if element_type in [2, 5]:
        if enemy.dynamic.frozen:
            _publish_scheduled_event(dispatch_port, new_anomaly)
        enemy.dynamic.frozen = True
    else:
        _publish_scheduled_event(dispatch_port, new_anomaly)


def _notify_special_resources(char_obj_list: list, anomaly) -> None:
    for char_obj in char_obj_list:
        char_obj.special_resources(anomaly)


def _process_new_or_replaced_anomaly(
    *,
    active_bar: AnomalyBar,
    element_type: int,
    enemy,
    time_now: int,
    char_obj_list: list,
    sim_instance: "Simulator",
    skill_node: "SkillNode",
    dispatch_port: "ScheduleDispatchPort",
    listener_broadcaster: Callable[..., None],
    dot_runtime_state: DotRuntimeStateAdapter,
) -> None:
    new_anomaly = spawn_output(
        active_bar,
        0,
        skill_node=skill_node,
        sim_instance=sim_instance,
        listener_broadcaster=listener_broadcaster,
    )
    _notify_special_resources(char_obj_list, new_anomaly)
    anomaly_effect_active(
        active_bar,
        time_now,
        enemy,
        new_anomaly,
        element_type,
        sim_instance=sim_instance,
        dot_runtime_state=dot_runtime_state,
    )
    _publish_new_anomaly_if_required(dispatch_port, enemy, element_type, new_anomaly)
    _set_active_anomaly_flag(enemy, element_type, True)
    enemy.dynamic.active_anomaly_bar_dict[element_type] = active_bar


def _process_disorder_anomaly(
    *,
    active_bar: AnomalyBar,
    element_type: int,
    last_anomaly_element_type: int,
    enemy,
    time_now: int,
    char_obj_list: list,
    sim_instance: "Simulator",
    skill_node: "SkillNode",
    dispatch_port: "ScheduleDispatchPort",
    listener_broadcaster: Callable[..., None],
    dot_runtime_state: DotRuntimeStateAdapter,
) -> None:
    last_anomaly_bar = enemy.dynamic.active_anomaly_bar_dict[last_anomaly_element_type]
    _set_active_anomaly_flag(enemy, last_anomaly_element_type, False)
    _set_active_anomaly_flag(enemy, element_type, True)
    if element_type in [2, 5]:
        enemy.dynamic.frozen = True

    disorder = spawn_output(
        last_anomaly_bar,
        1,
        skill_node=skill_node,
        sim_instance=sim_instance,
        listener_broadcaster=listener_broadcaster,
    )
    enemy.dynamic.active_anomaly_bar_dict[last_anomaly_element_type] = None
    enemy.anomaly_bars_dict[last_anomaly_element_type].active = False
    remove_dots_cause_disorder(
        disorder,
        enemy,
        dispatch_port,
        time_now,
        dot_runtime_state=dot_runtime_state,
    )

    new_anomaly = spawn_output(
        active_bar,
        0,
        skill_node=skill_node,
        sim_instance=sim_instance,
        listener_broadcaster=listener_broadcaster,
    )
    anomaly_effect_active(
        active_bar,
        time_now,
        enemy,
        new_anomaly,
        element_type,
        sim_instance=sim_instance,
        dot_runtime_state=dot_runtime_state,
    )
    enemy.dynamic.active_anomaly_bar_dict[element_type] = active_bar

    if element_type not in [2, 5]:
        _publish_scheduled_event(dispatch_port, new_anomaly)
    _notify_special_resources(char_obj_list, disorder)
    _publish_scheduled_event(dispatch_port, disorder)
    _record_decibel_update(sim_instance, skill_node, "disorder")
    enemy.sim_instance.schedule_data.change_process_state()
    if disorder.activated_by:
        print(
            f"由【{disorder.activated_by.char_name}】的【{disorder.activated_by.skill_tag}】技能触发了紊乱！【{ELEMENT_TYPE_MAPPING[last_anomaly_bar.element_type]}】属性的异常状态提前结束！"
        )


def anomaly_effect_active(
    bar: AnomalyBar,
    timenow: int,
    enemy,
    new_anomaly,
    element_type,
    sim_instance: "Simulator",
    dot_runtime_state: DotRuntimeStateAdapter | None = None,
):
    """
    该函数的作用是创建属性异常附带的debuff和dot，
    debuff与dot的index写在了Anomaly.accompany_debuff和Anomaly.accompany_dot里。
    这里通过Buff的BuffInitialize函数来根据Buff名，直接提取对应的双字典，
    并且直接放进Buff的构造函数内，对新的Buff进行实例化。
    然后，回传给exist_buff_dict中的Buff0。
    Args:
        bar: AnomalyBar: 样本异常条实例，仅用于获取静态信息（多为字符串），不用于业务和运算
        timenow: int: 当前时间
        enemy: Enemy: 敌人实例
        new_anomaly: AnomalyBar: 新触发的异常实例，通常为参与业务的主体，是样本异常条实例的深拷贝
        element_type: int: 属性类型（0~6）
        sim_instance: Simulator: 模拟器实例
    """
    if bar.accompany_debuff:
        for debuff in bar.accompany_debuff:
            buff_add_strategy(debuff, sim_instance=sim_instance)
    if bar.accompany_dot:
        new_dot = spawn_anomaly_dot(
            element_type, timenow, bar=new_anomaly, sim_instance=sim_instance
        )
        if new_dot:
            if dot_runtime_state is None:
                dot_runtime_state = DotRuntimeStateAdapter.from_enemy(enemy)
            dot_runtime_state.replace_by_index(new_dot, timenow)


def update_anomaly(
    element_type: int,
    enemy,
    time_now: int,
    char_obj_list: list,
    sim_instance: "Simulator",
    skill_node: "SkillNode",
    dynamic_buff_dict: dict[str, list["Buff"]] | None,
    runtime_context: AnomalyRuntimeContext | None = None,
    buff_runtime_view: "BuffRuntimeReadPort | None" = None,
    **kwargs,
):
    """
    该函数需要在Schedule阶段的SkillEvent分支内运行。
    用于判断该次属性异常触发应该是新建、替换还是触发紊乱。
    第一个参数是属性种类，第二个参数是Enemy类的实例，第三个参数是当前时间
    如果判断通过触发，则会立刻实例化一个对应的属性异常实例（自带复制父类的状态与属性），
    """
    if runtime_context is None:
        runtime_context = create_anomaly_runtime_context(
            sim_instance=sim_instance,
            enemy=enemy,
            buff_runtime_view=buff_runtime_view,
        )
    dispatch_port = runtime_context.dispatch_port
    listener_broadcaster = runtime_context.listener_broadcaster
    dot_runtime_state = runtime_context.dot_runtime_state
    buff_runtime_view = runtime_context.buff_runtime_view
    sim_instance = runtime_context.sim_instance
    bar: AnomalyBar = enemy.anomaly_bars_dict[skill_node.element_type]
    if not isinstance(bar, AnomalyBar):
        raise TypeError(f"{type(bar)}不是Anomaly类！")
    active_anomaly_check, active_anomaly_list, last_anomaly_element_type = check_anomaly_bar(enemy)
    # 获取当前最大值。修改最大值的操作在确认内置CD转好后再执行。
    bar.max_anomaly = getattr(
        enemy, f"max_anomaly_{enemy.trans_element_number_to_str[element_type]}"
    )
    assert bar.max_anomaly is not None and bar.current_anomaly is not None, (
        "当前异常值或最大异常值为None！"
    )

    if bar.current_anomaly >= bar.max_anomaly:
        # 积蓄值蓄满了，但是属性异常不一定触发，还需要验证一下内置CD
        bar.ready_judge(time_now)
        if bar.ready:
            # 内置CD检测也通过之后，属性异常正式触发。现将需要更新的信息更新一下。
            _record_decibel_update(sim_instance, skill_node, "anomaly")
            active_bar = _activate_anomaly_state(
                bar=bar,
                element_type=element_type,
                enemy=enemy,
                time_now=time_now,
                dynamic_buff_dict=dynamic_buff_dict,
                skill_node=skill_node,
                buff_runtime_view=buff_runtime_view,
            )

            _broadcast_active_anomaly(listener_broadcaster, active_bar)
            """
            更新完毕，现在正式进入分支判断——触发同类异常 & 触发异类异常（紊乱）。
            无论是哪个分支，都需要涉及enemy下的两大容器：enemy_debuff_list以及enemy_dot_list的修改，
            同时，也可能需要修改exist_buff_dict以及DYNAMIC_BUFF_DICT
            """
            if element_type in active_anomaly_list or active_anomaly_check == 0:
                """
                这个分支意味着：新触发了某异常或是同类异常覆盖，此时应该执行的策略是“更新”，模式编码是0
                该策略下，只需要抛出一个新的属性异常给dot，不需要改变enemy的信息，只需要更新enemy的dot和debuff 两个list即可。
                """
                _process_new_or_replaced_anomaly(
                    active_bar=active_bar,
                    element_type=element_type,
                    enemy=enemy,
                    time_now=time_now,
                    char_obj_list=char_obj_list,
                    sim_instance=sim_instance,
                    skill_node=skill_node,
                    dispatch_port=dispatch_port,
                    listener_broadcaster=listener_broadcaster,
                    dot_runtime_state=dot_runtime_state,
                )
            elif element_type not in active_anomaly_list and len(active_anomaly_list) > 0:
                """
                这个分支意味着：要结算紊乱。那么需要复制的就不应该是新的这个属性异常，而应该是老的属性异常的bar实例。
                为了区分好用于计算的异常积蓄条，
                """
                assert last_anomaly_element_type is not None
                _process_disorder_anomaly(
                    active_bar=active_bar,
                    element_type=element_type,
                    last_anomaly_element_type=last_anomaly_element_type,
                    enemy=enemy,
                    time_now=time_now,
                    char_obj_list=char_obj_list,
                    sim_instance=sim_instance,
                    skill_node=skill_node,
                    dispatch_port=dispatch_port,
                    listener_broadcaster=listener_broadcaster,
                    dot_runtime_state=dot_runtime_state,
                )
            # 在异常与紊乱两个分支的最后，清空bar的异常积蓄和快照。
            else:
                raise ValueError("无法解析的异常/紊乱分支")
            bar.reset_current_info_cause_output()


def remove_dots_cause_disorder(
    disorder,
    enemy,
    dispatch_port,
    time_now,
    dot_runtime_state: DotRuntimeStateAdapter | None = None,
):
    """
    该函数只负责移除dot。
    """
    if dot_runtime_state is None:
        dot_runtime_state = DotRuntimeStateAdapter.from_enemy(enemy)
    remove_dots_list = _collect_disorder_dots_to_remove(
        dot_runtime_state,
        disorder,
    )
    sim_instance = enemy.sim_instance
    for dot in remove_dots_list:
        if _is_freeze_disorder_dot(dot):
            _publish_freeze_follow_up_for_removed_dot(dispatch_port, dot)
            _mark_freeze_dot_removed_by_disorder(dot, time_now)
            _remove_disorder_dot_from_runtime(dot_runtime_state, dot, time_now)
            _clear_freeze_runtime_flags(enemy)
        else:
            _remove_disorder_dot_from_runtime(dot_runtime_state, dot, time_now)
        _record_disorder_dot_removal_process(sim_instance)
        print(f"因紊乱而强行移除Dot {dot.ft.index}")


def _collect_disorder_dots_to_remove(
    dot_runtime_state: DotRuntimeStateAdapter,
    disorder,
) -> list[Dot]:
    dots_to_remove: list[Dot] = []
    for dot in dot_runtime_state.snapshot():
        if not isinstance(dot, Dot):
            raise TypeError(f"{dot}不是DOT类！")
        if not _should_remove_dot_for_disorder(dot, disorder):
            continue
        _validate_disorder_dot_can_be_removed(dot)
        dots_to_remove.append(dot)
    return dots_to_remove


def _should_remove_dot_for_disorder(dot: Dot, disorder) -> bool:
    return _is_freeze_disorder_dot(dot) or dot.ft.index == disorder.accompany_dot


def _validate_disorder_dot_can_be_removed(dot: Dot) -> None:
    if dot.dy.effect_times > dot.ft.max_effect_times:
        raise ValueError("该Dot任务已经完成，应当被删除！")


def _is_freeze_disorder_dot(dot: Dot) -> bool:
    return dot.ft.index in FREEZE_DISORDER_DOT_INDEXES


def _publish_freeze_follow_up_for_removed_dot(
    dispatch_port: "ScheduleDispatchPort",
    dot: Dot,
) -> None:
    _publish_scheduled_event(dispatch_port, dot.anomaly_data)


def _mark_freeze_dot_removed_by_disorder(dot: Dot, time_now: int) -> None:
    dot.dy.ready = False
    dot.dy.last_effect_ticks = time_now
    dot.dy.effect_times += 1


def _remove_disorder_dot_from_runtime(
    dot_runtime_state: DotRuntimeStateAdapter,
    dot: Dot,
    time_now: int,
) -> None:
    dot.end(time_now)
    dot_runtime_state.remove_all([dot])


def _clear_freeze_runtime_flags(enemy) -> None:
    enemy.dynamic.frozen = False
    enemy.dynamic.frostbite = False


def _record_disorder_dot_removal_process(sim_instance: "Simulator") -> None:
    sim_instance.schedule_data.change_process_state()


def check_anomaly_bar(enemy):
    """
    自检函数：
    1、检查当前激活的属性异常数量是否>2，如果是直接报错。
    2、由于冰与烈霜异常会导致2,5同时进入active_anomaly_check列表，所以这里要进行筛选
    """
    active_anomaly_check = 0
    active_anomaly_list = []
    anomaly_name_list = []
    for (
        element_number,
        element_anomaly_effect,
    ) in enemy.trans_anomaly_effect_to_str.items():
        if getattr(enemy.dynamic, element_anomaly_effect):
            anomaly_name_list.append(element_anomaly_effect)
            anomaly_name_list_unique = list(set(anomaly_name_list))
            active_anomaly_check = len(anomaly_name_list_unique)
            active_anomaly_list.append(element_number)
        if active_anomaly_check >= 2:
            raise ValueError("当前同时存在两种以上的异常状态！！！")
    last_anomaly_element_type: int | None = None
    if len(active_anomaly_list) == 1:
        last_anomaly_element_type = active_anomaly_list[0]
    elif len(active_anomaly_list) == 2:
        if active_anomaly_list == [2, 5]:
            for number in [2, 5]:
                if enemy.anomaly_bars_dict[number].active:
                    last_anomaly_element_type = number
                    break
            else:
                raise TypeError(f"当前激活的异常类型列表为{active_anomaly_list}，是预期之外的值。")
    else:
        last_anomaly_element_type = None
    return active_anomaly_check, active_anomaly_list, last_anomaly_element_type


def spawn_anomaly_dot(
    element_type, timenow, bar=None, skill_tag=None, sim_instance: "Simulator | None" = None
):
    if element_type in anomlay_dot_dict:
        class_name = anomlay_dot_dict[element_type]
        new_dot = create_dot_instance(class_name, sim_instance=sim_instance, bar=bar)
        if isinstance(new_dot, Dot):
            new_dot.start(timenow)
        return new_dot
    else:
        return False


def spawn_normal_dot(dot_index, sim_instance: "Simulator", bar=None):
    if sim_instance is None:
        raise ValueError("sim_instance不能为空！")
    new_dot = create_dot_instance(dot_index, sim_instance=sim_instance, bar=bar)
    return new_dot


def create_dot_instance(class_name: str, sim_instance: "Simulator | None" = None, bar=None):
    # 动态导入相应模块
    module_name = f"zsim.sim_progress.Dot.Dots.{class_name}"  # 假设你的类都在dot.DOTS模块中
    try:
        module = importlib.import_module(module_name)  # 导入模块
        class_obj = getattr(module, class_name)  # 获取类对象
        if bar:
            dot_obj = class_obj(bar=bar, sim_instance=sim_instance)
        else:
            dot_obj = class_obj(sim_instance=sim_instance)
        return dot_obj  # 创建并返回类实例
    except (ModuleNotFoundError, AttributeError) as e:
        raise ValueError(f"加载类 {class_name} 失败：{e}")
