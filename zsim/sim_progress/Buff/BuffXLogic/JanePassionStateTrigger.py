from .. import Buff, check_preparation
from ..JudgeTools import build_preparation_context_from_buff
from ._preparation_helpers import ensure_owner_template_record, prepare_with_context


class JanePassionStateTriggerRecord:
    def __init__(self):
        self.char = None


class JanePassionStateTrigger(Buff.BuffLogic):
    def __init__(self, buff_instance):
        """简单的狂热状态触发器"""
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
            owner_name="简",
            record_factory=JanePassionStateTriggerRecord,
            context_builder=build_preparation_context_from_buff,
        )

    def special_judge_logic(self, **kwargs):
        """简的狂热状态触发器，其取值狂热状态同步"""
        self.check_record_module()
        self.get_prepared(char_CID=1261)
        passion_state = self.record.char.get_special_stats().get("狂热状态")
        if passion_state is None:
            raise ValueError(f"{self.buff_instance.ft.index} 的xjudge模块并未获取到简的狂热状态！")
        if passion_state:
            return True
        else:
            return False

    def special_exit_logic(self, **kwargs):
        """简的狂热状态触发器的退出逻辑，和触发函数持相反逻辑"""
        return not self.special_judge_logic()
