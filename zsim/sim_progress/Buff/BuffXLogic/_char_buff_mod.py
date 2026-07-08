from .. import Buff, check_preparation
from ..JudgeTools import build_preparation_context_from_buff
from ._buff_record_base_class import BuffRecordBaseClass as BRBC


class CharBuffXLogicNameRecord(BRBC):
    def __init__(self):
        super().__init__()


class CharBuffXLogicName(Buff.BuffLogic):
    def __init__(self, buff_instance):
        super().__init__(buff_instance)
        self.buff_instance: Buff = buff_instance
        self.xjudge = self.special_judge_logic
        self.buff_0: "Buff | None" = None
        self.record: BRBC | None = None

    def get_prepared(self, **kwargs):
        preparation_context = build_preparation_context_from_buff(self.buff_instance)
        return check_preparation(
            buff_instance=self.buff_instance,
            buff_0=self.buff_0,
            preparation_context=preparation_context,
            **kwargs,
        )

    def check_record_module(self):
        if self.buff_0 is None:
            preparation_context = build_preparation_context_from_buff(self.buff_instance)
            self.buff_0 = preparation_context.find_sub_exist_buff_dict("角色名字")[
                self.buff_instance.ft.index
            ]
        assert self.buff_0 is not None, (
            "【Buff初始化警告】角色名字的复杂逻辑模块未正确初始化，请检查函数"
        )
        if self.buff_0.history.record is None:
            self.buff_0.history.record = CharBuffXLogicNameRecord()
        self.record = self.buff_0.history.record

    def special_judge_logic(self, **kwargs):
        self.check_record_module()
        self.get_prepared(char_CID=0000)
        assert self.record is not None, (
            f"【Buff初始化警告】{self.buff_instance.ft.index}的复杂逻辑模块未正确初始化，请检查函数"
        )
