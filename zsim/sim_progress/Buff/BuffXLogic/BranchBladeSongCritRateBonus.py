from .. import Buff, JudgeTools, check_preparation
from ..JudgeTools import build_preparation_context_from_buff
from ._preparation_helpers import ensure_equipper_template_record, prepare_with_context
from .enemy_edge_state_read import read_enemy_frozen_edge_state


class BranchBladeSongCritRateBonusRecord:
    def __init__(self):
        self.enemy = None
        self.equipper = None
        self.main_module = None
        self.char = None
        self.last_tick_freez_statement = 0, False


class BranchBladeSongCritRateBonus(Buff.BuffLogic):
    def __init__(self, buff_instance):
        """
        该buff是新冰4的第二特效，需要检测冻结和碎冰效果。
        也就是enemy.dynamic.frozen的状态，只要发生改变，就可以触发。

        """
        super().__init__(buff_instance)
        self.buff_instance: Buff = buff_instance
        # 初始化特定逻辑
        self.xjudge = self.special_judge_logic
        self.equipper = None
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
        ensure_equipper_template_record(
            self,
            item_name="折枝剑歌",
            record_factory=BranchBladeSongCritRateBonusRecord,
            context_builder=build_preparation_context_from_buff,
        )

    def special_judge_logic(self, **kwargs):
        self.check_record_module()
        self.get_prepared(equipper="折枝剑歌", enemy=1)
        tick = JudgeTools.find_tick(sim_instance=self.buff_instance.sim_instance)
        this_tick_freez_statement = read_enemy_frozen_edge_state(self.record.enemy)
        if this_tick_freez_statement != self.record.last_tick_freez_statement[1]:
            self.record.last_tick_freez_statement = tick, this_tick_freez_statement
            return True
        else:
            self.record.last_tick_freez_statement = tick, this_tick_freez_statement
            return False
