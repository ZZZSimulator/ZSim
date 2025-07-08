import math

from zsim.define import (
    SWAP_CANCEL_DEBUG_TARGET_SKILL,
    SWAP_CANCEL_MODE_DEBUG,
)
from zsim.define import (
    SWAP_CANCEL_MODE_COMPLETION_COEFFICIENT as SCK,
)
from zsim.define import (
    SWAP_CANCEL_MODE_LAG_TIME as SCLT,
)

from .. import SkillNode
from .BasePreloadEngine import BasePreloadEngine

# EXPLAIN：关于SCK和LT的作用：
"""
以上两个系数分别是：
①合轴操作完成度系数 SWAP_CANCEL_MODE_COMPLETION_COEFFICIENT （程序中通常引用为SCK）
②操作滞后系数 SWAP_CANCEL_MODE_LAG_TIME （程序中通常引用为SCLT），它们共同用于模拟玩家的合轴操作。
因为不可能任意操作都具有完美的完成度（在第2帧就完美切人+下一招出手），
人体机能限制、注意力不集中、可能存在的操作习惯以及其他因素，都会导致合轴操作的延后实施，
所以，这里通过设置一个系数来模拟玩家的操作滞后程度，在计算时，我会取用skill_node的时长（skill.ticks)，并且乘以SCK，
所计算出的结果与SCLT参数相比较，取较小值作为最终的滞后时间（防止较长的技能滞后严重，导致模拟失真）。
后续的升级方向：
在引入随机数生成器后，可以进一步基于两个参数的基本值，对这两个参数进行随机处理，从而真正模拟玩家在操作端的浮动。
"""


