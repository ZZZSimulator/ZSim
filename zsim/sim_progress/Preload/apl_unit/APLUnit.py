from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from zsim.define import compare_methods_mapping

from ..APLModule.SubConditionUnit import (
    ActionSubUnit,
    AttributeSubUnit,
    BaseSubConditionUnit,
    BuffSubUnit,
    SpecialSubUnit,
    StatusSubUnit,
)

if TYPE_CHECKING:
    from zsim.simulator.simulator_class import Simulator


class APLUnit(ABC):
    def __init__(self, sim_instance: "Simulator"):
        """一行APL就是一个APLUnit，它是所有APLUnit的基类。"""
        self.priority = 0
        self.char_CID = None
        self.break_when_found_action = True
        self.result = None
        self.sub_conditions_unit_list = []
        self.apl_unit_type = None
        self.sim_instance = sim_instance

    @abstractmethod
    def check_all_sub_units(
        self, found_char_dict, game_state, sim_instance: "Simulator", **kwargs
    ):
        pass


def spawn_sub_condition(
    priority: int, sub_condition_code: str = None
) -> ActionSubUnit | BuffSubUnit | StatusSubUnit | AttributeSubUnit | ActionSubUnit:
    """解构apl子条件字符串，并且组建出构建sub_condition类需要的构造字典"""
    logic_mode = 0
    sub_condition_dict = {}
    code_head = sub_condition_code.split(":")[0]
    if "special" not in code_head and "." not in code_head:
        raise ValueError(f"不正确的条件代码！{sub_condition_code}")
    if code_head.startswith("!"):
        code_head = code_head[1:]
        logic_mode = 1
    sub_condition_dict["type"] = code_head.split(".")[0]
    sub_condition_dict["target"] = code_head.split(".")[1]
    code_body = sub_condition_code.split(":")[1]
    for _operator in [">=", "<=", "==", ">", "<", "!="]:
        if _operator in code_body:
            sub_condition_dict["operation_type"] = compare_methods_mapping[_operator]
            sub_condition_dict["stat"] = code_body.split(_operator)[0]
            sub_condition_dict["value"] = code_body.split(_operator)[1]
            break
    else:
        raise ValueError(f"不正确的计算符！{code_body}")
    sub_condition_output = sub_condition_unit_factory(
        priority, sub_condition_dict, mode=logic_mode
    )
    return sub_condition_output


def sub_condition_unit_factory(priority: int, sub_condition_dict: dict = None, mode=0):
    """根据传入的dict，来构建不同的子条件单元"""
    condition_type = sub_condition_dict["type"]
    if condition_type not in ["status", "attribute", "buff", "action", "special"]:
        raise ValueError(f"不正确的条件类型！{sub_condition_dict['type']}")
    if condition_type == "status":
        return StatusSubUnit(priority, sub_condition_dict, mode)
    elif condition_type == "attribute":
        return AttributeSubUnit(priority, sub_condition_dict, mode)
    elif condition_type == "buff":
        return BuffSubUnit(priority, sub_condition_dict, mode)
    elif condition_type == "action":
        return ActionSubUnit(priority, sub_condition_dict, mode)
    elif condition_type == "special":
        return SpecialSubUnit(priority, sub_condition_dict, mode)
    else:
        raise ValueError(
            f"special类的APL解析，是当前尚未开发的功能！优先级为{priority}，"
        )


class SimpleUnitForForceAdd(APLUnit):
    def __init__(self, condition_list, sim_instance: "Simulator" = None):
        super().__init__(sim_instance=sim_instance)

        for condition_str in condition_list:
            self.sub_conditions_unit_list.append(
                spawn_sub_condition(self.priority, condition_str)
            )

    def check_all_sub_units(
        self, found_char_dict, game_state, sim_instance: "Simulator", **kwargs
    ):
        if self.sim_instance is None:
            self.sim_instance = sim_instance

        result_box = []
        tick = kwargs.get("tick", None)
        if not self.sub_conditions_unit_list:
            return True, result_box
        for sub_units in self.sub_conditions_unit_list:
            if not isinstance(sub_units, BaseSubConditionUnit):
                raise TypeError(
                    "ActionAPLUnit类的sub_conditions_unit_list中的对象构建不正确！"
                )
            result = sub_units.check_myself(
                found_char_dict, game_state, tick=tick, sim_instance=sim_instance
            )
            result_box.append(result)
            if not result:
                return False, result_box
        else:
            return True, result_box
