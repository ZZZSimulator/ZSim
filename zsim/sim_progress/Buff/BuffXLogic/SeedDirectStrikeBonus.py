# 这是席德明攻Buff的脚本
from .. import Buff, check_preparation
from ..JudgeTools import build_preparation_context_from_buff
from ._buff_record_base_class import BuffRecordBaseClass as BRBC
from ._preparation_helpers import ensure_owner_template_record, prepare_with_context


class SeedDirectStrikeBonusRecord(BRBC):
    def __init__(self):
        super().__init__()
        self.buff_index = "Buff-角色-席德-明攻"


class SeedDirectStrikeBonus(Buff.BuffLogic):
    def __init__(self, buff_instance):
        """这是席德明攻Buff的脚本"""
        super().__init__(buff_instance)
        self.buff_instance: Buff = buff_instance
        self.xexit = self.special_exit_logic
        self.buff_0: "Buff | None" = None
        self.record: BRBC | None = None

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
            owner_name="席德",
            record_factory=SeedDirectStrikeBonusRecord,
            context_builder=build_preparation_context_from_buff,
        )

    def special_exit_logic(self, **kwargs):
        self.check_record_module()
        self.get_prepared(char_CID=1461)
        assert self.record is not None, (
            f"【Buff初始化警告】{self.buff_instance.ft.index}的复杂逻辑模块未正确初始化，请检查函数"
        )
        from zsim.sim_progress.Character.Seed import Seed

        seed: Seed = self.record.char
        if seed.vanguard is None:
            # 当席德的没有队友被指定为“正兵”时，明攻永远不可能触发。
            return False
        # 直接运行席德的围攻状态判断函数
        direct_strike = seed.direct_strike_active
        return not direct_strike
