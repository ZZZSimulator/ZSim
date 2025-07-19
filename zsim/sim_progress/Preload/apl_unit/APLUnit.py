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
        self.sub_conditions_ast = None
        self.apl_unit_type = None
        self.sim_instance = sim_instance

    @abstractmethod
    def check_all_sub_units(
            self, found_char_dict, game_state, sim_instance: "Simulator", **kwargs
    ):
        pass

    def evaluate_condition_ast(self, node: "ExprNode", found_char_dict, game_state, sim_instance, tick, result_box):
        """递归地评估逻辑树的表达式节点"""
        if node.is_leaf():
            if not isinstance(node.sub_condition, BaseSubConditionUnit):
                raise TypeError("逻辑树中包含非 BaseSubConditionUnit 类型的叶子节点")
            result = node.sub_condition.check_myself(
                found_char_dict, game_state, tick=tick, sim_instance=sim_instance
            )
            result_box.append(result)
            return result
        else:
            left_result = self.evaluate_condition_ast(node.left, found_char_dict, game_state, sim_instance, tick,
                                                      result_box)
            right_result = self.evaluate_condition_ast(node.right, found_char_dict, game_state, sim_instance, tick,
                                                       result_box)
            if node.operator == "and":
                return left_result and right_result
            elif node.operator == "or":
                return left_result or right_result
            else:
                raise ValueError(f"未知逻辑运算符: {node.operator}")


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


class ExprNode:
    def __init__(self, operator=None, left=None, right=None, sub_condition: "BaseSubConditionUnit" = None):
        """
        - operator: "and", "or"（逻辑运算符）
        - left/right: ExprNode 对象
        - sub_condition: 原子条件（BaseSubConditionUnit 的实例），只在叶子节点设置
        """
        self.operator = operator
        self.left = left
        self.right = right
        self.sub_condition = sub_condition

    def is_leaf(self):
        return self.operator is None


def logic_tree_to_expr_node(priority: int, logic_tree: dict | str | None) -> ExprNode | None:
    if logic_tree is None:
        return None
    # 如果是字符串（最小条件单元），构造叶子节点
    if isinstance(logic_tree, str):
        return ExprNode(sub_condition=spawn_sub_condition(priority, logic_tree))

    # 应该只有一个操作符键
    assert isinstance(logic_tree, dict) and len(logic_tree) == 1
    operator = list(logic_tree.keys())[0]
    children = logic_tree[operator]

    # 如果只有两个元素，直接构造左右节点
    if len(children) == 2:
        left_node = logic_tree_to_expr_node(priority, children[0])
        right_node = logic_tree_to_expr_node(priority, children[1])
        return ExprNode(operator=operator, left=left_node, right=right_node)

    # 如果超过两个，需要递归构造嵌套结构（左结合）
    current = logic_tree_to_expr_node(priority, children[0])
    for i in range(1, len(children)):
        right = logic_tree_to_expr_node(priority, children[i])
        current = ExprNode(operator=operator, left=current, right=right)
    return current
