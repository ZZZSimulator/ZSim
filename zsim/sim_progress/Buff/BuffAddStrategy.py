from copy import deepcopy
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .buff_class import Buff

if TYPE_CHECKING:
    from zsim.sim_progress.ScheduledEvent.buff_runtime import (
        BuffRuntimeFacade,
        BuffTemplateRegistry,
    )
    from zsim.simulator.simulator_class import Simulator


@dataclass(frozen=True)
class BuffAddRuntimeContext:
    runtime_facade: "BuffRuntimeFacade"
    template_registry_owner: "BuffTemplateRegistry"
    all_name_order_box: dict[str, list[str]]
    tick: int


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
    specified_count: int | float | None = None,
    sim_instance: "Simulator | None" = None,
):
    """
    这个函数是暴力添加buff用的，比如霜寒、畏缩等debuff，
    又比如核心被动强行添加buff的行为，都可以通过这个函数来实现。
    Args:
        added_buffs: str: 需要添加的Buff的index
        benifit_list: list[str]: 受益者名单
        specified_count: int | float | None: 指定层数，非必要参数
        sim_instance: Simulator: 模拟器实例
    """
    if sim_instance is None:
        raise ValueError("调用buff_add_strategy函数时，sim_instance是None")
    buff_name_list: list[str] = _buff_filter(*added_buffs)
    runtime_context = _create_buff_add_runtime_context(sim_instance)
    runtime_facade = runtime_context.runtime_facade
    """
    将Buff名称、Buff实例转化为对应的Buff并写入 runtime active store。
    是在Load阶段以外通过 runtime 写侧门面完成强制添加的通用方式。
    """
    # 对于buff_name_list中的每个Buff都执行一次

    for buff_name in buff_name_list:
        # FIXME: 这里可能存在Bug，指定受益人（benifit_list）可能与自动查找的逻辑冲突。
        selected_characters = confirm_selected_character(
            runtime_facade,
            buff_name,
            runtime_context.all_name_order_box,
            benifit_list,
        )
        if selected_characters is None:
            print(
                f"【BuffAddStrategy警告】并未找到适用于{buff_name}的受益人！本次Buff添加将被跳过！"
            )
            continue

        # 针对每位受益人，都执行一次Buff添加
        for names in selected_characters:
            let_buff_start(
                runtime_facade,
                runtime_context.template_registry_owner,
                buff_name,
                names,
                specified_count,
                runtime_context.tick,
            )


def _create_buff_add_runtime_context(
    sim_instance: "Simulator",
) -> BuffAddRuntimeContext:
    return BuffAddRuntimeContext(
        runtime_facade=sim_instance.buff_runtime_state.create_facade(),
        template_registry_owner=(sim_instance.buff_runtime_state.template_registry_owner()),
        all_name_order_box=sim_instance.load_data.all_name_order_box,
        tick=sim_instance.tick,
    )


def _create_forced_add_buff_from_template_owner(
    template_registry_owner: "BuffTemplateRegistry",
    beneficiary: str,
    buff_index: str,
    *,
    tick: int,
    specified_count: int | float | None = None,
) -> Buff:
    source_registry = template_registry_owner.for_owner(beneficiary)
    source_buff = source_registry[buff_index]
    buff_new = deepcopy(source_buff)
    buff_new.ft.operator = source_buff.ft.operator
    buff_new.ft.passively_updating = source_buff.ft.passively_updating
    buff_new.ft.beneficiary = source_buff.ft.beneficiary

    if source_buff.ft.simple_start_logic and buff_new.ft.simple_effect_logic:
        if specified_count is not None:
            buff_new.simple_start(
                tick,
                source_registry,
                specified_count=specified_count,
            )
        else:
            buff_new.simple_start(tick, source_registry)
    elif not source_buff.ft.simple_start_logic:
        buff_new.logic.xstart(benifit=beneficiary)
    elif not source_buff.ft.simple_effect_logic:
        buff_new.logic.xeffect()
    return buff_new


def let_buff_start(
    runtime_facade: "BuffRuntimeFacade",
    template_registry_owner: "BuffTemplateRegistry",
    buff_name: str,
    names: str,
    specified_count: int | float | None,
    tick: int,
):
    """
    这个函数是buff_add_strategy函数的添加Buff的核心业务函数。
    Args:
        runtime_facade: 同 tick Buff runtime 写侧门面
        buff_name: str: Buff名称
        names: str: 受益者名称
        specified_count: int | float | None: 指定层数，非必要参数
        tick: int: 当前时间
    """
    buff_new = _create_forced_add_buff_from_template_owner(
        template_registry_owner,
        names,
        buff_name,
        tick=tick,
        specified_count=specified_count,
    )
    buff_existing_check = runtime_facade.find_active_buff_by_index(names, buff_new.ft.index)
    if buff_existing_check:
        runtime_facade.remove_active_buff(names, buff_existing_check)
    # print(f'强制添加Buff函数执行，本次为 {names} 添加的Buff为：{buff_new.ft.index}，激活状态为：{buff_new.dy.active}，开始时间为：{buff_new.dy.startticks}，结束时间为：{buff_new.dy.endticks}，层数：{buff_new.dy.count}')
    runtime_facade.append_active_buff(names, buff_new)
    # 如果是敌人，更新动态 Debuff 列表
    if names == "enemy":
        runtime_facade.sync_enemy_debuff_mirror(buff_new)


def get_selected_character(adding_buff_code, all_name_order_box, copyed_buff):
    if copyed_buff.ft.add_buff_to == "0001" or copyed_buff.ft.operator == "enemy":
        selected_characters = ["enemy"]
    else:
        name_box_now = all_name_order_box[copyed_buff.ft.operator]
        selected_characters = [
            name_box_now[i] for i in range(len(name_box_now)) if adding_buff_code[i] == "1"
        ]
    return selected_characters


def confirm_selected_character(
    runtime_facade: "BuffRuntimeFacade",
    buff_name: str,
    all_name_order_box: dict[str, list[str]],
    benifit_list: list[str] | None = None,
) -> list[str] | None:
    """
    确认选中的角色是否存在。
    Args:
        runtime_facade: Buff runtime 写侧门面
        buff_name: str: 即将执行强行添加的Buff名称
        all_name_order_box: dict[str, list[str]]: 所有角色的名称列表
        benifit_list: list[str]: 外部制定的受益者名单
    """
    registered_source = runtime_facade.find_registered_buff_source(buff_name)
    if registered_source is None:
        return None

    _, selected_buff = registered_source
    adding_buff_code = str(int(selected_buff.ft.add_buff_to)).zfill(4)
    return (
        get_selected_character(adding_buff_code, all_name_order_box, selected_buff)
        if benifit_list is None
        else benifit_list
    )
