from typing import TYPE_CHECKING

from zsim.define import YUZUHA_REPORT

from .. import Buff, check_preparation
from ..JudgeTools import build_preparation_context_from_buff
from ._preparation_helpers import ensure_owner_template_record, prepare_with_context

if TYPE_CHECKING:
    from zsim.sim_progress.Character.Yuzuha import Yuzuha
    from zsim.sim_progress.Preload import SkillNode


class YuzuhaCinema6SheelTriggerRecord:
    def __init__(self):
        self.char = None
        self.allowed_skill_tag = "1411_Assault_Aid_B"
        self.charging_start = False
        self.charging_tick = 0
        self.sheel_counter = 0


class YuzuhaCinema6SheelTrigger(Buff.BuffLogic):
    """6画的炮弹触发逻辑"""

    def __init__(self, buff_instance):
        super().__init__(buff_instance)
        self.buff_instance: Buff = buff_instance
        self.xjudge = self.special_judge_logic
        self.xeffect = self.special_effect_logic
        self.buff_0 = None
        self.record: YuzuhaCinema6SheelTriggerRecord | None = None

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
            record_factory=YuzuhaCinema6SheelTriggerRecord,
            context_builder=build_preparation_context_from_buff,
        )

    def special_judge_logic(self, **kwargs):
        """模拟蓄力时间"""
        self.check_record_module()
        self.get_prepared(char_CID=1411)
        skill_node: "SkillNode" = kwargs.get("skill_node")
        if skill_node is None:
            return False
        if skill_node.skill_tag != self.record.allowed_skill_tag:
            return False
        tick = self.buff_instance.sim_instance.tick
        lasting_tick = tick - skill_node.preload_tick
        if 0 <= lasting_tick < 24:
            return False
        else:
            self.record.charging_start = True
            if self.record.charging_tick >= 24:
                char: "Yuzuha" = self.record.char
                if char.get_resources()[1] < 1:
                    return False
                else:
                    return True
            else:
                if tick == skill_node.end_tick:
                    self.record.charging_start = False
                    self.record.sheel_counter = 0
                    self.record.charging_tick = 0
                    return False
                self.record.charging_tick += 1
                return False

    def special_effect_logic(self, **kwargs):
        self.check_record_module()
        self.get_prepared(char_CID=1411)

        sim_instance = self.buff_instance.sim_instance
        preload_tick_list = [sim_instance.tick]
        skill_tag_list = ["1411_Cinema_6"]
        preparation_context = build_preparation_context_from_buff(self.buff_instance)
        preparation_context.preload_commands.schedule_preload_events(
            preload_tick_list=preload_tick_list,
            skill_tag_list=skill_tag_list,
        )
        self.record.sheel_counter += 1
        self.record.charging_tick = 0
        if YUZUHA_REPORT:
            sim_instance.schedule_data.change_process_state()
            print(
                f"【柚叶6画】检测到正在›蓄力支援突击，将发射1枚炮弹，这是本次蓄力的第{self.record.sheel_counter}枚"
            )
