import importlib
from copy import deepcopy

from zsim.define import ELEMENT_TYPE_MAPPING
from zsim.sim_progress.anomaly_bar import AnomalyBar
from zsim.sim_progress.anomaly_bar.CopyAnomalyForOutput import (
    Disorder,
    NewAnomaly,
    PolarityDisorder,
)
from zsim.sim_progress.Buff.BuffAddStrategy import buff_add_strategy
from zsim.sim_progress.Dot.BaseDot import Dot
from typing import TYPE_CHECKING
from zsim.models.event_enums import ListenerBroadcastSignal as LBS
if TYPE_CHECKING:
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


def spawn_output(anomaly_bar, mode_number, sim_instance: "Simulator", **kwargs):
    """
    该函数用于抛出一个新的属性异常类
    """
    if not isinstance(anomaly_bar, AnomalyBar):
        raise TypeError(f"{anomaly_bar}不是AnomalyBar类！")
    skill_node = kwargs.get("skill_node", None)

    # 先处理快照，使其除以总权值。
    anomaly_bar.anomaly_settled() if mode_number in [0] else None
    # 老逻辑
    # anomaly_bar.current_ndarray = (
    #     anomaly_bar.current_ndarray / anomaly_bar.current_anomaly
    # )
    # output = anomaly_bar.element_type, anomaly_bar.current_ndarray
    if mode_number == 0:
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
    return output


def anomaly_effect_active(
    bar: AnomalyBar,
    timenow: int,
    enemy,
    new_anomaly,
    element_type,
    sim_instance: "Simulator",
):
    """
    该函数的作用是创建属性异常附带的debuff和dot，
    debuff与dot的index写在了Anomaly.accompany_debuff和Anomaly.accompany_dot里。
    这里通过Buff的BuffInitialize函数来根据Buff名，直接提取对应的双字典，
    并且直接放进Buff的构造函数内，对新的Buff进行实例化。
    然后，回传给exist_buff_dict中的Buff0。
    """
    if bar.accompany_debuff:
        for debuff in bar.accompany_debuff:
            buff_add_strategy(debuff, sim_instance=sim_instance)
    if bar.accompany_dot:
        new_dot = spawn_anomaly_dot(
            element_type, timenow, bar=new_anomaly, sim_instance=sim_instance
        )
        if new_dot:
            for dots in enemy.dynamic.dynamic_dot_list[:]:
                if dots.ft.index == new_dot.ft.index:
                    dots.end(timenow)
                    enemy.dynamic.dynamic_dot_list.remove(dots)
            enemy.dynamic.dynamic_dot_list.append(new_dot)
            # event_list.append(new_dot)


def update_anomaly(
    element_type: int,
    enemy,
    time_now: int,
    event_list: list,
    char_obj_list: list,
    sim_instance: "Simulator",
    **kwargs,
):
    """
    该函数需要在Schedule阶段的SkillEvent分支内运行。
    用于判断该次属性异常触发应该是新建、替换还是触发紊乱。
    第一个参数是属性种类，第二个参数是Enemy类的实例，第三个参数是当前时间
    如果判断通过触发，则会立刻实例化一个对应的属性异常实例（自带复制父类的状态与属性），
    """
    skill_node = kwargs.get("skill_node")
    dynamic_buff_dict = kwargs.get("dynamic_buff_dict", None)
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
            sim_instance.decibel_manager.update(skill_node=skill_node, key="anomaly")
            bar.change_info_cause_active(
                time_now, dynamic_buff_dict=dynamic_buff_dict, skill_node=skill_node
            )
            enemy.update_anomaly(element_type)

            active_bar = deepcopy(bar)
            enemy.dynamic.active_anomaly_bar_dict[element_type] = active_bar

            # 异常事件监听器广播


            sim_instance.listener_manager.broadcast_event(event=active_bar, signal=LBS.ANOMALY)
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
                mode_number = 0
                new_anomaly = spawn_output(
                    active_bar, mode_number, skill_node=skill_node, sim_instance=sim_instance
                )
                for _char in char_obj_list:
                    _char.special_resources(new_anomaly)
                anomaly_effect_active(
                    active_bar,
                    time_now,
                    enemy,
                    new_anomaly,
                    element_type,
                    sim_instance=sim_instance,
                )
                if element_type in [2, 5]:
                    """
                    当前分支是冰异常和烈霜异常分支，触发异常后，不向eventlist里面添加事件。
                    但是如果有老的异常，那么就要立刻去掉老的，换上新的。
                    最后，frozen的状态参数被打开。
                    """
                    if enemy.dynamic.frozen:
                        event_list.append(new_anomaly)
                        # print("新的冰异常触发导致老碎冰直接结算")
                    enemy.dynamic.frozen = True
                    # print("触发了新的冰异常！")
                else:
                    """
                    只要不是冰和烈霜异常，就直接向eventlist里面添加即可。
                    """
                    event_list.append(new_anomaly)
                setattr(enemy.dynamic, enemy.trans_anomaly_effect_to_str[element_type], True)
                enemy.dynamic.active_anomaly_bar_dict[element_type] = active_bar
            elif element_type not in active_anomaly_list and len(active_anomaly_list) > 0:
                """
                这个分支意味着：要结算紊乱。那么需要复制的就不应该是新的这个属性异常，而应该是老的属性异常的bar实例。
                为了区分好用于计算的异常积蓄条，
                """
                mode_number = 1
                last_anomaly_bar = enemy.dynamic.active_anomaly_bar_dict[last_anomaly_element_type]
                setattr(
                    enemy.dynamic,
                    enemy.trans_anomaly_effect_to_str[last_anomaly_element_type],
                    False,
                )
                setattr(enemy.dynamic, enemy.trans_anomaly_effect_to_str[element_type], True)
                if element_type in [2, 5]:
                    # if enemy.dynamic.frozen:
                    #     event_list.append(last_anomaly_bar)
                    enemy.dynamic.frozen = True
                    # print("触发了新的冰异常！")

                # 旧的激活异常拿出来复制，变成disorder后，从enemy身上清空。
                disorder = spawn_output(
                    last_anomaly_bar,
                    mode_number,
                    skill_node=skill_node,
                    sim_instance=sim_instance,
                )
                enemy.dynamic.active_anomaly_bar_dict[last_anomaly_element_type] = None
                enemy.anomaly_bars_dict[last_anomaly_element_type].active = False
                remove_dots_cause_disorder(disorder, enemy, event_list, time_now)

                # 新的激活异常根据原来的Bar进行复制，并且添加到enemy身上。
                new_anomaly = spawn_output(
                    active_bar, 0, skill_node=skill_node, sim_instance=sim_instance
                )
                anomaly_effect_active(
                    active_bar,
                    time_now,
                    enemy,
                    new_anomaly,
                    element_type,
                    sim_instance=sim_instance,
                )
                enemy.dynamic.active_anomaly_bar_dict[element_type] = active_bar

                # 向eventlist中添加事件。主要包括非烈霜、冰属性的新异常，以及紊乱。
                if element_type not in [2, 5]:
                    event_list.append(new_anomaly)
                for obj in char_obj_list:
                    obj.special_resources(disorder)
                event_list.append(disorder)
                sim_instance.decibel_manager.update(skill_node=skill_node, key="disorder")
                enemy.sim_instance.schedule_data.change_process_state()
                print(
                    f"由【{disorder.activated_by.char_name}】的【{disorder.activated_by.skill_tag}】技能触发了紊乱！【{ELEMENT_TYPE_MAPPING[last_anomaly_bar.element_type]}】属性的异常状态提前结束！"
                )
            # 在异常与紊乱两个分支的最后，清空bar的异常积蓄和快照。
            else:
                raise ValueError("无法解析的异常/紊乱分支")
            bar.reset_current_info_cause_output()


