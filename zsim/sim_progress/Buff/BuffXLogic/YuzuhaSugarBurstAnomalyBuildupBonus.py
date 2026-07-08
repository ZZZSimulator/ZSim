from .. import Buff, check_preparation
from ..JudgeTools import build_preparation_context_from_buff
from ._preparation_helpers import ensure_owner_template_record, prepare_with_context


class YuzuhaSugarBurstAnomalyBuildupBonusRecord:
    def __init__(self):
        self.char = None
        self.na_skill_level = None
        self.skill_tag = "1411_SNA_A"
        self.basic_count = 6
        self.count_growth_per_level = 1.5
        self.sub_exist_buff_dict = None


class YuzuhaSugarBurstAnomalyBuildupBonus(Buff.BuffLogic):
    """柚叶自带Buff——彩糖花火积蓄值提升。由于数值和buff等级挂钩所以需要在这里控制层数；"""

    def __init__(self, buff_instance):
        super().__init__(buff_instance)
        self.buff_instance: Buff = buff_instance
        self.xjudge = self.special_judge_logic
        self.xhit = self.special_hit_logic
        self.buff_0 = None
        self.record: YuzuhaSugarBurstAnomalyBuildupBonusRecord | None = None

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
            owner_name="柚叶",
            record_factory=YuzuhaSugarBurstAnomalyBuildupBonusRecord,
            context_builder=build_preparation_context_from_buff,
        )

    def special_judge_logic(self, **kwargs):
        """只放行彩糖花火"""
        self.check_record_module()
        self.get_prepared(char_CID=1411)
        skill_node = kwargs.get("skill_node")
        if skill_node is None:
            return False
        if skill_node.skill_tag != self.record.skill_tag:
            return False
        if skill_node.preload_tick != self.buff_instance.sim_instance.tick:
            return False
        else:
            return True

    def special_hit_logic(self, **kwargs):
        """根据技能等级生成对应层数"""
        self.check_record_module()
        self.get_prepared(char_CID=1411, na_skill_level=1, sub_exist_buff_dict=1)
        self.buff_instance.simple_start(
            timenow=self.buff_instance.sim_instance.tick,
            sub_exist_buff_dict=self.record.sub_exist_buff_dict,
            no_count=1,
        )
        count = (
            self.record.basic_count
            + self.record.na_skill_level * self.record.count_growth_per_level
        )
        self.buff_instance.dy.count = count
        self.buff_instance.update_to_buff_0(buff_0=self.buff_0)
