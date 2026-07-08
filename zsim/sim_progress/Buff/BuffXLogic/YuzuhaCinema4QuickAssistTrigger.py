from typing import TYPE_CHECKING

from zsim.define import YUZUHA_REPORT

from .. import Buff, check_preparation
from ..JudgeTools import build_preparation_context_from_buff
from ._preparation_helpers import ensure_owner_template_record, prepare_with_context

if TYPE_CHECKING:
    from zsim.sim_progress.data_struct.QuickAssistSystem import QuickAssistSystem
    from zsim.sim_progress.Preload import SkillNode


class YuzuhaCinema4QuickAssistTriggerRecord:
    def __init__(self):
        self.char = None
        self.allowed_skill_tag_list = [
            "1411_Assault_Aid",
            "1411_Assault_Aid_A",
            "1411_Assault_Aid_B",
        ]
        self.trigger_skill_node = None


class YuzuhaCinema4QuickAssistTrigger(Buff.BuffLogic):
    def __init__(self, buff_instance):
        super().__init__(buff_instance)
        self.buff_instance: Buff = buff_instance
        self.xjudge = self.special_judge_logic
        self.xhit = self.special_hit_logic
        self.buff_0 = None
        self.record: YuzuhaCinema4QuickAssistTriggerRecord | None = None

    def get_prepared(self, **kwargs):
        return prepare_with_context(
            self,
            check_preparation_func=check_preparation,
            context_builder=build_preparation_context_from_buff,
            **kwargs,
        )

    def check_record_module(self):
        ensure_owner_template_record(
            self,
            owner_name="柚叶",
            record_factory=YuzuhaCinema4QuickAssistTriggerRecord,
            context_builder=build_preparation_context_from_buff,
        )

    def special_judge_logic(self, **kwargs):
        """浮波柚叶的4画触发器——支援突击触发快速支援"""
        self.check_record_module()
        self.get_prepared(char_CID=1411)
        if self.record.trigger_skill_node is not None:
            raise ValueError("【柚叶4画触发器】存在尚未处理的快支触发事件！")
        skill_node: "SkillNode" = kwargs.get("skill_node")
        if skill_node is None:
            return False
        if skill_node.skill_tag not in self.record.allowed_skill_tag_list:
            return False
        tick = self.buff_instance.sim_instance.tick
        if not skill_node.is_last_hit(tick=tick):
            return False
        self.record.trigger_skill_node = skill_node
        return True

    def special_hit_logic(self, **kwargs):
        self.check_record_module()
        self.get_prepared(char_CID=1411)
        sim_instance = self.buff_instance.sim_instance
        QAS: "QuickAssistSystem" = sim_instance.preload.preload_data.quick_assist_system
        target_char_obj = sim_instance.char_data.find_next_char_obj(char_now=1411, direction=1)
        QAS.force_active_quick_assist(
            tick_now=sim_instance.tick,
            skill_node=self.record.trigger_skill_node,
            char_name=target_char_obj.NAME,
        )
        if YUZUHA_REPORT:
            sim_instance.schedule_data.change_process_state()
            print(
                f"【柚叶4画】技能 {self.record.trigger_skill_node.skill_tag} 最后一击命中，并且成功激活了 {target_char_obj.NAME} 的快速支援！"
            )
        self.record.trigger_skill_node = None
