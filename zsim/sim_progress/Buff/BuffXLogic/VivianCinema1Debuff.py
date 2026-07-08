from zsim.sim_progress.Dot.runtime_state import DotRuntimeStateAdapter

from .. import Buff, check_preparation
from ..JudgeTools import build_preparation_context_from_buff
from ._preparation_helpers import ensure_owner_template_record, prepare_with_context


class VVivianCinema1DebuffRecord:
    def __init__(self):
        self.char = None
        self.enemy = None


class VivianCinema1Debuff(Buff.BuffLogic):
    def __init__(self, buff_instance):
        """薇薇安1画的负面效果判定逻辑"""
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
            owner_name="薇薇安",
            record_factory=VVivianCinema1DebuffRecord,
            context_builder=build_preparation_context_from_buff,
        )

    def special_judge_logic(self, **kwargs):
        """检测到敌人身上有薇薇安的预言Dot就放行"""
        self.check_record_module()
        self.get_prepared(char_CID=1331, enemy=1)
        dot_runtime_state = DotRuntimeStateAdapter.from_enemy(self.record.enemy)
        if dot_runtime_state.find_active_by_index("ViviansProphecy") is not None:
            return True
        else:
            return False
