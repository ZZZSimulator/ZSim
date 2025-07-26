from typing import TYPE_CHECKING

from zsim.sim_progress.data_struct import (
    EnemyAttackEventManager,
    NodeStack,
    QuickAssistSystem,
)

from . import SkillNode

if TYPE_CHECKING:
    from zsim.simulator.simulator_class import Simulator


class PreloadData:
    """循环于Preload阶段内部的数据"""

    def __init__(self, skills, sim_instance, **kwargs):
        load_data = kwargs.get("load_data")
        self.sim_instance: "Simulator" = sim_instance
        self.preload_action: list[SkillNode] = []  # 最终return返回给外部申请的数据结构
        from zsim.sim_progress.Character.skill_class import Skill

        self.skills: list[Skill] = skills  # 用于创建SkillNode，是SkillNode构造函数的必要参数。

        self.personal_node_stack: dict[int, NodeStack] = {}  # 个人的技能栈
        self.current_node_stack: NodeStack = NodeStack(length=5)  # Preload阶段的总技能栈
        self.latest_active_generation_node: SkillNode | None = (
            None  # 最近一次主动生成的skillnode，#TODO：可能是无用参数！
        )
        self.preload_action_list_before_confirm: list[
            tuple[str, bool, int]
        ] = []  # 当前tick需要执行preload的SkillTag列表，列表中的元素是(skill_tag, active_generation)，其中，active_generation指的是动作是否是主动生成。
        self.name_box: list[str] | None = None
        self.char_data = None
        self.load_data = load_data
        self.load_mission_dict: dict = load_data.load_mission_dict
        self.quick_assist_system = None
        self.atk_manager: EnemyAttackEventManager | None = None

    @property
    def operating_now(self) -> int | None:
        """返回正在操作的角色"""
        if self.latest_active_generation_node is None:
            return None
        _cid = int(self.latest_active_generation_node.skill_tag.split("_")[0])
        return _cid

    def push_node_in_swap_cancel(self, node: SkillNode, tick: int):
        """合轴模式中的内部数据更新函数。将构造好的SkillNode加入preload_action中，同时更新Preload板块的内部数据。"""
        self.check_myself_before_push_node()
        self.preload_action.append(node)
        char_cid = int(node.skill_tag.split("_")[0])
        self.current_node_stack.push(node)
        if char_cid not in self.personal_node_stack:
            self.personal_node_stack[char_cid] = NodeStack(length=3)

        if not self.personal_node_stack[char_cid].last_node_is_end(tick):
            """若检测到当前stack中的最新node还未结束，但是SwapCancel还是放行了，那么就说明可能发生了node的顶替，
            此时应该排除是附加伤害的可能性，因为附加伤害是可以被swapcancel轻易放行的，但是并不具备打断的效果。"""
            if not (
                node.skill.labels is not None
                and "additional_damage" in node.skill.labels  # 技能拥有附加标签
            ):
                self.force_change_action(node)
        if self.personal_node_stack[char_cid].is_empty():
            """检测角色的第一个动作抛出。"""
            self.sim_instance.listener_manager.broadcast_event(event=node, enter_battle_event=1)
        self.personal_node_stack[char_cid].push(node)
        if node.active_generation:
            self.latest_active_generation_node = node
        if self.quick_assist_system is None:
            self.quick_assist_system = QuickAssistSystem(
                self.char_data.char_obj_list, sim_instance=self.sim_instance
            )
        self.quick_assist_system.update(tick, node, self.load_data.all_name_order_box)
        if self.atk_manager.attacking:
            self.atk_manager.answered_action.append(node)
        from zsim.sim_progress.Preload.APLModule.ActionReplaceManager import (
            ActionReplaceManager,
        )

        action_replace_manager: ActionReplaceManager = (
            self.sim_instance.preload.strategy.apl_engine.apl.action_replace_manager
        )
        action_replace_manager.parry_aid_strategy.update_myself(skill_node=node, tick=tick)

    def check_myself_before_push_node(self):
        """Confirm阶段自检"""
        _active_generation_node_list = []
        for _node in self.preload_action:
            if _node.active_generation:
                _active_generation_node_list.append(_node)
        if len(_active_generation_node_list) > 1:
            raise ValueError(
                f"在一个Tick中检测到了多个主动技能！共有：{_active_generation_node_list}"
            )

    def get_on_field_node(self, tick: int) -> SkillNode | None:
        """获取当前的前台技能"""
        return self.current_node_stack.get_on_field_node(tick)

    def chek_myself_before_start_preload(self, enemy, tick):
        """Preload阶段自检"""
        if self.preload_action:
            print(f"尚未被Load阶段处理的技能：{self.preload_action}")
        enemy.stun_judge(tick)

    def external_add_skill(self, skill_tuple: tuple[str, bool, int]):
        """外部Buff向下一个Tick添加技能的接口，通常用于协同攻击"""
        skill_tag, active_generation, apl_priority = skill_tuple
        self.preload_action_list_before_confirm.append(skill_tuple)

    def reset_myself(self, name_box):
        """重置preload_data"""
        self.preload_action = []  # 最终return返回给外部申请的数据结构
        for cid, stack in self.personal_node_stack.items():
            stack.reset()
        self.current_node_stack.reset()
        self.latest_active_generation_node = None
        self.preload_action_list_before_confirm = []
        self.name_box = name_box

    def force_change_action(self, skill_node: SkillNode):
        """强制更新动作，用于技能强制顶替、被打断或是类似场合"""
        char_cid = int(skill_node.skill_tag.strip().split("_")[0])
        node_be_changed: SkillNode = self.personal_node_stack[char_cid].peek()
        if node_be_changed.end_tick <= skill_node.preload_tick:
            raise ValueError(
                f"尝试用{skill_node.skill_tag}来强制替换{node_be_changed.skill_tag}，但是后者已经于{node_be_changed.end_tick}结束，这种情况不用调用强制替换方法。请检查调用逻辑。"
            )
        self.delete_mission_in_preload_data(node_be_changed)

        if node_be_changed.skill.do_immediately and "dodge" not in node_be_changed.skill_tag:
            raise ValueError(
                f"{skill_node.skill_tag}正在尝试顶替一个最高优先级的技能：{node_be_changed.skill_tag}"
            )

    def delete_mission_in_preload_data(self, node_be_changed):
        """在PreloadData中强制干涉Load阶段，并且执行特定任务的删除。"""
        mission_key_to_remove = []
        for mission_key, mission in self.load_mission_dict.items():
            from zsim.sim_progress.Load import LoadingMission

            if not isinstance(mission, LoadingMission):
                continue
            if mission.mission_tag == node_be_changed.skill_tag:
                mission.mission_end()
                mission_key_to_remove.append(mission_key)
        for key in mission_key_to_remove:
            self.load_mission_dict.pop(key)
