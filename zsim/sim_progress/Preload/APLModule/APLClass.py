import json
from typing import TYPE_CHECKING

from zsim.define import APL_NA_ORDER_PATH, CHAR_PARRY_STRATEGY_MAP
from zsim.sim_progress.data_struct.NormalAttackManager import (
    BaseNAManager,
    na_manager_factory,
)
from zsim.sim_progress.Preload.APLModule.ActionReplaceManager import (
    ActionReplaceManager,
)

from ..apl_unit.ActionAPLUnit import ActionAPLUnit
from .APLOperator import APLOperator

if TYPE_CHECKING:
    from zsim.sim_progress.Preload import PreloadData
    from zsim.simulator.simulator_class import Simulator


class APLClass:
    """
    APL代码的执行部分。它会调用apl_condition并且轮询所有的APL代码，
    找出第一个符合条件的动作并且执行。
    """

    def __init__(
        self,
        all_apl_unit_list: list,
        preload_data: "PreloadData" = None,
        sim_instance: "Simulator" = None,
    ):
        self.game_state: dict | None = None
        self.sim_instance: "Simulator" = sim_instance
        self.preload_data = preload_data
        self.actions_list = all_apl_unit_list
        self.na_manager_dict: dict[int, BaseNAManager] = {}
        try:
            json_path = APL_NA_ORDER_PATH
            with open(json_path, "r", encoding="utf-8") as file:
                self.NA_action_dict = json.load(file)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"初始化时发生错误: {e}")
            self.NA_action_dict = {}
        self.apl_operator: APLOperator | None = None
        self.repeat_action: tuple[str, int] = ("", 0)
        self.action_replace_manager = None

    def execute(self, tick, mode: int) -> tuple[str, int, ActionAPLUnit]:
        if self.game_state is None:
            self.get_game_state()
        if self.apl_operator is None:
            self.apl_operator = APLOperator(
                self.actions_list,
                self.game_state,
                simulator_instance=self.sim_instance,
                preload_data=self.preload_data,
            )
        cid, skill_tag, apl_priority, apl_unit = (
            self.apl_operator.spawn_next_action_in_common_mode(tick)
            if not self.preload_data.atk_manager.attacking
            else self.apl_operator.spawn_next_action_in_atk_response_mode(tick)
        )
        final_result = self.perform_action(cid, skill_tag, tick)
        # FIXME: 这里的优先级修改可能存在问题，需要重新考虑一下。
        if final_result != skill_tag:
            apl_priority = 0
        return final_result, apl_priority, apl_unit

    def get_game_state(self) -> dict | None:
        if self.game_state is None:
            try:
                # 延迟从 sys.modules 获取字典A，假设 main 模块中已定义字典 A
                # main_module = sys.modules["simulator.main_loop"]
                # if main_module is None:
                #     raise ImportError("Main module not found.")
                # self.game_state = main_module.game_state  # 获取 main 中的 A
                self.game_state = self.preload_data.sim_instance.game_state
            except Exception as e:
                print(f"Error loading dictionary A: {e}")
        return self.game_state

    def perform_action(self, CID: int, action: str, tick: int) -> str:
        """APL逻辑判定通过，执行动作！"""
        if self.game_state is None:
            self.game_state = self.get_game_state()
        if self.preload_data is None:
            self.preload_data = self.game_state.get("preload").preload_data
        output = self.action_processor(CID, action, tick)
        return output

    def action_processor(self, CID, action, tick) -> str:
        """用于生成动作，以及模拟游戏内的部分动作替换逻辑"""

        if self.action_replace_manager is None:
            self.action_replace_manager = ActionReplaceManager(self.preload_data)
        result_tupe = self.action_replace_manager.action_replace_factory(
            CID, action, tick
        )
        if result_tupe[0]:
            output = result_tupe[1]
        else:
            output = self.spawn_action_directly(CID, action)
        return output

    def spawn_action_directly(self, CID, action):
        """在没有被快速支援、或是其他技能拦截的情况下，直接生成动作"""
        if action == "auto_NA":
            if CID not in self.na_manager_dict:
                for _char_obj in self.preload_data.char_data.char_obj_list:
                    if _char_obj.CID == CID:
                        self.na_manager_dict[CID] = na_manager_factory(_char_obj)
                        break
                else:
                    raise ValueError(f"在构造普攻管理器时，未找到CID为{CID}的角色！")
            current_na_manager = self.na_manager_dict[CID]
            stack = self.preload_data.personal_node_stack.get(CID, None)
            if stack is None:
                last_action = None
            else:
                last_action = stack.peek()
            if last_action is None or CID != self.preload_data.operating_now:
                """没有第一个动作时，直接派生第一段普攻"""
                output = current_na_manager.first_hit
            else:
                output = current_na_manager.spawn_out_na(last_action)
        elif action == "assault_after_parry":
            if CID in CHAR_PARRY_STRATEGY_MAP:
                output = CHAR_PARRY_STRATEGY_MAP[CID]
            else:
                output = f"{CID}_Assault_Aid"
        else:
            output = action
        return output
