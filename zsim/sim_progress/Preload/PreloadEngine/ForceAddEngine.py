from typing import TYPE_CHECKING

from .. import SkillNode
from ..APLModule.APLJudgeTools import get_game_state
from ..PreloadEngine import BasePreloadEngine

if TYPE_CHECKING:
    from zsim.simulator.simulator_class import Simulator


class ForceAddEngine(BasePreloadEngine):
    """该引擎的主要作用是：在技能结束时，检索它们的后置技能，并且执行添加"""

    def __init__(self, data):
        super().__init__(data)
        self.game_state = None
        self.found_char_dict = {}

    def run_myself(self, tick: int):
        """当每个node结束时，都应该调用这个函数来判断强制添加。"""
        self.active_signal = False
        for cid, stack in self.data.personal_node_stack.items():
            node: SkillNode | None
            node = stack.peek()
            if node is None:
                continue
            if node.end_tick > tick:
                """如果当前node并未结束，则不符合“node”结束的条件，则应该直接跳过。"""
                continue
            follow_up: list = node.skill.follow_up
            if not follow_up:
                continue
            conditions_unit: list = node.skill.force_add_condition_APL
            should_force_add, index = self.prcoess_force_add_apl(
                conditions_unit,
                skill_tag=node.skill_tag,
                tick=tick,
                sim_instance=self.data.sim_instance,
            )
            if should_force_add:
                # print(f'强制添加判定通过！该强制添加来自于{node.skill_tag}，将要添加：{follow_up[index]}')
                self.check_char(follow_up, index, node)  # 检验数据的正确性
                self.data.preload_action_list_before_confirm.append(
                    (follow_up[index], False, 0)
                )
                self.active_signal = True

    def check_char(self, follow_up, index, node):
        """
        该函数的作用：确保：B角色技能在强制预载时，并没有动作存在即可。
        如果程序流程合理，这个函数是不会被执行的。
        """
        follow_up_skill_CID = int(follow_up[index][:4])
        follow_up_skill_add_tick = node.end_tick
        followed_char_stack = self.data.personal_node_stack.get(
            follow_up_skill_CID, None
        )
        if followed_char_stack is not None:
            if node.end_tick < followed_char_stack.peek().end_tick:
                raise ValueError(
                    f"出现了不应该出现的情况！技能{follow_up[index]}理应在{node.skill_tag}之后、于{follow_up_skill_add_tick}执行，但是此时角色{follow_up_skill_CID}尚有动作存在。"
                )

    def prcoess_force_add_apl(
        self, conditions_unit, sim_instance: "Simulator", **kwargs
    ) -> tuple[bool, int]:
        """强制添加动作的前置判定，有APL模块则运行模块，无APL模块则直接通过。"""
        should_force_add = True
        index = 0
        tick = kwargs.get("tick", None)
        if conditions_unit and self.game_state is None:
            self.game_state = get_game_state(sim_instance=sim_instance)
        if conditions_unit:
            """存在条件类APL判定"""
            for unit in conditions_unit:
                _apl_result, result_box = unit.check_all_sub_units(
                    self.found_char_dict,
                    self.game_state,
                    tick=tick,
                    sim_instance=sim_instance,
                )
                if not _apl_result:
                    """当apl单元的自运行结果为False时，意味着该条APL的条件中存在着不满足的项，所以应该continue，赶紧去检查下个Box"""
                    should_force_add = False
                    index += 1
                else:
                    should_force_add = True
                    return should_force_add, index
            else:
                """
                for循环执行完毕后，还是没有return，那么就意味着，当前所有的APL单元的自运行都没通过，
                也就是说当前该动作组中的所有衔接动作都不满足自动衔接的条件，
                此时，返回False， index（这里的index其实已经无所谓了）
                """
                return should_force_add, index
        else:
            return should_force_add, index
