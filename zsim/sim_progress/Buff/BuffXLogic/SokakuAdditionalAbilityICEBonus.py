from .. import Buff, check_preparation
from ..JudgeTools import build_preparation_context_from_buff
from ._preparation_helpers import ensure_owner_template_record, prepare_with_context


class SokakuAdditionalAbilityIBRecord:
    def __init__(self):
        self.char = None
        self.action_stack = None
        self.last_update_resource = 0


class SokakuAdditionalAbilityICEBonus(Buff.BuffLogic):
    """
    苍角组队被动：
    消耗涡流发动展旗时激活
    """

    def __init__(self, buff_instance):
        super().__init__(buff_instance)
        self.buff_instance: Buff = buff_instance
        # 初始化特定逻辑
        self.xjudge = self.special_judge_logic
        self.buff_0 = None
        self.record = None

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
            owner_name="苍角",
            record_factory=SokakuAdditionalAbilityIBRecord,
            context_builder=build_preparation_context_from_buff,
        )

    def special_judge_logic(self, **kwargs):
        self.check_record_module()
        self.get_prepared(char_CID=1131, action_stack=1)
        action_now = self.record.action_stack.peek()
        resource_now = self.record.char.get_resources()[1]
        if action_now.mission_tag != "1131_E_EX_A":
            return False
        if self.record.last_update_resource <= resource_now:
            self.record.last_update_resource = resource_now
            return False
        else:
            self.record.last_update_resource = resource_now
            return True
