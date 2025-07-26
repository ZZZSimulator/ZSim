from __future__ import annotations

from typing import TYPE_CHECKING

from . import JudgeTools
from .buff_class import Buff
from .BuffAdd import add_debuff_to_enemy

if TYPE_CHECKING:
    from zsim.simulator.simulator_class import Simulator
    from zsim.sim_progress.Preload import SkillNode
    from zsim.sim_progress.Load import LoadingMission


def ScheduleBuffSettle(
    time_tick: int,
    exist_buff_dict: dict,
    enemy,
    DYNAMIC_BUFF_DICT: dict,
    action_stack,
    sim_instance: Simulator,
    **kwargs,
):
    """
    专门用于处理Schedule阶段才能处理的Buff（buff.ft.schedule_judge = True）
    此类Buff往往需要当前Tick的结果出来之后再判定触发与否；
    """
    preload_data = JudgeTools.find_preload_data(sim_instance=sim_instance)
    action_result = None
    if "anomaly_bar" in kwargs:
        anomaly_bar = kwargs["anomaly_bar"]
        if anomaly_bar.activated_by is not None:
            action_result = anomaly_bar.activated_by
    elif "skill_node" in kwargs:
        from zsim.sim_progress.Preload import SkillNode
        from zsim.sim_progress.Load import LoadingMission

        skill_node = kwargs["skill_node"]
        if isinstance(skill_node, SkillNode):
            action_result = skill_node
        elif isinstance(skill_node, LoadingMission):
            action_result = skill_node.mission_node
        else:
            print(f"ScheduleBuffSettle函数接收到了无法识别的event类型{type(skill_node).__name__}")
            return
    if action_result is None:
        action_now = preload_data.get_on_field_node(time_tick)
    else:
        action_now = action_result
    if action_now is None:
        print("Warnning！！！ScheduleBuffSettle函数没有找到action_now！")
        # FIXME: 修复这个问题！！！
        return
    char_on_field = action_now.char_name
    all_name_order_box = JudgeTools.find_all_name_order_box(sim_instance=sim_instance)
    name_box_on_field = all_name_order_box[char_on_field]
    for char_name in name_box_on_field:
        sub_exist_buff_dict = exist_buff_dict[char_name]
        if char_name == "enemy":
            continue
        elif char_name == char_on_field:
            process_schedule_on_field_buff(
                sub_exist_buff_dict,
                name_box_on_field,
                time_tick,
                DYNAMIC_BUFF_DICT,
                enemy,
                **kwargs,
            )
        else:
            process_schedule_backend_buff(
                sub_exist_buff_dict,
                all_name_order_box,
                time_tick,
                DYNAMIC_BUFF_DICT,
                enemy,
                **kwargs,
            )


def process_schedule_on_field_buff(
    sub_exist_buff_dict: dict,
    name_box_now: list,
    time_tick: int,
    DYNAMIC_BUFF_DICT: dict,
    enemy,
    **kwargs,
):
    """
    用来处理schedule阶段的前台buff。这里特殊说明一下name_box_now的情况
    这个list取自当前的init_data下的namebox，是经过顺序变化的、只适用于前台角色第一视角的name_box
    所以，这个box只能传入本函数， 为前台角色处理前台buff使用，在处理后台buff的函数中，
    应该获取的是all_name_order_box，并从中提取出对应的name_box
    """
    for buff in sub_exist_buff_dict.values():
        ArgumentCheck(buff=buff)
        if not buff.ft.schedule_judge:
            continue
        if buff.ft.passively_updating:
            continue
        # Buff判定
        all_match = buff.logic.xjudge(**kwargs)
        if not all_match:
            continue
        # Buff 激活
        adding_buff_code = str(int(buff.ft.add_buff_to)).zfill(4)
        selected_characters = [
            name_box_now[i] for i in range(len(name_box_now)) if adding_buff_code[i] == "1"
        ]
        # if buff.ft.index == 'Buff-武器-精1啜泣摇篮-全队增伤自增长':
        #     print(f'onfield函数处理了这个buff！当前的namebox是：{name_box_now}')
        add_schedule_buff(
            selected_characters,
            buff,
            time_tick,
            sub_exist_buff_dict,
            DYNAMIC_BUFF_DICT,
            enemy,
            **kwargs,
        )


