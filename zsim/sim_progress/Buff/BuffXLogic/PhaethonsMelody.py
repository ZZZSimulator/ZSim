from .. import Buff, check_preparation, find_tick
from ..JudgeTools import build_preparation_context_from_buff
from ._preparation_helpers import ensure_equipper_template_record, prepare_with_context


class PhaethonsMelodyRecord:
    def __init__(self):
        self.equipper = None
        self.char = None


class PhaethonsMelody(Buff.BuffLogic):
    """法厄同之歌的复杂逻辑，以太增伤部分。"""

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
            item_name="法厄同之歌",
            record_factory=PhaethonsMelodyRecord,
            context_builder=build_preparation_context_from_buff,
        )

    def special_judge_logic(self, **kwargs):
        """法厄同之歌的复杂逻辑，监测到非装备者的强化E发动时放行。"""
        self.check_record_module()
        self.get_prepared(equipper="法厄同之歌")
        skill_node = kwargs.get("skill_node", None)
        if skill_node is None:
            return False
        from zsim.sim_progress.Preload import SkillNode

        if not isinstance(skill_node, SkillNode):
            raise TypeError(
                f"{self.buff_instance.ft.index}的xjudge函数获取的skill_node不是SkillNode类！"
            )

        # 滤去自己的技能
        if self.record.equipper == skill_node.char_name:
            return False
        # 过滤非强化E的技能
        if skill_node.skill.trigger_buff_level != 2:
            return False

        tick = find_tick(sim_instance=self.buff_instance.sim_instance)
        if skill_node.preload_tick == tick:
            return True
        return False