class SwapCancelValidateEngine(BasePreloadEngine):
    """该引擎的作用是：判断当前传入的APL运行结果是否满足合轴的需求"""

    def __init__(self, data):
        super().__init__(data)
        self.validators = [
            self._validate_char_avaliable,
            self._validate_char_task_conflict,
            self._validate_swap_tick,
            self._validate_qte_activation,
            self._validate_wait_event,
            self._validate_swap_state_check,
            self._validate_swap_strategy_check,
        ]

        self.__report_tag = None

    @property
    def external_update_signal(self):
        return True if self.data.preload_action_list_before_confirm else False

    def run_myself(
        self,
        skill_tag: str,
        tick: int,
        apl_priority: int = 0,
        apl_skill_node: SkillNode | None = None,
        **kwargs,
    ) -> bool:
        """合轴可行性分析基本分为以下几个步骤：
        1、当前涉及角色是否有空
        2、合轴时间是否符合
        3、确认合轴后，将skill_tag和主动参数 打包成tuple"""
        self.active_signal = False
        """若当前APL动作为等待，那么直接返回False，不做任何操作。"""
        if self._validate_wait_event(apl_skill_tag=skill_tag):
            self._swap_cancel_debug_print(mode=0, skill_tag=skill_tag)
            return False
        """检测对应角色是否有空——当前tick是否存在未完成动作"""
        if not self._validate_char_avaliable(
            skill_tag=skill_tag, tick=tick, apl_skill_node=apl_skill_node
        ):
            self._swap_cancel_debug_print(mode=1, skill_tag=skill_tag)
            return False
        """检测当前tick的APL输出是否与角色自身的任务冲突——动作的顶替判定"""
        if not self._validate_char_task_conflict(
            skill_tag=skill_tag, apl_skill_node=apl_skill_node, tick=tick
        ):
            self._swap_cancel_debug_print(mode=2, skill_tag=skill_tag)
            return False

        """QTE状态过滤器——QTE阶段不支持任何合轴"""
        if self._validate_qte_activation(tick=tick, skill_node=apl_skill_node):
            return False

        """检测当前tick的角色状态是否支持合轴——切人CD检测、高优先级动作判定"""
        if not self._validate_swap_state_check(
            tick=tick, skill_tag=skill_tag, apl_skill_node=apl_skill_node
        ):
            self._swap_cancel_debug_print(mode=3, skill_tag=skill_tag)
            return False

        """检测当前的tick是否满足合轴操作的需求"""
        if not self._validate_swap_tick(skill_tag=skill_tag, tick=tick):
            self._swap_cancel_debug_print(mode=4, skill_tag=skill_tag)
            return False

        """检测当前的前台动作是否允许进行合轴——合轴策略过滤"""
        if not self._validate_swap_strategy_check(tick=tick, skill_tag=skill_tag):
            return False

        self.data.preload_action_list_before_confirm.append(
            (skill_tag, True, apl_priority)
        )
        self.active_signal = True
        return True

    def _validate_char_avaliable(
        self, skill_tag: str, apl_skill_node: SkillNode, tick: int
    ) -> bool:
        """角色是否可以获取的判定"""
        cid = int(skill_tag.split("_")[0])
        char_stack = self.data.personal_node_stack.get(cid, None)
        if char_stack is None:
            """角色的动作栈都尚未创建，说明角色当前没有任何动作，角色有空。"""
            return True
        """获取上一个非附加伤害的技能Node"""
        char_latest_node = char_stack.get_effective_node()
        # char_latest_active_node = char_stack.get_on_field_node(tick)
        # if char_latest_active_node is not None:
        #     print(char_latest_node.skill_tag, char_latest_active_node.skill_tag)
        if char_latest_node is None:
            """角色栈已经创建但是上一个动作为空，说明本动作是角色的第一个动作，角色有空。"""
            return True
        # print([_stacknode.skill_tag for _stacknode in char_stack.stack])
        # print(f'APL：{apl_skill_node.skill_tag, apl_skill_node.apl_priority}， 上个技能：{char_latest_node.skill_tag, char_latest_node.apl_priority, char_latest_node.end_tick}')

        """角色当前有一个正在发生的Node"""
        if char_latest_node.end_tick > tick:
            """如果该node是闪避，则直接放行——闪避是可以被自己的技能合轴、顶替的。"""
            if "dodge" in char_latest_node.skill_tag:
                # print(
                #     f"{apl_skill_node.char_name}的技能{apl_skill_node.skill_tag}企图取消自己的闪避技能！"
                # ) if SWAP_CANCEL_MODE_DEBUG else None
                return True
            elif (
                "parry" in char_latest_node.skill_tag
                and "knock_back_cause_parry" in skill_tag
            ):
                """对于衔接于招架之后的击退，要立即放行"""
                return True
            """正在进行的技能并非立即执行类型，而新的技能是立即执行类型，则放行"""
            if (
                apl_skill_node.skill.do_immediately
                and not char_latest_node.skill.do_immediately
            ):
                return True
            else:
                return False
        else:
            """角色上一个动作已经结束，说明角色有空。"""
            return True

    @staticmethod
    def spawn_lag_time(node: SkillNode) -> int:
        """
        生成滞后时间，关于函数中两个参数SCK和SCLT的含义，请参考本文件开头的注释。
        这里返回的lag_time是经过向上取整的。
        """
        lag_time = math.ceil(min(node.skill.ticks * SCK, SCLT))
        return lag_time

    def _validate_swap_tick(self, skill_tag: str, tick: int, **kwargs):
        """针对当前技能的合轴时间的检测"""
        current_node_on_field = self.data.get_on_field_node(tick)
        if current_node_on_field is None:
            return True

        # 放行所有的附加伤害——附加伤害通常都没有动作，所以无需合轴
        if (
            current_node_on_field.skill.labels is not None
            and "additional_damage" in current_node_on_field.skill.labels
        ):
            return True

        # 放行特别豁免清单中的技能，比如被击退等特殊动作；
        if any([_sub_tag in skill_tag for _sub_tag in ["knock_back"]]):
            return True

        swap_lag_tick = self.spawn_lag_time(current_node_on_field)
        if (
            swap_lag_tick
            + current_node_on_field.skill.swap_cancel_ticks
            + current_node_on_field.preload_tick
            > tick
        ):
            return False
        else:
            if SWAP_CANCEL_MODE_DEBUG and SWAP_CANCEL_DEBUG_TARGET_SKILL:
                if SWAP_CANCEL_DEBUG_TARGET_SKILL == skill_tag:
                    print(
                        f"监听的技能{skill_tag}满足合轴时间要求！合轴放行！上一个技能{current_node_on_field.skill_tag}因本次合轴而提前结束。"
                        f"本次合轴延迟时间为{swap_lag_tick + current_node_on_field.skill.swap_cancel_ticks}ticks，被合轴技能时间为{current_node_on_field.skill.ticks}ticks。"
                    )
            return True

    def _validate_qte_activation(self, tick: int, skill_node: SkillNode) -> bool:
        """针对当前技能的QTE是否处于激活状态的检测，当检查到有角色正在释放QTE时，返回True"""
        # enemy = self.data.sim_instance.schedule_data.enemy
        # if enemy.qte_manager.qte_data.single_qte is not None:
        #     if skill_node.skill.trigger_buff_level != 5:
        #         return True
        for _cid, stack in self.data.personal_node_stack.items():
            if stack.peek() is None:
                continue
            node_now = stack.peek()
            if node_now.end_tick > tick:
                if "QTE" in node_now.skill_tag:
                    # FIXME: 由于伊芙琳的QTE是可以进行合轴的，这里一定会遇到Bug。
                    return True
            continue
        else:
            return False

    def _validate_wait_event(self, apl_skill_tag: str = None) -> bool:
        """用于检测传入的apl动作是否为wait。"""
        if apl_skill_tag == "wait":
            return True
        else:
            return False

    def _validate_char_task_conflict(
        self, skill_tag: str, apl_skill_node: SkillNode, tick: int
    ) -> bool:
        """
        针对角色自身的任务冲突的检测——尽管角色当前tick有空
        但并不意味着apl抛出的动作就可以直接执行。
        APL抛出的动作还需要和角色自身的任务进行冲突检测，相互竞争和覆盖。
        """
        cid = int(skill_tag.split("_")[0])
        for _tuples in self.data.preload_action_list_before_confirm:
            _tuples: tuple[str, bool, int]
            """
            preload_data中，preload_action_list_before_confirm是一个列表，
            其中记录了当前tick要被抛出的动作，其中，每个元素是一个元组，
            元组的第一个元素是技能的tag，第二个元素是技能的主动类型，第三个元素是APL的优先级。
            
            对于当前函数来说，APL抛出的动作apl_skill_node尚未进入preload_action_list_before_confirm列表，
            此时该列表中的所有技能都来自于ForceAddEngine强行添加。
            """
            _tag = _tuples[0]
            if cid == int(_tag.split("_")[0]):
                """如果角色在当前tick有forceadd的任务，并且APL抛出的动作并非do_immediately，则返回False"""
                if not apl_skill_node.skill.do_immediately:
                    return False

                for obj in self.data.skills:
                    if not obj.CID == cid:
                        continue
                    if obj.get_skill_info(skill_tag=_tag, attr_info="do_immediately"):
                        """如果当前tick被force_add添加的skill_tag本来就是do_immediately类型，那么就没法抢队了"""
                        return False
                    else:
                        """附加伤害additional_damage（类似于“白雷”）由于不需要占用角色，所以可以免于被挤掉的命运"""
                        skill_info = obj.get_skill_info(
                            skill_tag=_tag, attr_info="labels"
                        )
                        if skill_info is None:
                            skill_info = {}
                        if "additional_damage" not in skill_info.keys():
                            """但若当前tick被force_add 添加的skill_tag只是个普通技能，那么就要执行顶替。"""
                            print(
                                f"即将添加的衔接技能：{_tuples}被{skill_tag}顶替！"
                            ) if SWAP_CANCEL_MODE_DEBUG else None
                            self.data.preload_action_list_before_confirm.remove(_tuples)
                            return True
                        break
                else:
                    raise ValueError(f"没找到{cid}对应的角色！")
            else:
                continue
        else:
            return True

    def _validate_swap_state_check(
        self, tick: int, skill_tag: str, apl_skill_node: SkillNode
    ):
        """检查角色当前的状态是否允许当前技能进行合轴"""
        cid = int(skill_tag.split("_")[0])
        node_on_field: SkillNode | None = self.data.get_on_field_node(tick)
        char_node_stack = self.data.personal_node_stack.get(cid, None)
        char_latest_node: SkillNode | None = (
            char_node_stack.peek() if char_node_stack else None
        )
        char_change_cd: bool
        last_actively_generated_node: SkillNode | None = (
            self.data.latest_active_generation_node
        )
        if node_on_field and not node_on_field.active_generation:
            """
            由于get_on_field_node函数只会尽量返回台前的主动技能，
            而当场上仅存在一个被动技能时，该技能也会被函数获取并且返回。
            这里需要检测返回结果的主动生成状态，若为False，则说明当前前台技能是被动技能，
            此时，node_on_field等同于None
            """
            node_on_field = None
        if char_latest_node is None:
            char_change_cd = True
        else:
            tick_delta = tick - char_latest_node.end_tick
            char_change_cd = tick_delta >= 60

        """当前台存在一个高优先级技能时，合轴操作都是不可用的"""
        if (
            node_on_field is not None
            and node_on_field.skill.do_immediately
            and "dodge" not in node_on_field.skill_tag
        ):
            return False

        """第一个主动动作时，直接放行"""
        if last_actively_generated_node is None:
            return True

        """当前台不存在技能或是前台技能并非高优先级时，那么可以进行合轴的进一步判定"""
        if str(cid) not in last_actively_generated_node.skill_tag:
            """当动作涉及切人时，需要进行切人CD的检测"""
            if char_change_cd:
                """当前角色的切人CD已经冷却完毕，则直接放行。"""
                return True
            else:
                if (
                    any(
                        [
                            _sub_tag in skill_tag
                            for _sub_tag in ["QTE", "Aid", "knock_back"]
                        ]
                    )
                    or apl_skill_node.skill.do_immediately
                ):
                    """如果是支援类和连携技这种无视切人CD的技能，那么此时角色可以切出"""
                    return True
                else:
                    return False
        else:
            """当动作不涉及切人时，直接放行"""
            return True

    def _validate_swap_strategy_check(self, tick: int, skill_tag: str):
        """该函数用于检测当前技能的合轴策略是否允许合轴——在场的主动动作是否允许合轴。"""
        cid = skill_tag.split("_")[0]
        last_actively_generated_node: SkillNode | None = (
            self.data.latest_active_generation_node
        )
        if (
            last_actively_generated_node is None
            or last_actively_generated_node.end_tick < tick
        ):
            return True

        if cid in last_actively_generated_node.skill_tag:
            return True
        else:
            if last_actively_generated_node.apl_unit is None:
                raise ValueError(
                    f"{last_actively_generated_node.skill_tag}作为主动动作但是却没有APLUnit！"
                )
            if (
                last_actively_generated_node.apl_unit.apl_unit_type
                == "action.no_swap_cancel+="
            ):
                """
                当前台技能的apl_unit非空（意味着前台技能来自于APL模块），
                并且apl_unit的种类为“action.no_swap_cancel+=”，即合轴禁止类型，则不可切人。
                """
                self._swap_cancel_debug_print(
                    mode=5,
                    skill_tag=skill_tag,
                    last_actively_generated_node=last_actively_generated_node,
                )
                return False
            return True

    def check_myself(self):
        if self.data.preload_action_list_before_confirm:
            self.active_signal = True

    def _swap_cancel_debug_print(
        self,
        mode: int,
        skill_tag: str,
        last_actively_generated_node: SkillNode | None = None,
    ):
        if not SWAP_CANCEL_MODE_DEBUG:
            return

        """由于APL的SwapCancelEngine基本会看每个tick都调用，所以这里需要避免重复播报。"""
        if self.__report_tag == skill_tag:
            return

        self.__report_tag = skill_tag
        skill_compare = True if SWAP_CANCEL_DEBUG_TARGET_SKILL else False

        if mode == 0:
            print("APL返回的结果是wait！")
        elif mode == 1:
            print(f"{skill_tag}所涉及角色当前没空！") if not skill_compare else print(
                f"{skill_tag}所涉及角色当前没空！"
            ) if skill_tag == SWAP_CANCEL_DEBUG_TARGET_SKILL else None
        elif mode == 2:
            print(
                f"{skill_tag}所涉及角色当前tick存在任务冲突，合轴失败！"
            ) if not skill_compare else (
                print(
                    f"{skill_tag}所涉所涉及角色当前tick存在任务冲突，合轴失败！及角色当前没空！"
                )
                if skill_tag == SWAP_CANCEL_DEBUG_TARGET_SKILL
                else None
            )
        elif mode == 3:
            print(
                f"{skill_tag}所涉及角色切人CD未就绪  或是 技能优先级低于前台技能，合轴失败！"
            ) if not skill_compare else print(
                f"{skill_tag}所涉及角色切人CD未就绪  或是 技能优先级低于前台技能，合轴失败！"
            ) if skill_tag == SWAP_CANCEL_DEBUG_TARGET_SKILL else None
        elif mode == 4:
            print(
                f"当前tick不满足{skill_tag}合轴所需的时间！"
            ) if not skill_compare else print(
                f"当前tick不满足{skill_tag}合轴所需的时间！"
            ) if skill_tag == SWAP_CANCEL_DEBUG_TARGET_SKILL else None
        elif mode == 5:
            print(
                f"{skill_tag}的上一个主动动作{last_actively_generated_node.skill.skill_tag}的APL策略为不要合轴！"
            ) if not skill_compare else print(
                f"{skill_tag}的上一个主动动作{last_actively_generated_node.skill.skill_tag}的APL策略为不要合轴！"
            ) if skill_tag == SWAP_CANCEL_DEBUG_TARGET_SKILL else None
        else:
            raise ValueError("mode参数错误！")
