from zsim.sim_progress.Character.Seed import Seed

from .. import Buff, check_preparation
from ..JudgeTools import build_preparation_context_from_buff
from ._buff_record_base_class import BuffRecordBaseClass as BRBC
from ._preparation_helpers import ensure_owner_template_record, prepare_with_context


class SeedOnslaughtBonusRecord(BRBC):
    def __init__(self):
        super().__init__()


class SeedOnslaughtBonus(Buff.BuffLogic):
    """席德的强袭Buff复杂逻辑"""

    def __init__(self, buff_instance):
        super().__init__(buff_instance)
        self.buff_instance: Buff = buff_instance
        self.xjudge = self.special_judge_logic
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
            record_factory=SeedOnslaughtBonusRecord,
            context_builder=build_preparation_context_from_buff,
        )

    def special_judge_logic(self, **kwargs):
        """席德的强袭状态早就已经记录在席德的特殊资源中了，所以这里不需要重复判断，只需要直接调用方法判断是否生效即可"""
        self.check_record_module()
        self.get_prepared(char_CID=1461)
        assert self.record is not None, (
            f"【Buff初始化警告】{self.buff_instance.ft.index}的复杂逻辑模块未正确初始化，请检查函数"
        )
        assert type(self.record.char) is Seed, (
            f"当前record中的角色不是席德，而是{type(self.record.char).__name__}, CID为：{self.record.char.CID, self.record.char.NAME}"
        )

        return self.record.char.onslaught_active

    def special_exit_logic(self, **kwargs):
        """强袭Buff的退出逻辑和生效逻辑相反，所以这里需要调用席德的方法检测是否退出强袭状态"""
        self.check_record_module()
        self.get_prepared(char_CID=1461)
        assert self.record is not None, (
            f"【Buff初始化警告】{self.buff_instance.ft.index}的复杂逻辑模块未正确初始化，请检查函数"
        )
        return not self.xjudge
