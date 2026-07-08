from .. import Buff, check_preparation
from ..JudgeTools import build_preparation_context_from_buff
from ._preparation_helpers import ensure_owner_template_record, prepare_with_context


class YanagiCinema6EXDmgBonusRecord:
    def __init__(self):
        self.char = None


class YanagiCinema6EXDmgBonus(Buff.BuffLogic):
    """
    柳的6画，森罗万象激活时，通过判定。
    """

    def __init__(self, buff_instance):
        super().__init__(buff_instance)
        self.buff_instance: Buff = buff_instance
        self.xjudge = self.special_judge_logic
        self.xexit = self.special_exit_logic
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
            record_factory=YanagiCinema6EXDmgBonusRecord,
            context_builder=build_preparation_context_from_buff,
        )

    def special_judge_logic(self, **kwargs):
        """检测当前的森罗万象状态是否开启，若开启则通过判定。"""
        self.check_record_module()
        self.get_prepared(char_CID=1221)
        if self.record.char.get_special_stats()["森罗万象状态"]:
            return True
        else:
            return False

    def special_exit_logic(self, **kwargs):
        return not self.special_judge_logic(**kwargs)
