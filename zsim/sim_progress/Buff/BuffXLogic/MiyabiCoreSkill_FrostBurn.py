from .. import Buff, check_preparation
from ..JudgeTools import build_preparation_context_from_buff, detect_edge
from ._preparation_helpers import ensure_owner_template_record, prepare_with_context
from .enemy_edge_state_read import read_enemy_frost_frostbite_edge_state


class MiyabiCoreSkillFB:
    def __init__(self):
        self.last_frostbite = False
        self.enemy = None


class MiyabiCoreSkill_FrostBurn(Buff.BuffLogic):
    """
    该buff是雅的核心被动中的【霜灼】，【霜灼】的进入机制是，随着烈霜属性异常触发，同步触发。
    执行这一步的是：update_anomaly函数，该函数会在烈霜属性积蓄条满的时候，
    根据bar.accompany_debuff中记录的str，去添加同名debuff。
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
            owner_name="雅",
            record_factory=MiyabiCoreSkillFB,
            context_builder=build_preparation_context_from_buff,
        )

    def special_exit_logic(self, **kwargs):
        """
        霜灼buff的退出机制是检测到霜寒的下降沿就退出
        """
        self.check_record_module()
        self.get_prepared(enemy=1)
        frostbite_now = read_enemy_frost_frostbite_edge_state(self.record.enemy)
        frostbite_statement = [self.record.last_frostbite, frostbite_now]

        def mode_func(a, b):
            return a is True and b is False

        result = detect_edge(frostbite_statement, mode_func)
        self.record.last_frostbite = frostbite_now
        return result