def process_schedule_backend_buff(
    sub_exist_buff_dict: dict,
    all_name_order_box: dict,
    time_tick: int,
    DYNAMIC_BUFF_DICT: dict,
    enemy,
    **kwargs,
):
    """
    用来处理schedule阶段的后台buff。
    """
    for buff in sub_exist_buff_dict.values():
        ArgumentCheck(buff=buff)
        if not buff.ft.schedule_judge:
            continue
        if not buff.ft.backend_acitve:
            continue
        if buff.ft.passively_updating:
            continue
        all_match = buff.logic.xjudge(**kwargs)
        if not all_match:
            continue
        main_char = buff.ft.operator
        name_box_now = all_name_order_box[main_char]
        adding_buff_code = str(int(buff.ft.add_buff_to)).zfill(4)
        selected_characters = [
            name_box_now[i] for i in range(len(name_box_now)) if adding_buff_code[i] == "1"
        ]
        # if buff.ft.index == 'Buff-武器-精1啜泣摇篮-全队增伤自增长':
        #     print(f'backend函数处理了这个buff！当前的namebox是：{name_box_now}')
        add_schedule_buff(
            selected_characters,
            buff,
            time_tick,
            sub_exist_buff_dict,
            DYNAMIC_BUFF_DICT,
            enemy,
            **kwargs,
        )


def add_schedule_buff(
    selected_characters: list,
    buff: Buff,
    time_tick: int,
    sub_exist_buff_dict: dict,
    DYNAMIC_BUFF_DICT: dict,
    enemy,
    **kwargs,
):
    """
    Schedule阶段用来直接添加buff的函数
    """
    if not buff.ft.schedule_judge:
        raise ValueError(f"{buff.ft.index}不是schedule阶段buff！")
    for characters in selected_characters:
        buff_new = Buff.create_new_from_existing(buff)
        buff_new.ft.operator = buff.ft.operator
        buff_new.ft.passively_updating = buff.ft.passively_updating
        # if buff.ft.index == 'Buff-武器-精1啜泣摇篮-全队增伤自增长':
        #     print(f'buff_0情况：{buff.dy.startticks, buff.dy.endticks}')
        #     print(f'新buff情况：{buff_new.dy.startticks, buff_new.dy.endticks}')
        if not buff.ft.operator == characters:
            continue
        if buff.ft.simple_effect_logic:
            buff_new.simple_start(time_tick, sub_exist_buff_dict)
        else:
            buff_new.logic.xeffect(**kwargs)
        # Buff加载
        buff_existing_check = next(
            (
                existing_buff
                for existing_buff in DYNAMIC_BUFF_DICT[characters]
                if existing_buff.ft.index == buff.ft.index
            ),
            None,
        )
        if buff_existing_check:
            DYNAMIC_BUFF_DICT[characters].remove(buff_existing_check)
        DYNAMIC_BUFF_DICT[characters].append(buff_new)
        if characters == "enemy":
            buff_existing_check = next(
                (
                    existing_buff
                    for existing_buff in enemy.dynamic.dynamic_debuff_list
                    if existing_buff.ft.index == buff.ft.index
                ),
                None,
            )
            if buff_existing_check:
                enemy.dynamic.dynamic_debuff_list.remove(buff_existing_check)
            add_debuff_to_enemy(buff_new, characters, enemy)


def ArgumentCheck(**kwargs):
    action_now = kwargs.get("action_now", None)
    buff = kwargs.get("buff", None)
    if action_now:
        if not isinstance(action_now, LoadingMission):
            raise TypeError(f"{action_now}不是LoadingMission类！")
    if buff:
        if not isinstance(buff, Buff):
            raise TypeError(f"{buff}不是Buff类！")


if __name__ == "__main__":
    pass
