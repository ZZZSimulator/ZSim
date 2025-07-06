from typing import TYPE_CHECKING

from .buff_class import Buff

if TYPE_CHECKING:
    from zsim.simulator.simulator_class import Simulator


def _buff_filter(*args, **kwargs):
    buff_name_list: list[str] = []
    for arg in args:
        if isinstance(arg, str):
            buff_name_list.append(arg)
        elif isinstance(arg, Buff):
            buff_name_list.append(arg.ft.index)
    for value in kwargs.values():
        if isinstance(value, str):
            buff_name_list.append(value)
        if isinstance(value, Buff):
            buff_name_list.append(value.ft.index)
    return buff_name_list


def buff_add_strategy(
    *added_buffs: str | Buff,
    benifit_list: list[str] | None = None,
    specified_count: int | None = None,
    sim_instance: "Simulator" = None,
):
    """
    这个函数是暴力添加buff用的，比如霜寒、畏缩等debuff，
    又比如核心被动强行添加buff的行为，都可以通过这个函数来实现。
    """
    if sim_instance is None:
        raise ValueError("调用buff_add_strategy函数时，sim_instance是None")
    buff_name_list: list[str] = _buff_filter(*added_buffs)

    all_name_order_box = sim_instance.load_data.all_name_order_box
    # name_box = main_module.load_data.name_box
    # name_box_now = name_box + ['enemy']
    enemy = sim_instance.schedule_data.enemy
    exist_buff_dict = sim_instance.load_data.exist_buff_dict
    tick = sim_instance.tick
    DYNAMIC_BUFF_DICT = sim_instance.global_stats.DYNAMIC_BUFF_DICT
    """
    将Buff名称、Buff实例转化为对应的Buff并且添加到DYNAMIC_BUFF_DICT或者其他地方。
    是在Load阶段以外暴力互动DYNAMIC_BUFF_DICT的通用方式。
    """
    for buff_name in buff_name_list:
        # FIXME: 这里可能存在Bug，指定受益人（benifit_list）可能与自动查找的逻辑冲突。
        for char_name, sub_exist_buff_dict in exist_buff_dict.items():
            if buff_name in sub_exist_buff_dict:
                copyed_buff = sub_exist_buff_dict[buff_name]
                if isinstance(copyed_buff, Buff):
                    # 创建新的 Buff 实例
                    adding_buff_code = str(int(copyed_buff.ft.add_buff_to)).zfill(4)
                    selected_characters = (
                        get_selected_character(
                            adding_buff_code, all_name_order_box, copyed_buff
                        )
                        if benifit_list is None
                        else benifit_list
                    )
                    for names in selected_characters:
                        from copy import deepcopy

                        buff_new = deepcopy(copyed_buff)
                        # buff_new = Buff.create_new_from_existing(copyed_buff)
                        if (
                            copyed_buff.ft.simple_start_logic
                            and buff_new.ft.simple_effect_logic
                        ):
                            if specified_count is not None:
                                buff_new.simple_start(
                                    tick,
                                    sub_exist_buff_dict,
                                    specified_count=specified_count,
                                )
                            else:
                                buff_new.simple_start(tick, sub_exist_buff_dict)

                        elif not copyed_buff.ft.simple_start_logic:
                            # print(buff_new.ft.index)
                            buff_new.logic.xstart(benifit=names)
                        elif not copyed_buff.ft.simple_effect_logic:
                            buff_new.logic.xeffect()
                        # 更新 DYNAMIC_BUFF_DICT
                        dynamic_buff_list = DYNAMIC_BUFF_DICT.get(names, [])
                        buff_existing_check = next(
                            (
                                existing_buff
                                for existing_buff in dynamic_buff_list
                                if existing_buff.ft.index == buff_new.ft.index
                            ),
                            None,
                        )
                        if buff_existing_check:
                            dynamic_buff_list.remove(buff_existing_check)
                        # print(f'强制添加Buff函数执行，本次添加的Buff为：{buff_new.ft.index}，激活状态为：{buff_new.dy.active}，开始时间为：{buff_new.dy.startticks}，结束时间为：{buff_new.dy.endticks}，层数：{buff_new.dy.count}')
                        dynamic_buff_list.append(buff_new)

                        # 如果是敌人，更新动态 Debuff 列表
                        if names == "enemy":
                            enemy_dynamic_debuff_list = (
                                enemy.dynamic.dynamic_debuff_list
                            )
                            debuff_existing_check = next(
                                (
                                    existing_buff
                                    for existing_buff in enemy_dynamic_debuff_list
                                    if existing_buff.ft.index == buff_new.ft.index
                                ),
                                None,
                            )
                            if debuff_existing_check:
                                enemy_dynamic_debuff_list.remove(debuff_existing_check)
                            enemy_dynamic_debuff_list.append(buff_new)


def get_selected_character(adding_buff_code, all_name_order_box, copyed_buff):
    if copyed_buff.ft.add_buff_to == "0001" or copyed_buff.ft.operator == "enemy":
        selected_characters = ["enemy"]
    else:
        name_box_now = all_name_order_box[copyed_buff.ft.operator]
        selected_characters = [
            name_box_now[i]
            for i in range(len(name_box_now))
            if adding_buff_code[i] == "1"
        ]
    return selected_characters
