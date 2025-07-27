from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from ...APLModule.APLJudgeTools import check_number_type

if TYPE_CHECKING:
    from zsim.simulator.simulator_class import Simulator


class BaseSubConditionUnit(ABC):
    def __init__(self, priority: int, sub_condition_dict: dict = None, mode=0):
        """单个APL判断条件的对象基类。"""
        self.logic_mode = mode  # mode 为1 时为反逻辑
        self.priority = priority  # 优先级
        if sub_condition_dict is None:
            self.no_condition = True  # 无条件
        else:
            self.no_condition = False
        self.check_target = sub_condition_dict["target"]  # 检查目标 比如enemy，self，或者角色ID
        self.check_stat = None
        self.nested_stat_key_list = []
        """
        在check_stat难免会碰到多层的嵌套结构，在APL中，统一用'→'来表示嵌套结构，这个list就是用来装这些嵌套的key的。
        目前，nested_stat_key_list只为char.get_special_states函数服务
        """
        if "→" in sub_condition_dict["stat"]:  # 被检查的参数，这里有很多，不一一列举。
            self.check_stat = sub_condition_dict["stat"].split("→")[0]
            self.nested_stat_key_list = sub_condition_dict["stat"].split("→")[1:]
        else:
            self.check_stat = sub_condition_dict["stat"]
        self.operation_type = sub_condition_dict["operation_type"]  # 计算类型，主要是比较符和调用符
        self.check_value = check_number_type(
            sub_condition_dict["value"]
        )  # 参与计算的值 或者调用的函数名

    @abstractmethod
    def check_myself(
        self,
        found_char_dict,
        game_state,
        sim_instance: "Simulator" = None,
        *args,
        **kwargs,
    ):
        pass

    def spawn_result(self, value=None, **kwargs):
        """根据self.operation_type中的匿名函数来输出结果的函数"""
        # value = check_number_type(value)
        result = self.operation_type(value, self.check_value)
        # if self.priority == 11 and result:
        #     import inspect
        #     print(f'{self.priority}_result：{value, self.check_value, inspect.getsource(self.operation_type).strip(), result}')

        return self.translate_result(result)

    def translate_result(self, result):
        if self.logic_mode == 0:
            return result
        else:
            return not result
