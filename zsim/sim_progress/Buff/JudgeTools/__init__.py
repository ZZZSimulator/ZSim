from typing import TYPE_CHECKING

from .FindCharFromCID import find_char_from_CID
from .FindCharFromName import find_char_from_name
from .FindEquipper import find_equipper
from .FindMain import (
    find_all_name_order_box,  # noqa: F401
    find_char_list,
    find_dynamic_buff_list,
    find_enemy,
    find_event_list,
    find_exist_buff_dict,
    find_preload_data,
    find_stack,
    find_tick,  # noqa: F401
)

if TYPE_CHECKING:
    from .. import Buff


def check_preparation(buff_0, buff_instance: "Buff", **kwargs):
    """
    这是一个综合函数。根据传入的参数，来执行不同的内容。
    """
    # 先决条件检查
    if buff_0.history.record is None:
        raise ValueError("buff_0的record模块尚未初始化！！！")
    record = buff_0.history.record

    # 参数获取
    equipper: str = kwargs.get("equipper")
    char_CID: int = kwargs.get("char_CID")
    char_NAME: str = kwargs.get("char_NAME")
    enemy = kwargs.get("enemy")
    sub_exist_buff_dict = kwargs.get("sub_exist_buff_dict")
    dynamic_buff_list = kwargs.get("dynamic_buff_list")
    action_stack = kwargs.get("action_stack")
    event_list = kwargs.get("event_list")
    trigger_buff_0 = kwargs.get("trigger_buff_0")
    preload_data = kwargs.get("preload_data")
    char_obj_list = kwargs.get("char_obj_list")

    # 参数正确性检查
    if (
        sub_exist_buff_dict
        and char_NAME is None
        and char_CID is None
        and equipper is None
    ):
        raise ValueError(
            "在查询sub_exist_buff_dict的同时，应保证传入char_CID/char_NAME/equipper中的一个参数"
        )
    if (
        trigger_buff_0
        and trigger_buff_0[0] == "enemy"
        and not any([char_CID, char_NAME, equipper])
    ):
        raise ValueError(
            "在查询来自于enemy的trigger_buff_0的同时，应保证传入char_CID/char_NAME/equipper中的一个参数"
        )

    # 函数主体部分
    if equipper:
        if record.equipper is None:
            record.equipper = find_equipper(
                equipper, sim_instance=buff_instance.sim_instance
            )
        if record.char is None:
            record.char = find_char_from_name(
                record.equipper, sim_instance=buff_instance.sim_instance
            )
    if char_CID:
        if record.char is None:
            record.char = find_char_from_CID(
                char_CID, sim_instance=buff_instance.sim_instance
            )
    if char_NAME:
        if record.char is None:
            record.char = find_char_from_name(
                char_NAME, sim_instance=buff_instance.sim_instance
            )

    if sub_exist_buff_dict:
        if record.char is None:
            raise ValueError("在buff_0.history.record 中并未读取到对应的char")
        if record.sub_exist_buff_dict is None:
            record.sub_exist_buff_dict = find_exist_buff_dict(
                sim_instance=buff_instance.sim_instance
            )[record.char.NAME]
    if enemy:
        if record.enemy is None:
            record.enemy = find_enemy(sim_instance=buff_instance.sim_instance)
    if dynamic_buff_list:
        if record.dynamic_buff_list is None:
            record.dynamic_buff_list = find_dynamic_buff_list(
                sim_instance=buff_instance.sim_instance
            )
    if action_stack:
        if record.action_stack is None:
            record.action_stack = find_stack(sim_instance=buff_instance.sim_instance)
    if event_list:
        # print('event_list放在record中很有可能不会随动！！注意！')
        if record.event_list is None:
            record.event_list = find_event_list(sim_instance=buff_instance.sim_instance)
    if trigger_buff_0:
        trigger_buff_0_handler(record, trigger_buff_0, buff_instance=buff_instance)
    if preload_data:
        if record.preload_data is None:
            record.preload_data = find_preload_data(
                sim_instance=buff_instance.sim_instance
            )
    if char_obj_list:
        if record.char_obj_list is None:
            record.char_obj_list = find_char_list(
                sim_instance=buff_instance.sim_instance
            )


def trigger_buff_0_handler(record, trigger_buff_0, buff_instance: "Buff"):
    """
    该函数用于寻找trigger_buff_0，在搜索不同的触发器Buff‘时，程序所面临的情况往往是复杂的。
    1、触发器的操作者（operator）和受益者（beneficiary）都是本人的，那么传入的数据直接可以使用；
    2、触发器Buff来自于装备者的，其操作者不是一个固定人选，所以需要先找到equipper，再替换操作者；
    3、触发器的操作者和受益者不同的（比如目标Buff是一个debuff，存在于Enemy身上），此时，应该传入Operator
        ——原因是，Buff只有在自身是主视角的时候，才会执行触发，由于模拟器内没有Enemy的主视角，所以，Enemy所有的buff都是需要别的角色来添加的，
        所以，应该直接找到活跃的Buff源——也就是Buff 的Operator的源头。
    """
    if not isinstance(trigger_buff_0, tuple):
        raise TypeError("输入的参数必须是tuple！")
    if record.trigger_buff_0 is None:
        operator = trigger_buff_0[0]
        buff_index = trigger_buff_0[1]
        if operator == "equipper":
            if record.equipper is None:
                record.equipper = find_equipper(
                    operator, sim_instance=buff_instance.sim_instance
                )
                # FIXME:这里要解决传入的operator 是“equipper”字符串的问题！！！！虽然该分支不会被执行，所以从未出错（obsidian笔记详解一下）

            operator = record.equipper
        elif operator == "enemy":
            operator = record.char.NAME
        sub_exist_buff_dict = find_exist_buff_dict(
            sim_instance=buff_instance.sim_instance
        )[operator]
        founded_list = []
        for _buff_founded in sub_exist_buff_dict.values():
            if buff_index in _buff_founded.ft.index:
                founded_list.append(_buff_founded)
        if len(founded_list) != 1:
            """说明提供的关键词筛选出了多个Buff，此时需要进一步筛选出正确结果"""
            founded_buff_index_list = [
                founded_buff.ft.index for founded_buff in founded_list
            ]
            """验错环节"""
            if len(set(founded_buff_index_list)) != len(founded_list):
                raise ValueError(
                    f"在{operator}的sub_exist_buff_dict中找到了2个以上的同名buff！"
                )
            trigger_index_length = len(buff_index)
            for _buffs in founded_list:
                if _buffs.ft.index[-trigger_index_length:] == buff_index:
                    record.trigger_buff_0 = _buffs
                    break
            else:
                raise ValueError(
                    f"并未找到Buff名后缀为{buff_index}的触发器Buff，说明提供的用于寻找trigger_buff_0的关键词无法有效筛选出触发器，请调整关键词或者数据库Buff Index"
                )
        else:
            record.trigger_buff_0 = founded_list[0]
