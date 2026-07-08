from zsim.define import HUGO_REPORT

from .. import Buff, check_preparation
from ..JudgeTools import build_preparation_context_from_buff
from ._preparation_helpers import ensure_owner_template_record, prepare_with_context


class HugoCorePassiveDoubleStunAtkBonusRecord:
    def __init__(self):
        self.char = None
        self.stun_char_count = None
        self.char_obj_list = None


class HugoCorePassiveDoubleStunAtkBonus(Buff.BuffLogic):
    def __init__(self, buff_instance):
        """雨果核心被动，双击破角色的攻击力加成"""
        super().__init__(buff_instance)
        self.buff_instance: Buff = buff_instance
        self.buff_0: Buff | None = None
        self.record = None
        self.xjudge = self.special_judge_logic

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
            owner_name="雨果",
            record_factory=HugoCorePassiveDoubleStunAtkBonusRecord,
            context_builder=build_preparation_context_from_buff,
        )

    def special_judge_logic(self, **kwargs):
        """当队伍里存在2名被击角色时，触发该效果"""
        self.check_record_module()
        self.get_prepared(char_CID=1291, char_obj_list=1)
        if self.record.stun_char_count is None:
            self.record.stun_char_count = 0
            for char_obj in self.record.char_obj_list:
                from zsim.sim_progress.Character import Character

                if not isinstance(char_obj, Character):
                    raise TypeError("char_obj_list中的对象不是Character类的实例")
                if char_obj.specialty == "击破":
                    self.record.stun_char_count += 1
            if HUGO_REPORT:
                self.buff_instance.sim_instance.schedule_data.change_process_state()
                print(
                    f"雨果的双击破角色攻击力Buff在初始化阶段检测到了队伍中有{self.record.stun_char_count}名击破角色"
                )

        stun_char_count = self.record.stun_char_count
        if stun_char_count >= 2:
            return True
        return False
