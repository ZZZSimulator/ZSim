from .. import Buff, check_preparation
from ..JudgeTools import build_preparation_context_from_buff
from ._preparation_helpers import ensure_owner_template_record, prepare_with_context


class NicoleCoreSkillRecord:
    def __init__(self):
        self.action_stack = None
        self.char = None
        self.enemy = None
        self.dynamic_buff_list = None
        self.sub_exist_buff_dict = None


class NicoleCoreSkillDefReduction(Buff.BuffLogic):
    def __init__(self, buff_instance):
        """
        妮可的核心被动，减防。
        """
        super().__init__(buff_instance)
        self.buff_instance: Buff = buff_instance
        self.buff_0 = None
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
            owner_name="妮可",
            record_factory=NicoleCoreSkillRecord,
            context_builder=build_preparation_context_from_buff,
        )

    def special_judge_logic(self, **kwargs):
        """
        目前这个buff的触发条件是简化过的。本来应该是检测“强化子弹”
        """
        self.check_record_module()
        self.get_prepared(action_stack=1)
        if self.record.action_stack.peek().mission_tag == "1211_SNA_1":
            return False
        else:
            return True
