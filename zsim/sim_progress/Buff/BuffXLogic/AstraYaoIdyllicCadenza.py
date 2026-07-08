from .. import Buff, check_preparation
from ..JudgeTools import build_preparation_context_from_buff
from ._preparation_helpers import ensure_owner_template_record, prepare_with_context


class AstraYaoIdyllicCadenzaRecord:
    def __init__(self):
        self.char = None


class AstraYaoIdyllicCadenza(Buff.BuffLogic):
    def __init__(self, buff_instance):
        """耀嘉音咏叹华彩的加成效果的判定逻辑"""
        super().__init__(buff_instance)
        self.buff_instance: Buff = buff_instance
        self.buff_0 = None
        self.record = None
        self.xjudge = self.special_judge_logic
        self.xexit = self.special_exit_logic

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
            owner_name="耀嘉音",
            record_factory=AstraYaoIdyllicCadenzaRecord,
            context_builder=build_preparation_context_from_buff,
        )

    def special_judge_logic(self, **kwargs):
        """检测咏叹华彩状态"""
        self.check_record_module()
        self.get_prepared(char_CID=1311)
        if self.record.char.get_resources()[1]:
            return True
        else:
            return False

    def special_exit_logic(self, **kwargs):
        return not self.special_judge_logic(**kwargs)
