from .. import Buff, check_preparation
from ..JudgeTools import build_preparation_context_from_buff
from ._preparation_helpers import ensure_owner_template_record, prepare_with_context
from .enemy_edge_state_read import read_enemy_stun_edge_state


class LighterUniqueSkillStunTimeRecord:
    def __init__(self):
        self.last_stun_statement = False
        self.enemy = None


class LighterUniqueSkillStunTimeLimitBonus(Buff.BuffLogic):
    """
    该buff的退出逻辑特殊，失衡结束就会直接退出。
    """

    def __init__(self, buff_instance):
        super().__init__(buff_instance)
        self.buff_instance: Buff = buff_instance
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
            owner_name="莱特",
            record_factory=LighterUniqueSkillStunTimeRecord,
            context_builder=build_preparation_context_from_buff,
        )

    def special_exit_logic(self, **kwargs):
        """
        获取当前失衡值，和上一次失衡值对比。
        """
        self.check_record_module()
        self.get_prepared(enemy=1)

        current_stun = read_enemy_stun_edge_state(self.record.enemy)
        if self.record.last_stun_statement and not current_stun:
            self.record.last_stun_statement = current_stun
            return True
        else:
            self.record.last_stun_statement = current_stun
            return False
