from typing import TYPE_CHECKING

from zsim.sim_progress.Report import report_to_log

from .. import SkillNode, SkillsQueue
from ..PreloadEngine import BasePreloadEngine
from zsim.models.event_enums import ListenerBroadcastSignal as LBS
if TYPE_CHECKING:
    from zsim.sim_progress.Character import Character
    from zsim.sim_progress.Preload.PreloadDataClass import PreloadData


class ConfirmEngine(BasePreloadEngine):
    def __init__(self, data: "PreloadData"):
        """
        这个引擎的主要功能有：
        1、将各环节产生的需要进行Preload的skill_tag，构造成SkillNode，
        2、可行性验证
        3、内部数据交互、更新
        4、外部数据交互、更新
        """
        super().__init__(data)
        self.external_update_signal = False
        self.external_add_skill_list = []
        self.validators = [self._validate_timing]

    def run_myself(self, tick: int, **kwargs):
        """依次执行 Node构造、验证、内外部数据交互"""
        apl_skill_node: SkillNode | None = kwargs.get("apl_skill_node", None)
        apl_skill_tag = kwargs.get("apl_skill_tag", None)
        if apl_skill_node is None and apl_skill_tag != "wait":
            raise ValueError("ConfirmEngine 并未获取到 APL Skill Node，请检查输入")
        for i in range(len(self.data.preload_action_list_before_confirm)):
            tuples = self.data.preload_action_list_before_confirm.pop()
            #  1、创建node
            node = self.spawn_node_from_tag(tick, tuples, template_node_from_apl=apl_skill_node)
            #  2、可行性验证
            if self.validate_node_execution(node, tick):
                # 3、内部数据交互
                self.data.push_node_in_swap_cancel(node, tick)
                report_to_log(f"[PRELOAD]:In tick: {tick}, {node.skill_tag} has been preloaded")
                # 4、外部数据交互
                self.update_external_data(node, tick)
                # print(f'{node.skill_tag}通过了可行性验证，该主动动作来自于优先级为{node.apl_priority}的APL代码')
                # if any(
                #     [_subtags in node.skill_tag for _subtags in ["knock_back", "parry"]]
                # ):
                #     print(
                #         f"{node.skill_tag}被ConfirmEngine接收，它将从{node.preload_tick}开始，于{node.end_tick}结束。"
                #     )
            else:
                pass

    def spawn_node_from_tag(
        self,
        tick: int,
        tuples: tuple[str, bool, int],
        template_node_from_apl: SkillNode | None = None,
    ):
        """通过skill_tag构造Node"""
        skill_tag = tuples[0]
        active_generation = tuples[1] if tuples[1] else False
        if template_node_from_apl and skill_tag == template_node_from_apl.skill_tag:
            apl_unit = template_node_from_apl.apl_unit
        else:
            apl_unit = None
        node = SkillsQueue.spawn_node(
            skill_tag,
            tick,
            self.data.skills,
            active_generation=active_generation,
            apl_priority=tuples[2],
            apl_unit=apl_unit,
        )
        return node

    def update_external_data(self, node: SkillNode, tick: int):
        """与外部数据交互，主要是和char进行交互。"""
        for char in self.data.char_data.char_obj_list:
            char.update_sp_and_decibel(node)
            char.special_resources(node, tick=tick)
            char.dynamic.lasting_node.update_node(node, tick)
        # 切人逻辑
        name_box = self.data.name_box
        if (
            isinstance(name_box, list)
            and all(isinstance(name, str) for name in name_box)
            and node.active_generation
        ):
            self.switch_char(node, self.data.char_data)
        self.data.sim_instance.decibel_manager.update(skill_node=node)

    def switch_char(self, this_node: SkillNode, char_data) -> None:
        name_box = self.data.name_box
        old_name_box = name_box.copy()
        name_index = name_box.index(this_node.char_name)
        # 更改前台角色（切人逻辑）
        if name_index == 1:
            name_switch = name_box.pop(0)
            name_box.append(name_switch)
        elif name_index == 2:
            name_switch = name_box.pop(0)
            name_box.append(name_switch)
            name_switch = name_box.pop(0)
            name_box.append(name_switch)
        for char in char_data.char_obj_list:
            char: "Character"
            if name_box[0] == char.NAME:
                if name_box[0] != old_name_box[0]:
                    """在更新name_box的时候，将切人事件对所有监听器进行广播。"""
                    self.data.sim_instance.listener_manager.broadcast_event(
                        event=char, signal=LBS.SWITCHING_IN, skill_node=this_node
                    )
                    char.dynamic.on_field = True
            else:
                char.dynamic.on_field = False

    def validate_node_execution(self, node: SkillNode, tick: int) -> bool:
        """集中验证节点可执行性"""
        # watchdog.watch_reverse_order(node, self.data.personal_node_stack.peek())
        result = all(validator(node, tick) for validator in self.validators)
        return result

    @staticmethod
    def _validate_timing(node: SkillNode, tick: int) -> bool:
        """检验preload_tick的封装是否有问题，"""
        results = node.preload_tick <= tick
        if not results:
            print(
                f"Preload Tick的可行性验证未通过！应在{node.preload_tick}tick preload的{node.skill_tag}技能过早的在confirm引擎中出现！"
            )
        return node.preload_tick <= tick
