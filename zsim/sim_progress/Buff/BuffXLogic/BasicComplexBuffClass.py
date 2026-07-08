from .. import Buff, check_preparation
from ..JudgeTools import build_preparation_context_from_buff
from ._preparation_helpers import ensure_owner_template_record, prepare_with_context


class BaseBuffRecord:
    """基础记录Class"""

    def __init__(self):
        self.char = None
        self.buff_0 = None
        self.exist_buff_dict = None
        self.sub_exist_buff_dict = None
        self.preload_data = None
        self.trigger_buff_0 = None
        self.equipper = None


class BasicComplexBuffClass(Buff.BuffLogic):
    RECORD_CLASS = BaseBuffRecord

    def __init__(self, buff_instance):
        super().__init__(buff_instance)
        self.buff_instance: Buff = buff_instance
        self.buff_0 = None
        self.record = None
        self.xjudge = self.special_judge_logic
        self.xexit = self.special_exit_logic
        self.xhit = self.special_hit_logic
        self.xeffect = self.special_effect_logic

    def get_prepared(self, **kwargs):
        """通用准备检查方法"""
        return prepare_with_context(
            self,
            check_preparation_func=check_preparation,
            context_builder=build_preparation_context_from_buff,
            **kwargs,
        )

    def check_record_module(self, **kwargs):
        """通用记录模块检查"""
        char_name = kwargs.get("char_name", None)
        if char_name is None:
            raise ValueError(
                f"{self.buff_instance.ft.index}在进行初始化时，复杂Buff逻辑中的check_record_module函数中并未传入有效的char_name参数！"
            )
        ensure_owner_template_record(
            self,
            owner_name=char_name,
            record_factory=self.RECORD_CLASS,
            context_builder=build_preparation_context_from_buff,
        )

    def special_judge_logic(self, **kwargs):
        pass

    def special_exit_logic(self, **kwargs):
        pass

    def special_start_logic(self, **kwargs):
        pass

    def special_hit_logic(self, **kwargs):
        pass
