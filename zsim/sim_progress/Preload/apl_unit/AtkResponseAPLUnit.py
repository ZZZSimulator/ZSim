from typing import TYPE_CHECKING
from sim_progress.Preload.apl_unit.APLUnit import APLUnit

if TYPE_CHECKING:
    from simulator.simulator_class import Simulator


class AtkResponseAPLUnit(APLUnit):
    def __init__(self, apl_unit_dict: dict, sim_instance: "Simulator" = None):
        """动作响应类APL"""
        super().__init__(sim_instance=sim_instance)
        self.char_CID = apl_unit_dict["CID"]
        self.priority = apl_unit_dict["priority"]
        self.apl_unit_type = apl_unit_dict["type"]
        self.response_proactive_level = None  # 进攻响应APL的主动响应等级
        if self.apl_unit_type.split("_")[-1] == "positive+=":
            self.response_proactive_level = 1
        elif self.apl_unit_type.split("_")[-1] == "balance+=":
            self.response_proactive_level = 0
        else:
            raise ValueError(
                f"不正确的进攻响应APL类型：{self.apl_unit_type}，只能是positive或balance！"
            )
        if "atk_response" not in self.apl_unit_type:
            raise ValueError("企图对非进攻响应APL构造AtkResponseAPLUnit类！")
        self.break_when_found_action = True
        self.result = apl_unit_dict["action"]
        from sim_progress.Preload.apl_unit.APLUnit import spawn_sub_condition, logic_tree_to_expr_node

        for condition_str in apl_unit_dict["conditions"]:
            self.sub_conditions_unit_list.append(
                spawn_sub_condition(self.priority, condition_str)
            )

        self.sub_conditions_ast = logic_tree_to_expr_node(
            self.priority,
            apl_unit_dict.get("conditions_tree", None)
        )
        self.common_response_tag_list = ["parry", "dodge"]

    def check_all_sub_units(
        self, found_char_dict, game_state, sim_instance: "Simulator", **kwargs
    ):
        """仅供模式下的单行APL的逻辑函数：检查所有子条件并且输出结果"""
        result_box = []
        tick = kwargs.get("tick", None)
        if tick is None:
            tick = self.sim_instance.tick
        if not self.check_atk_response_conditions(tick):
            """如果进攻响应的前置条件不满足，直接返回False"""
            return False, result_box
        """在进行附加条件的检查之前，先检查当前时间是否符合响应策略积极度"""
        if not self.check_response_tick(tick):
            return False, result_box

        if self.sub_conditions_ast is None:
            return True, result_box

        final_result = self.evaluate_condition_ast(
            self.sub_conditions_ast, found_char_dict, game_state, sim_instance, tick, result_box
        )
        return final_result, result_box

    def check_atk_response_conditions(self, tick: int) -> bool:
        """检查进攻响应的前置条件是否满足"""
        atk_manager = self.sim_instance.preload.preload_data.atk_manager
        if not atk_manager.attacking:
            # print("当前没有正在进行的进攻事件，无法响应！")
            return False
        if atk_manager.is_answered:
            # print("当前进攻事件已经被响应，无法再次响应！")
            return False
        rt_tick = atk_manager.get_rt()

        can_be_answered_result_tuple: tuple = atk_manager.can_be_answered(
            rt_tick=rt_tick
        )
        if not can_be_answered_result_tuple[0]:
            print(
                f"当前进攻事件无法在第{tick}tick被响应，当前的响应窗口为{can_be_answered_result_tuple}"
            )
            return False
        return True

    def check_response_tick(self, tick: int) -> bool:
        """检查当前tick是否符合响应策略积极度"""
        proactive_level = self.response_proactive_level
        atk_manager = self.sim_instance.preload.preload_data.atk_manager
        response_window: tuple[int, int]
        skill_tick: int = 0
        if any(
            [common_tag in self.result for common_tag in self.common_response_tag_list]
        ):
            response_window = (
                atk_manager.interaction_window_open_tick,
                atk_manager.interaction_window_close_tick,
            )
        else:
            """如果技能并非常规响应动作（如强化E、大招等），则需要获取技能的具体ticks，来计算新的响应窗口。"""
            cid: int = int(self.char_CID)
            skill_obj_list = self.sim_instance.preload.preload_data.skills
            for _skill_obj in skill_obj_list:
                if cid == _skill_obj.CID:
                    skill_obj = _skill_obj
                    break
            else:
                raise ValueError(f"没有找到CID为{cid}的技能对象！")

            skill_tick: int = skill_obj.get_skill_info(
                skill_tag=self.result, attr_info="ticks"
            )
            response_window = atk_manager.get_uncommon_response_window(
                another_ta=skill_tick
            )
        if proactive_level == 0:
            """在平衡策略下，响应动作需要尽量晚一些执行，所以检测右边界
            但是又不能完全和右边界重合，因为那样太晚了，所以我们就让它提早一帧放行。"""
            if tick + 1 == response_window[1]:
                return True
        elif proactive_level == 1:
            from define import ENEMY_ATK_PARAMETER_DICT

            if skill_tick != 0 and skill_tick < ENEMY_ATK_PARAMETER_DICT["Taction"]:
                print(
                    f"Warning: 技能 {self.result} 的ticks小于基础参数Taction，这会导致响应窗口的左边界不正确！所以直接于左边界处拦截，直接返回False。"
                )
                """
                但若是这个响应动作的时间小于30tick，则一定会引起响应失败。
                在EnemyAttackAction中的get_first_hit的方法中，这一定会引起报错。
                为了保证程序的运行，我需要提前拦截这种错误，让本函数返回False并且输出错误信息。
                """
                return False
            """在积极策略下，响应动作需要尽量早一些执行，所以检测左边界"""
            if tick == response_window[0]:
                return True
        else:
            raise ValueError(
                f"不正确的进攻响应APL的主动响应等级：{self.response_proactive_level}！"
            )
        return False
