from typing import TYPE_CHECKING

from zsim.sim_progress.Preload.APLModule.APLJudgeTools import (
    check_cid,
    get_personal_node_stack,
)
from zsim.sim_progress.Preload.APLModule.SubConditionUnit import BaseSubConditionUnit

if TYPE_CHECKING:
    from zsim.simulator.simulator_class import Simulator

    from ... import PreloadClass
    from ...APLModule.ActionReplaceManager import ActionReplaceManager
    from ...PreloadDataClass import PreloadData


class ActionSubUnit(BaseSubConditionUnit):
    def __init__(self, priority: int, sub_condition_dict: dict = None, mode=0):
        super().__init__(
            priority=priority, sub_condition_dict=sub_condition_dict, mode=mode
        )

    class ActionCheckHandler:
        @classmethod
        def handler(cls, *args, **kwargs):
            raise NotImplementedError

    class LatestActionTagHandler(ActionCheckHandler):
        @classmethod
        def handler(cls, char_cid: int, game_state, tick: int) -> str | None:
            preload_data: "PreloadData" = game_state["preload"].preload_data
            lastest_node = preload_data.latest_active_generation_node
            if lastest_node is None:
                return None
            if lastest_node.end_tick >= tick:
                return lastest_node.skill_tag
            else:
                return None

    class StrictLinkedHandler(ActionCheckHandler):
        """强衔接判定，技能skill_tag符合的同时，还需要上一个动作刚好结束。"""

        @classmethod
        def handler(cls, char_cid: int, game_state, tick: int) -> str | None:
            char_stack = get_personal_node_stack(game_state).get(char_cid, None)
            if char_stack is None:
                return None
            else:
                for i in range(char_stack.length):
                    current_node = char_stack.peek_index(i + 1)
                    if current_node is None:
                        return None
                    if (
                        current_node.skill.labels is not None
                        and "additional_damage" in current_node.skill.labels
                    ):
                        continue
                    if current_node.end_tick != tick:
                        return None
                    return current_node.skill_tag
                else:
                    return None

    class LenientLinkedHandler(ActionCheckHandler):
        @classmethod
        def handler(cls, char_cid: int, game_state, tick: int) -> str | None:
            char_stack = get_personal_node_stack(game_state).get(char_cid, None)
            if char_stack is None:
                return None
            for i in range(char_stack.length):
                current_node = char_stack.peek_index(i)
                if current_node is None:
                    return None
                if (
                    current_node.skill.labels is not None
                    and "additional_damage" in current_node.skill.labels
                ):
                    continue
                else:
                    return current_node.skill_tag
            else:
                return None

    class PositiveLinkedHander(ActionCheckHandler):
        @classmethod
        def handler(cls, char_cid: int, game_state, tick: int) -> str | None:
            """
            积极衔接判定，技能skill_tag符合的同时，
            只要上一个动作没有结束，就尝试进行衔接！
            一般用于上一个节能可以被自己技能打断的情况，比如闪避。
            """
            char_stack = get_personal_node_stack(game_state).get(char_cid, None)
            if char_stack is None:
                return None
            for i in range(char_stack.length):
                current_node = char_stack.peek_index(i + 1)
                if current_node is None:
                    return None
                if (
                    current_node.skill.labels is not None
                    and "additional_damage" in current_node.skill.labels
                ):
                    continue
                if current_node.end_tick >= tick:
                    return current_node.skill_tag
            else:
                return None

    class FirstActionHandler(ActionCheckHandler):
        @classmethod
        def handler(cls, char_cid: int, game_state, tick: int) -> bool:
            char_stack = get_personal_node_stack(game_state).get(char_cid, None)
            if char_stack is None:
                return True
            else:
                current_node = char_stack.peek()
                if current_node is None:
                    return True
            return False

    class IsPerformingHandler(ActionCheckHandler):
        @classmethod
        def handler(cls, char_cid: int, game_state, tick: int) -> None | str:
            """该函数的主要作用是尝试获取角色正在释放的某个技能的skill_tag。如果角色现在有空，则直接返回None"""
            char_stack = get_personal_node_stack(game_state).get(char_cid, None)
            if char_stack is None:
                return None
            last_node = char_stack.peek()
            if last_node is None:
                return None
            else:
                if last_node.end_tick >= tick:
                    return last_node.skill_tag
                else:
                    return None

    class DuringParryHandler(ActionCheckHandler):
        @classmethod
        def handler(cls, char_cid: int, game_state, tick: int) -> bool:
            """该函数主要作用是判断当前角色是否正处于进攻交互阶段（招架、或者被击退）"""
            preload: "PreloadClass" = game_state["preload"]
            action_replace_manager: "ActionReplaceManager" = (
                preload.strategy.apl_engine.apl.action_replace_manager
            )
            if action_replace_manager is None:
                return False
            parry_strategy = action_replace_manager.parry_aid_strategy
            return parry_strategy.parry_interaction_in_progress

    class AssaultAidEnableHandler(ActionCheckHandler):
        @classmethod
        def handler(cls, char_cid: int, game_state, tick: int) -> bool:
            """该函数主要用于检查，当前角色的“支援突击”是否处于激活可用状态"""
            preload: "PreloadClass" = game_state["preload"]
            action_replace_manager: "ActionReplaceManager" = (
                preload.strategy.apl_engine.apl.action_replace_manager
            )
            if action_replace_manager is None:
                return False
            assault_aid_enable = (
                action_replace_manager.parry_aid_strategy.assault_aid_enable
            )
            return assault_aid_enable

    ActionHandlerMap = {
        "skill_tag": LatestActionTagHandler,
        "strict_linked_after": StrictLinkedHandler,
        "lenient_linked_after": LenientLinkedHandler,
        "positive_linked_after": PositiveLinkedHander,
        "first_action": FirstActionHandler,
        "is_performing": IsPerformingHandler,
        "during_parry": DuringParryHandler,
        "assault_aid_enable": AssaultAidEnableHandler,
    }

    def check_myself(
        self,
        found_char_dict,
        game_state,
        sim_instance: "Simulator" = None,
        *args,
        **kwargs,
    ):
        """处理 动作判定类 的子条件"""
        handler_cls = self.ActionHandlerMap.get(self.check_stat)
        handler = handler_cls() if handler_cls else None
        if not handler:
            raise ValueError(
                f"当前检查的check_stat为：{self.check_stat}，优先级为{self.priority}，暂无处理该属性的逻辑模块！"
            )
        if self.check_target in ["after", "team"]:
            return self.spawn_result(handler.handler(game_state))
        else:
            """check_target 不是 after（其实已经弃用了），就是CID"""

            check_cid(self.check_target)
            char_cid = int(self.check_target)
            tick = sim_instance.tick
            result = self.spawn_result(handler.handler(char_cid, game_state, tick))
            return result
        #     if self.check_stat == 'skill_tag':
        #         checked_value = get_last_action(game_state)
        #         return self.spawn_result(checked_value)
        #     else:
        #         raise ValueError(f'子条件中的check_stat为：{self.check_stat}，优先级为{self.priority}，暂无处理该属性的逻辑模块！')
        # else:
        #     raise ValueError(f'子条件中的check_target为：{self.check_target}，优先级为{self.priority}，暂无处理该目标类型的逻辑模块！')
