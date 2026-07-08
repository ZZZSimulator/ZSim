from .. import Buff, check_preparation
from ..JudgeTools import build_preparation_context_from_buff
from ._preparation_helpers import ensure_owner_template_record, prepare_with_context


class YanagiStanceKagenRecord:
    def __init__(self):
        self.char = None


class YanagiStanceKagen(Buff.BuffLogic):
    """
    柳的下弦增幅，检测到下弦状态就通过判定
    """

    def __init__(self, buff_instance):
        super().__init__(buff_instance)
        self.buff_instance: Buff = buff_instance
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
            owner_name="柳",
            record_factory=YanagiStanceKagenRecord,
            context_builder=build_preparation_context_from_buff,
        )

    def special_judge_logic(self, **kwargs):
        """
        检测柳的当前状态，如果当前状态为下弦就通过判定。
        """
        self.check_record_module()
        self.get_prepared(char_CID=1221)
        if self.record.char.stance_manager.stance_now:
            return False
        else:
            return True
