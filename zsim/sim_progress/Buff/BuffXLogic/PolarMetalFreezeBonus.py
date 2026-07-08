from .. import Buff, JudgeTools, check_preparation
from ..JudgeTools import build_preparation_context_from_buff
from ._preparation_helpers import ensure_equipper_template_record, prepare_with_context
from .enemy_edge_state_read import EnemyEdgeStateReadPort


class PolarMetalRecord:
    def __init__(self):
        self.last_tick_freez_statement = 0, False
        self.equipper = None
        self.enemy = None
        self.char = None


class PolarMetalFreezeBonus(Buff.BuffLogic):
    """
    这是极地重金属的复杂逻辑判定。
    主要检测的是碎冰的变化状态，如果碎冰状态变了，就返回True
    """

    def __init__(self, buff_instance):
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
            item_name="极地重金属",
            record_factory=PolarMetalRecord,
            context_builder=build_preparation_context_from_buff,
        )

    def special_judge_logic(self, **kwargs):
        self.check_record_module()
        self.get_prepared(enemy=1)
        enemy = self.record.enemy
        tick = JudgeTools.find_tick(sim_instance=self.buff_instance.sim_instance)
        this_tick_freez_statement = EnemyEdgeStateReadPort(enemy).frozen_edge_state()
        if this_tick_freez_statement != self.record.last_tick_freez_statement[1]:
            self.record.last_tick_freez_statement = tick, this_tick_freez_statement
            return True
        else:
            self.record.last_tick_freez_statement = tick, this_tick_freez_statement
            return False
