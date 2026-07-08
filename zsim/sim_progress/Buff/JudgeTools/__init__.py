from typing import TYPE_CHECKING

from .DetectEdges import detect_edge  # noqa: F401
from .FindCharFromCID import find_char_from_CID
from .FindCharFromName import find_char_from_name
from .FindEquipper import find_equipper
from .FindMain import find_all_name_order_box  # noqa: F401
from .FindMain import find_init_data  # noqa: F401,
from .FindMain import find_tick  # noqa: F401
from .FindMain import (
    find_char_list,
    find_enemy,
    find_exist_buff_dict,
    find_preload_data,
    find_stack,
)
from .PreparationContext import (  # noqa: F401
    BuffTemplateRegistryReadPort,
    CharacterLookup,
    EquipmentOwnerLookup,
    PreloadCommandPort,
    PreparationContext,
    TriggerBuffLookup,
    TriggerBuffRef,
    build_preparation_context_from_buff,
    build_preparation_context_from_sim_instance,
    create_calculator_runtime_read_context_from_sim_instance,
)
from .TriggerState import (  # noqa: F401
    TriggerBuffState,
    read_trigger_buff_state,
    read_trigger_buff_state_active,
)

if TYPE_CHECKING:
    from .. import Buff


def check_preparation(
    buff_0: "Buff | None",
    buff_instance: "Buff",
    equipper: str | None = None,
    char_CID: int | None = None,
    char_NAME: str | None = None,
    **kwargs,
):
    """
    这是一个综合函数。根据传入的参数，来执行不同的内容。
    """
    preparation_context = kwargs.pop("preparation_context", None)
    if preparation_context is not None and not isinstance(preparation_context, PreparationContext):
        raise TypeError("preparation_context必须是PreparationContext实例")
    if "event_list" in kwargs:
        raise ValueError(
            "check_preparation(..., event_list=...) 的旧 event_list 参数已删除；"
            "计划事件发布请使用 ScheduleDispatchPort。"
        )
    if preparation_context is None:
        raise ValueError(
            "check_preparation requires PreparationContext; old sim_instance "
            "fallback discovery has been removed."
        )

    # 先决条件检查
    assert buff_0 is not None, "buff_0不能为空"
    if buff_0.history.record is None:
        raise ValueError("buff_0的record模块尚未初始化！！！")
    record = buff_0.history.record

    # 参数获取
    enemy = kwargs.get("enemy")
    sub_exist_buff_dict = kwargs.get("sub_exist_buff_dict")
    dynamic_buff_list = kwargs.get("dynamic_buff_list")
    action_stack = kwargs.get("action_stack")
    trigger_buff_0 = kwargs.get("trigger_buff_0")
    preload_data = kwargs.get("preload_data")
    char_obj_list = kwargs.get("char_obj_list")
    na_skill_level = kwargs.get("na_skill_level")
    trigger_buff_ref = TriggerBuffRef.coerce(trigger_buff_0) if trigger_buff_0 else None

    # 参数正确性检查
    if sub_exist_buff_dict and char_NAME is None and char_CID is None and equipper is None:
        raise ValueError(
            "在查询sub_exist_buff_dict的同时，应保证传入char_CID/char_NAME/equipper中的一个参数"
        )
    if (
        trigger_buff_ref is not None
        and trigger_buff_ref.requires_character
        and not any([char_CID, char_NAME, equipper])
    ):
        raise ValueError(
            "在查询来自于enemy的trigger_buff_0的同时，应保证传入char_CID/char_NAME/equipper中的一个参数"
        )

    # 函数主体部分
    if equipper:
        if record.equipper is None:
            record.equipper = preparation_context.find_equipper(equipper)
        if record.char is None:
            assert record.equipper is not None, "equipper不能为空"
            record.char = preparation_context.find_char_from_name(record.equipper)
    if char_CID:
        if record.char is None:
            record.char = preparation_context.find_char_from_cid(char_CID)
    if char_NAME:
        if record.char is None:
            record.char = preparation_context.find_char_from_name(char_NAME)

    if sub_exist_buff_dict:
        if record.char is None:
            raise ValueError("在buff_0.history.record 中并未读取到对应的char")
        if record.sub_exist_buff_dict is None:
            record.sub_exist_buff_dict = preparation_context.find_sub_exist_buff_dict(
                record.char.NAME
            )
    if enemy:
        if record.enemy is None:
            record.enemy = preparation_context.enemy
    if dynamic_buff_list:
        if record.dynamic_buff_list is None:
            record.dynamic_buff_list = preparation_context.active_buff_view
    if action_stack:
        if record.action_stack is None:
            record.action_stack = preparation_context.action_stack
    if trigger_buff_ref:
        trigger_buff_0_handler(
            record,
            trigger_buff_ref,
            buff_instance=buff_instance,
            preparation_context=preparation_context,
        )
    if preload_data:
        if record.preload_data is None:
            record.preload_data = preparation_context.preload_data
    if char_obj_list:
        if record.char_obj_list is None:
            record.char_obj_list = preparation_context.char_obj_list
    if na_skill_level:
        if record.char is None:
            raise ValueError("在buff_0.history.record 中并未读取到对应的char")
        record.na_skill_level = record.char.skill_object.skill_level_dict.get("normal")


def trigger_buff_0_handler(
    record,
    trigger_buff_0,
    buff_instance: "Buff",
    preparation_context: PreparationContext | None = None,
):
    """
    该函数用于寻找trigger_buff_0，在搜索不同的触发器Buff‘时，程序所面临的情况往往是复杂的。
    1、触发器的操作者（operator）和受益者（beneficiary）都是本人的，那么传入的数据直接可以使用；
    2、触发器Buff来自于装备者的，其操作者不是一个固定人选，所以需要先找到equipper，再替换操作者；
    3、触发器的操作者和受益者不同的（比如目标Buff是一个debuff，存在于Enemy身上），此时，应该传入Operator
        ——原因是，Buff只有在自身是主视角的时候，才会执行触发，由于模拟器内没有Enemy的主视角，所以，Enemy所有的buff都是需要别的角色来添加的，
        所以，应该直接找到活跃的Buff源——也就是Buff 的Operator的源头。
    """
    trigger_buff_ref = TriggerBuffRef.coerce(trigger_buff_0)
    if preparation_context is None:
        raise ValueError(
            "trigger_buff_0 preparation requires PreparationContext; old Buff "
            "template discovery has been removed."
        )
    if record.trigger_buff_0 is None:
        operator = trigger_buff_ref.operator
        if trigger_buff_ref.operator_kind == TriggerBuffRef.EQUIPPER:
            if record.equipper is None:
                if preparation_context is None:
                    record.equipper = find_equipper(
                        operator, sim_instance=buff_instance.sim_instance
                    )
                else:
                    record.equipper = preparation_context.find_equipper(operator)
                # FIXME:这里要解决传入的operator 是“equipper”字符串的问题！！！！虽然该分支不会被执行，所以从未出错（obsidian笔记详解一下）

            operator = record.equipper
        elif trigger_buff_ref.operator_kind == TriggerBuffRef.ENEMY_SOURCE:
            operator = record.char.NAME

        resolved_trigger_ref = trigger_buff_ref.with_resolved_owner(operator)
        record.trigger_buff_0 = preparation_context.find_trigger_buff_ref(resolved_trigger_ref)
