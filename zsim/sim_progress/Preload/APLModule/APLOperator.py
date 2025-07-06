from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from zsim.simulator.simulator_class import Simulator

    from ..apl_unit.ActionAPLUnit import ActionAPLUnit
    from ..apl_unit.APLUnit import APLUnit
    from ..PreloadDataClass import PreloadData


class APLOperator:
    """APL执行器，负责运行对象化的APL代码，并返回布尔值。"""

    def __init__(
        self,
        all_apl_unit_list,
        game_state: dict,
        preload_data: "PreloadData",
        simulator_instance: "Simulator" = None,
    ):
        self.game_state = game_state
        self.preload_data = preload_data
        self.found_char_dict = {}  # 用于装角色实例，键值是CID
        self.leagal_apl_type_list = [
            "action+=",
            "action.no_swap_cancel+=",
            "action.atk_response_positive+=",
            "action.atk_response_balance+=",
        ]
        self.sim_instance = simulator_instance
        from zsim.sim_progress.Preload.apl_unit.APLUnit import APLUnit

        self.apl_unit_inventory: dict[
            int, APLUnit
        ] = {}  # 用于装已经解析过的apl子条件实例。
        for unit_dict in all_apl_unit_list:
            self.apl_unit_inventory[unit_dict["priority"]] = self.apl_unit_factory(
                unit_dict
            )
            # print(unit_dict["priority"], unit_dict)

    def spawn_next_action_in_common_mode(
        self, tick
    ) -> tuple[int, str, int, "ActionAPLUnit"]:
        """APL执行器的核心功能函数——筛选出优先级最高的下一个动作（普通模式）"""
        atk_response_mode = self.preload_data.atk_manager.attacking
        if atk_response_mode:
            raise ValueError(
                "在进攻响应模式下，不能调用spawn_next_action_in_common_mode方法！"
            )

        for priority, apl_unit in self.apl_unit_inventory.items():
            from zsim.sim_progress.Preload.apl_unit.ActionAPLUnit import ActionAPLUnit
            from zsim.sim_progress.Preload.apl_unit.AtkResponseAPLUnit import (
                AtkResponseAPLUnit,
            )

            apl_unit: ActionAPLUnit | AtkResponseAPLUnit
            if isinstance(apl_unit, AtkResponseAPLUnit):
                continue
            result, result_box = apl_unit.check_all_sub_units(
                self.found_char_dict,
                self.game_state,
                tick=tick,
                sim_instance=self.sim_instance,
                preload_data=self.preload_data,
            )
            if not result:
                # if priority in [4] and tick <= 1200:
                #     print(
                #         f"这次不通过的APL优先级为{priority}，内容为{apl_unit.result} 判定结果为：{result_box}"
                #     )
                continue
            else:
                if apl_unit.break_when_found_action:
                    # print(
                    #     f"APL找到了新的最高优先级的动作！优先级为：{apl_unit.priority}，输出动作：{apl_unit.result}"
                    # )
                    return (
                        int(apl_unit.char_CID),
                        apl_unit.result,
                        apl_unit.priority,
                        apl_unit,
                    )
                else:
                    continue
        else:
            raise ValueError("没有找到符合要求的APL！")

    def spawn_next_action_in_atk_response_mode(
        self, tick
    ) -> tuple[int, str, int, "ActionAPLUnit"]:
        """APL执行器的核心功能函数——筛选出优先级最高的下一个动作（进攻响应模式）"""
        if not self.preload_data.atk_manager.attacking:
            raise ValueError(
                "在非进攻响应模式下，不能调用spawn_next_action_in_atk_response_mode方法！"
            )
        from zsim.sim_progress.Preload.apl_unit.ActionAPLUnit import ActionAPLUnit
        from zsim.sim_progress.Preload.apl_unit.AtkResponseAPLUnit import AtkResponseAPLUnit

        for priority, apl_unit in self.apl_unit_inventory.items():
            if isinstance(apl_unit, ActionAPLUnit | AtkResponseAPLUnit):
                result, result_box = apl_unit.check_all_sub_units(
                    self.found_char_dict,
                    self.game_state,
                    tick=tick,
                    sim_instance=self.sim_instance,
                    preload_data=self.preload_data,
                )
                if not result:
                    continue
                else:
                    return (
                        int(apl_unit.char_CID),
                        apl_unit.result,
                        apl_unit.priority,
                        apl_unit,
                    )
        else:
            raise ValueError("没有找到符合要求的APL！")

    def apl_unit_factory(self, apl_unit_dict) -> "APLUnit":
        """构造APL子单元的工厂函数"""
        from zsim.sim_progress.Preload.apl_unit.ActionAPLUnit import ActionAPLUnit
        from zsim.sim_progress.Preload.apl_unit.AtkResponseAPLUnit import AtkResponseAPLUnit

        if apl_unit_dict["type"] in ["action+=", "action.no_swap_cancel+="]:
            return ActionAPLUnit(apl_unit_dict, sim_instance=self.sim_instance)
        elif "action.atk_response" in apl_unit_dict["type"]:
            return AtkResponseAPLUnit(
                apl_unit_dict=apl_unit_dict, sim_instance=self.sim_instance
            )

        elif all(
            code_str in apl_unit_dict["type"]
            for code_str in ["a", "c", "t", "i", "o", "n"]
        ):
            raise ValueError(
                f"貌似是拼写错误，当前输入的APL类型为：{apl_unit_dict['type']}"
            )
        else:
            raise ValueError(f"无法识别的APL类型：{apl_unit_dict['type']}")
        # # Optimized Code:
        #
        # if "enemy" not in judge_code:
        #     return False
        # path, operator, value = self._judge_code_spliter(judge_code)
        # accessor = self._access_cache(path)  # 缓存访问器
        #
        # # 获取实际数值
        # target_value = accessor(self.game_state["schedule_data"])
        # if target_value is None:
        #     return False
        #
        # # 执行比较操作（可扩展更多运算符）

        # print("Debugging 1st", target_value, '2nd', value)
        # return compare_methods_mapping[operator](target_value, type(target_value)(value))  # 保持类型一致
