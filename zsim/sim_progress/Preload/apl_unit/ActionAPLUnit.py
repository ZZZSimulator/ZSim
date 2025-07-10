from typing import TYPE_CHECKING

from .APLUnit import APLUnit

if TYPE_CHECKING:
    from zsimsimulator.simulator_class import Simulator




class ActionAPLUnit(APLUnit):
    def __init__(self, apl_unit_dict: dict, sim_instance: "Simulator" = None):
        """动作类APL"""
        super().__init__(sim_instance=sim_instance)
        self.char_CID = apl_unit_dict["CID"]
        self.priority = apl_unit_dict["priority"]
        self.apl_unit_type = apl_unit_dict["type"]
        self.break_when_found_action = True
        self.result = apl_unit_dict["action"]
        from zsim.sim_progress.Preload.apl_unit.APLUnit import spawn_sub_condition

        for condition_str in apl_unit_dict["conditions"]:
            self.sub_conditions_unit_list.append(
                spawn_sub_condition(self.priority, condition_str)
            )
        self.builtin_percond_list: list = []
        if (
            self.result == "assault_after_parry"
        ):  # 对于突击支援，需要添加一项内置的条件检查。
            """APL脚本代码：action.CID:positive_linked_after==CID_knock_back_cause_parry"""
            precond_str_1 = f"action.{self.char_CID}:strict_linked_after=={self.char_CID}_knock_back_cause_parry"
            precond_str_2 = f"special.preload_data:operating_char=={self.char_CID}"

            for precond in [precond_str_1, precond_str_2]:
                self.builtin_percond_list.append(
                    spawn_sub_condition(self.priority, precond)
                )

    def check_all_sub_units(
        self, found_char_dict, game_state, sim_instance: "Simulator", **kwargs
    ):
        """单行APL的逻辑函数：检查所有子条件并且输出结果"""
        result_box = []
        tick = kwargs.get("tick", None)
        if self.builtin_percond_list:
            for precond_unit in self.builtin_percond_list:
                if not precond_unit.check_myself(
                    found_char_dict, game_state, tick=tick, sim_instance=sim_instance
                ):
                    return False, result_box
        if not self.sub_conditions_unit_list:
            """无条件直接输出True"""
            return True, result_box
        from zsim.sim_progress.Preload.APLModule.SubConditionUnit import (
            BaseSubConditionUnit,
        )

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
