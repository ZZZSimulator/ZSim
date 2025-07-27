import math
from typing import TYPE_CHECKING

from zsim.define import ASTRAYAO_REPORT
from zsim.sim_progress.Buff import JudgeTools
from zsim.sim_progress.data_struct import schedule_preload_event_factory
from zsim.sim_progress.Preload.PreloadDataClass import PreloadData

from .character import Character
from .utils.filters import _skill_node_filter

if TYPE_CHECKING:
    from zsim.sim_progress.Preload import SkillNode


class AstraYao(Character):
    """耀佳音的特殊资源模块"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.idyllic_cadenza = False  # 咏叹华彩状态
        self.chord_manager = ChordCoattackManager(self)

    @property
    def chord(self) -> int:
        """每拥有25点能量，耀嘉音将拥有1点[和弦]"""
        return math.floor(self.sp / 25)

    class Dynamic(Character.Dynamic):
        """
        这里的所有修改，是为了让on_field属性能够完美适配咏叹华彩状态，
        当咏叹华彩状态为True时，on_field属性永远返回True，
        而当它为False时，on_field属性返回存储的值。
        """

        def __init__(self, char_instantce: Character):
            super().__init__(char_instantce)
            self.character: "AstraYao" = char_instantce  # type: ignore
            self._on_field = False  # 初始化父类的普通属性

        @property
        def on_field(self):
            """重写on_field属性，根据咏叹华彩状态返回不同值"""
            if self.character.idyllic_cadenza:  # 如果咏叹华彩状态为True
                return True
            return self._on_field  # 否则返回存储的值

        @on_field.setter
        def on_field(self, value):
            """保留设置功能"""
            self._on_field = value

    def __update_idyllic_cadenza(self, skill_node: "SkillNode") -> None:
        """更新咏叹华彩状态"""
        if skill_node.skill_tag in ["1311_E_A", "1311_QTE", "1311_Q"]:
            self.idyllic_cadenza = True
        elif "1311_NA_3" in skill_node.skill_tag:
            self.idyllic_cadenza = False

    def special_resources(self, *args, **kwargs) -> None:
        # 输入类型检查
        skill_nodes: list["SkillNode"] = _skill_node_filter(*args, **kwargs)
        for node in skill_nodes:
            self.__update_idyllic_cadenza(node)
            pass

    def get_resources(self) -> tuple[str, int]:
        return "咏叹华彩", self.idyllic_cadenza

    def get_special_stats(self, *args, **kwargs) -> dict[str | None, object | None]:
        return {"和弦": self.chord}


"""================================分割线=================================="""


class ChordCoattackManager:
    def __init__(self, char_instance: AstraYao):
        self.char = char_instance
        self.quick_assist_trigger_manager = self.QuickAssistTriggerManager(self.char)
        self.chord_trigger = self.ChordTrigger(self)

    class QuickAssistTriggerManager:
        """快速支援管理器"""

        def __init__(self, char_instance: AstraYao):
            self.char = char_instance
            self.light_attack_trigger = self.BaseSingleTrigger(
                self, cd=180 if self.char.cinema < 4 else 60
            )
            self.heavy_attack_trigger = self.BaseSingleTrigger(self, cd=60)
            self.found_char_dict: dict[str, Character] = {}
            self.preload_data: PreloadData | None = None

        def update_myself(self, tick: int, event):
            """这个函数的作用是更新自身状态，并且尝试触发轻、重两种快速支援触发器。"""
            from zsim.sim_progress.Load import LoadingMission
            from zsim.sim_progress.Preload import SkillNode

            if isinstance(event, LoadingMission):
                skill_node = event.mission_node
            elif isinstance(event, SkillNode):
                skill_node = event
            else:
                return

            # 处理loading_mission为None的情况
            if skill_node.loading_mission is None:
                skill_node.loading_mission = LoadingMission(skill_node)
                skill_node.loading_mission.mission_start(tick, report=False)

            # # 检查当前tick是否为命中tick
            # if not skill_node.loading_mission.is_hit_now(tick):
            #     raise ValueError(
            #         f"在非命中tick {tick} 上调用了耀嘉音快支管理器中的update_myself方法，当前的命中tick列表为：{skill_node.loading_mission.mission_dict}"
            #     )

            # 根据轻重攻击情况触发快速支援
            if skill_node.loading_mission.is_heavy_hit(tick):
                self.heavy_attack_trigger.try_active(tick, skill_node)
            else:
                self.light_attack_trigger.try_active(tick, skill_node)

        class BaseSingleTrigger:
            """单个触发器类"""

            def __init__(self, manager_instance, cd: int):
                self.manager: ChordCoattackManager.QuickAssistTriggerManager = manager_instance
                self.cd = cd
                self.last_update_tick = 0

            def is_ready(self, tick: int):
                if self.last_update_tick == 0:
                    return True
                if tick - self.last_update_tick >= self.cd:
                    return True
                else:
                    return False

            def determine_target_char(self, tick: int):
                """
                根据当前角色和角色顺序确定目标角色，这里需要分两种情况讨论：
                1、下一个角色是耀嘉音——跳过耀嘉音，直接触发下下位角色的快速支援，
                2、下一个角色不是耀嘉音——正常触发下一位角色的快速支援。
                """
                assert self.manager.preload_data is not None, "preload_data is not initialized"
                _operating_node = self.manager.preload_data.get_on_field_node(tick)
                all_name_order_box = self.manager.preload_data.load_data.all_name_order_box
                if _operating_node is None:
                    raise ValueError("想要触发耀嘉音的快速支援，则当前场上必须存在角色！")
                current_name_order = all_name_order_box[_operating_node.char_name]

                if current_name_order[1] == "耀嘉音":
                    target = current_name_order[2]
                else:
                    target = current_name_order[1]
                # print(_operating_node.skill_tag, current_name_order, target)
                return target

            def __active(self, tick: int, skill_node):
                """触发快速支援！不包含CD判断，只包含触发逻辑。"""
                if self.manager.preload_data is None:
                    if self.manager.char.sim_instance is None:
                        raise ValueError("sim_instance is None, cannot find preload_data")
                    self.manager.preload_data = JudgeTools.find_preload_data(
                        sim_instance=self.manager.char.sim_instance
                    )
                    if not isinstance(self.manager.preload_data, PreloadData):
                        raise TypeError("快速支援管理器无法找到PreloadData实例！")
                self.last_update_tick = tick
                target_char = self.determine_target_char(tick)
                assert self.manager.preload_data.quick_assist_system is not None
                self.manager.preload_data.quick_assist_system.force_active_quick_assist(
                    tick, skill_node, target_char
                )

            def try_active(self, tick: int, skill_node):
                """尝试触发快速支援！这是给外部调用的接口。"""
                if self.manager.char.chord < 1 or not self.manager.char.idyllic_cadenza:
                    """当耀嘉音的和弦数量不足、或不处于唱歌状态时，不予触发！"""
                    return False

                if not self.is_ready(tick):
                    return
                self.__active(tick, skill_node)

    class ChordTrigger:
        def __init__(self, manager_instance):
            self.manager: ChordCoattackManager = manager_instance
            self.preload_data: PreloadData | None = None
            # 震音：Tremolo；音簇：Tone Clusters
            self.tremolo_tick = 35  # 震音的总时长
            self.tone_clusters_tick = 50  # 音簇的总时长
            self.coattack_base_count = (
                1 if not self.manager.char.additional_abililty_active else 2
            )  # 震音的基础轮次
            self.c2_update_tick = 0
            self.c2_trigger_cd = 180
            self.core_passive_buff_index = "Buff-角色-耀佳音-核心被动-攻击力"
            self.last_chord_update_tick = 0  # 上一次调用和弦构造函数的时间点！
            self.tremolo_tag = "1311_E_EX_A"
            self.free_tremolo_tag = "1311_E_EX_A_FREE"
            self.tone_clusters_tag = "1311_E_EX_C"

        def c2_ready(self, tick: int):
            return tick - self.c2_update_tick >= self.c2_trigger_cd

        def try_spawn_chord_coattack(self, tick: int, skill_node: "SkillNode | None"):
            """给外部的接口，尝试执行！"""
            if self.manager.char.sp < 25:
                return
            self.coattack_active(tick, skill_node)

        def coattack_active(self, tick: int, skill_node: "SkillNode | None"):
            """
            给外部函数调用的接口，用于生成协同攻击。
            如果有顺带传入skill_node参数，则意味着调用来自Buff系统的触发器，
            此时，协同攻击预载行为往往伴随着耀嘉音核心被动攻击力Buff的刷新。
            """
            c2_count = 1 if self.manager.char.cinema >= 2 else 0
            loop_times = self.coattack_base_count + c2_count
            self.__chord_group_spawn_loop(tick, loop_times)
            if skill_node is not None:
                self.__add_core_passive_buff(skill_node)

        def __chord_group_spawn_loop(self, tick: int, loop_times: int):
            """
            用于抛出成组的和弦攻击，每组动作包含1次震音、3次音簇。
            并且可以进行重复执行，模仿耀嘉音技能模组中，多次触发的情况。
            """
            if self.preload_data is None:
                if self.manager.char.sim_instance is None:
                    raise ValueError("sim_instance is None, cannot find preload_data")
                self.preload_data = JudgeTools.find_preload_data(
                    sim_instance=self.manager.char.sim_instance
                )
                if not isinstance(self.preload_data, PreloadData):
                    raise TypeError("和弦管理器无法找到PreloadData实例！")
            priority_list = [-1, -1]
            preload_tick = tick
            for i in range(loop_times):
                if i == 2:
                    if self.c2_ready(tick):
                        self.c2_update_tick = tick
                    else:
                        """针对2画，这里需要注意内置CD的判断"""
                        continue
                if i == 0:
                    skill_tag_list = [self.tremolo_tag, self.tone_clusters_tag]
                else:
                    skill_tag_list = [self.free_tremolo_tag, self.tone_clusters_tag]
                skill_preload_tick_list = [
                    preload_tick,
                    preload_tick + self.tremolo_tick,
                ]
                preload_tick += self.tremolo_tick + self.tone_clusters_tick
                if self.manager.char.sim_instance is None:
                    raise ValueError("sim_instance is None, cannot schedule event")
                schedule_preload_event_factory(
                    skill_tag_list=skill_tag_list,
                    preload_tick_list=skill_preload_tick_list,
                    preload_data=self.preload_data,
                    apl_priority_list=priority_list,
                    sim_instance=self.manager.char.sim_instance,
                )

        def __add_core_passive_buff(self, skill_node: "SkillNode"):
            """在触发第一次震音的时刻，也会给角色上Buff"""
            add_buff_list = [self.manager.char.NAME] + [skill_node.char_name]
            benifit_list = list(set(add_buff_list))
            from zsim.sim_progress.Buff.BuffAddStrategy import buff_add_strategy

            if self.manager.char.sim_instance is None:
                raise ValueError("sim_instance is None, cannot add buff")

            buff_add_strategy(
                self.core_passive_buff_index,
                benifit_list=benifit_list,
                sim_instance=self.manager.char.sim_instance,
            )
            if ASTRAYAO_REPORT:
                assert self.manager.char.sim_instance is not None
                self.manager.char.sim_instance.schedule_data.change_process_state()
                print(f"核心被动触发器激活！为{benifit_list}添加了{self.core_passive_buff_index}！")
