from typing import TYPE_CHECKING

from .. import Buff, JudgeTools, check_preparation

if TYPE_CHECKING:
    from zsim.sim_progress.Preload import SkillNode


class PuzzleSphereExDmgBonusRecord:
    def __init__(self):
        self.equipper = None
        self.char = None
        self.enemy = None


class PuzzleSphereExDmgBonus(Buff.BuffLogic):
    def __init__(self, buff_instance):
        super().__init__(buff_instance)
        self.buff_instance: Buff = buff_instance
        self.xjudge = self.special_judge_logic
        self.equipper = None
        self.buff_0 = None
        self.record = None

    def get_prepared(self, **kwargs):
        return check_preparation(buff_instance=self.buff_instance, buff_0=self.buff_0, **kwargs)

    def check_record_module(self):
        if self.equipper is None:
            self.equipper = JudgeTools.find_equipper(
                "幻变魔方", sim_instance=self.buff_instance.sim_instance
            )
        if self.buff_0 is None:
            self.buff_0 = JudgeTools.find_exist_buff_dict(
                sim_instance=self.buff_instance.sim_instance
            )[self.equipper][self.buff_instance.ft.index]
        if self.buff_0.history.record is None:
            self.buff_0.history.record = PuzzleSphereExDmgBonusRecord()
        self.record = self.buff_0.history.record

    def special_judge_logic(self, **kwargs):
        """幻变魔方的特殊判定逻辑，强化E发动时，若敌人的血量高于50%，则放行。"""
        self.check_record_module()
        self.get_prepared(equipper="幻变魔方", enemy=1)
        skill_node: "SkillNode | None" = kwargs.get("skill_node", None)
        if skill_node is None:
            return False
        if skill_node.char_name != self.record.char.NAME:
            return False
        if skill_node.skill.trigger_buff_level != 2:
            return False
        if self.record.enemy.get_current_hp_percentage() < 0.5:
            return False
        return True
