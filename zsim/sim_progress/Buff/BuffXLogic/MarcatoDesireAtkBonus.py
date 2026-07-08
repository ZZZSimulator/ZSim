from .. import Buff, check_preparation, find_tick
from ..JudgeTools import build_preparation_context_from_buff
from ._preparation_helpers import ensure_equipper_template_record, prepare_with_context
from .enemy_anomaly_read import read_enemy_anomaly_active


class MarcatoDesireRecord:
    def __init__(self):
        self.equipper = None
        self.char = None
        self.enemy = None


class MarcatoDesireAtkBonus(Buff.BuffLogic):
    """强音热望的复杂逻辑：连携技或强化E命中属性异常状态下敌人时触发"""

    def __init__(self, buff_instance):
        super().__init__(buff_instance)
        self.buff_instance: Buff = buff_instance
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
            item_name="强音热望",
            record_factory=MarcatoDesireRecord,
            context_builder=build_preparation_context_from_buff,
        )

    def special_judge_logic(self, **kwargs):
        self.check_record_module()
        self.get_prepared(equipper="强音热望", enemy=1)
        skill_node = kwargs.get("skill_node", None)
        if skill_node is None:
            return False
        from zsim.sim_progress.Preload import SkillNode

        if not isinstance(skill_node, SkillNode):
            raise ValueError(
                f"{self.buff_instance.ft.index}的Xjudge函数获取的skill_node不是SkillNode类型！"
            )
        prepared_char_name = (
            self.record.char.NAME if self.record.char is not None else self.record.equipper
        )
        if skill_node.char_name != prepared_char_name:
            return False
        if not skill_node.is_hit_now(find_tick(sim_instance=self.buff_instance.sim_instance)):
            return False
        if skill_node.skill.trigger_buff_level in [2, 5]:
            if read_enemy_anomaly_active(self.record.enemy):
                return True
        return False
