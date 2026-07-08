from .. import Buff
from ..JudgeTools import build_preparation_context_from_buff


class IceJadeTeaPotExtraDMGBonus(Buff.BuffLogic):
    """
    青衣专武>=15层时的额外增伤触发判定。
    """

    def __init__(self, buff_instance):
        super().__init__(buff_instance)
        self.buff_instance: Buff = buff_instance
        self.xjudge = self.special_judge_logic

    def special_judge_logic(self, **kwargs):
        preparation_context = build_preparation_context_from_buff(self.buff_instance)
        equipper = preparation_context.find_equipper("玉壶青冰")
        for buffs in preparation_context.find_active_buffs(equipper):
            if "玉壶青冰-普攻加冲击" not in buffs.ft.index:
                continue
            if buffs.dy.count >= 15:
                return True
            else:
                return False