def remove_dots_cause_disorder(disorder, enemy, event_list, time_now):
    """
    该函数只负责移除dot。
    """
    remove_dots_list = []
    for dots in enemy.dynamic.dynamic_dot_list:
        if not isinstance(dots, Dot):
            raise TypeError(f"{dots}不是DOT类！")
        if dots.ft.index in ["Freez", "Freezdot"] or dots.ft.index == disorder.accompany_dot:
            if dots.dy.effect_times > dots.ft.max_effect_times:
                raise ValueError("该Dot任务已经完成，应当被删除！")
            remove_dots_list.append(dots)
    else:
        for _dot in remove_dots_list:
            if _dot.ft.index in ["Freez", "Freezdot"]:
                event_list.append(_dot.anomaly_data)
                _dot.dy.ready = False
                _dot.dy.last_effect_ticks = time_now
                _dot.dy.effect_times += 1
                _dot.end(time_now)
                enemy.dynamic.dynamic_dot_list.remove(_dot)
                enemy.dynamic.frozen = False
                enemy.dynamic.frostbite = False
            else:
                _dot.end(time_now)
                enemy.dynamic.dynamic_dot_list.remove(_dot)
            sim_instance = enemy.sim_instance
            sim_instance.schedule_data.change_process_state()
            print(f'因紊乱而强行移除Dot {_dot.ft.index}')


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
    element_type, timenow, bar=None, skill_tag=None, sim_instance: "Simulator" = None
):
    if element_type in anomlay_dot_dict:
        class_name = anomlay_dot_dict[element_type]
        new_dot = create_dot_instance(class_name, bar, sim_instance=sim_instance)
        if isinstance(new_dot, Dot):
            new_dot.start(timenow)
        return new_dot
    else:
        return False


def spawn_normal_dot(dot_index, sim_instance: "Simulator"):
    if sim_instance is None:
        raise ValueError("sim_instance不能为空！")
    new_dot = create_dot_instance(dot_index, sim_instance=sim_instance)
    return new_dot


def create_dot_instance(class_name, bar=None, sim_instance: "Simulator" = None):
    # 动态导入相应模块
    module_name = f"zsim.sim_progress.Dot.Dots.{class_name}"  # 假设你的类都在dot.DOTS模块中
    try:
        module = importlib.import_module(module_name)  # 导入模块
        class_obj = getattr(module, class_name)  # 获取类对象
        if bar:
            dot_obj: Dot = class_obj(bar=bar, sim_instance=sim_instance)
        else:
            dot_obj: Dot = class_obj(sim_instance=sim_instance)
        return dot_obj  # 创建并返回类实例
    except (ModuleNotFoundError, AttributeError) as e:
        raise ValueError(f"Error loading class {class_name}: {e}")
