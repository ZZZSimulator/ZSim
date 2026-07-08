from .. import Buff, check_preparation
from ..JudgeTools import build_preparation_context_from_buff
from ._preparation_helpers import ensure_owner_template_record, prepare_with_context


class Soldier0AnbyCoreSkillDMGBonusRecord:
    def __init__(self):
        self.char = None
        self.dynamic_buff_list = None
        self.enemy = None
        self.sub_exist_buff_dict = None
        self.trigger_buff_0 = None


class Soldier0AnbyCoreSkillDMGBonus(Buff.BuffLogic):
    def __init__(self, buff_instance):
        """
        零号·安比的核心被动，银星有层数就触发增伤。
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
            owner_name="零号·安比",
            record_factory=Soldier0AnbyCoreSkillDMGBonusRecord,
            context_builder=build_preparation_context_from_buff,
        )

    def special_judge_logic(self, **kwargs):
        """
        只要是检测到有银星，就返回True
        """
        self.check_record_module()
        self.get_prepared(char_CID=1381)
        if self.record.char.get_resources()[1] > 0:
            return True
        else:
            return False
