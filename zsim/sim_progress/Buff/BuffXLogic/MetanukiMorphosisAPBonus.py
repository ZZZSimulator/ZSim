from .. import Buff, JudgeTools, check_preparation
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from zsim.sim_progress.Preload import SkillNode


class MetanukiMorphosisAPBonusRecord:
    def __init__(self):
        self.equipper = None
        self.char = None


class MetanukiMorphosisAPBonus(Buff.BuffLogic):
    def __init__(self, buff_instance):
        super().__init__(buff_instance)
        self.buff_instance: Buff = buff_instance
        self.xjudge = self.special_judge_logic
        self.equipper = None
        self.buff_0 = None
        self.record: MetanukiMorphosisAPBonusRecord | None = None

    def get_prepared(self, **kwargs):
        return check_preparation(buff_instance=self.buff_instance, buff_0=self.buff_0, **kwargs)

    def check_record_module(self):
        if self.equipper is None:
            self.equipper = JudgeTools.find_equipper(
                "狸法七变化", sim_instance=self.buff_instance.sim_instance
            )
        if self.buff_0 is None:
            self.buff_0 = JudgeTools.find_exist_buff_dict(
                sim_instance=self.buff_instance.sim_instance
            )[self.equipper][self.buff_instance.ft.index]
        if self.buff_0.history.record is None:
            self.buff_0.history.record = MetanukiMorphosisAPBonusRecord()
        self.record = self.buff_0.history.record

    def special_judge_logic(self, **kwargs):
        """检测到装备者的追加攻击时放行，但是需要注意此效果只能生效一个"""
        self.check_record_module()
        self.get_prepared(equipper="狸法七变化")
        skill_node: "SkillNode" = kwargs.get("skill_node")
        if skill_node is None:
            return False
        if skill_node.char_name != self.record.char.NAME:
            return False
        if not skill_node.have_label(label_key="aftershock_attack"):
            return False
        if skill_node.is_hit_now(tick=self.buff_instance.sim_instance.tick):
            return True
        else:
            return False
