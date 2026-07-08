from zsim.sim_progress.calculation.calculator import (
    create_calculator_runtime_read_context_from_sim_instance,
    get_calculator_buff_attribute_reader_service,
)

from .. import Buff, JudgeTools, check_preparation
from ..JudgeTools import build_preparation_context_from_buff
from ._preparation_helpers import ensure_owner_template_record, prepare_with_context


class TriggerAdditionalAbilityStunBonusRecord:
    def __init__(self):
        self.char = None
        self.sub_exist_buff_dict = None
        self.enemy = None
        self.dynamic_buff_list = None


class TriggerAdditionalAbilityStunBonus(Buff.BuffLogic):
    def __init__(self, buff_instance):
        """扳机的组队被动，根据暴击率提升失衡值。"""
        super().__init__(buff_instance)
        self.buff_instance: Buff = buff_instance
        self.buff_0 = None
        self.record = None
        self.xjudge = self.special_judge_logic
        self.xhit = self.special_hit_logic

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
            owner_name="扳机",
            record_factory=TriggerAdditionalAbilityStunBonusRecord,
            context_builder=build_preparation_context_from_buff,
        )

    def special_judge_logic(self, **kwargs):
        """首先，扳机组队被动的判断逻辑和核心被动没有区别"""
        self.check_record_module()
        self.get_prepared(char_CID=1361)
        from zsim.sim_progress.Preload import SkillNode

        skill_node: SkillNode | None
        skill_node = kwargs.get("skill_node", None)
        if skill_node is None:
            raise ValueError(f"{self.buff_instance.ft.index}的xjudge中缺少skill_node参数")
        if "1361" not in skill_node.skill_tag or not skill_node.skill.labels:
            return False
        if "aftershock_attack" in skill_node.skill.labels.keys():
            return True
        return False

    def special_hit_logic(self, **kwargs):
        """判定通过后，执行Buff激活，计算实时暴击率，替换当前层数。"""
        self.check_record_module()
        self.get_prepared(char_CID=1361, sub_exist_buff_dict=1, enemy=1)
        tick = JudgeTools.find_tick(sim_instance=self.buff_instance.sim_instance)
        context = create_calculator_runtime_read_context_from_sim_instance(
            sim_instance=self.buff_instance.sim_instance,
            enemy=self.record.enemy,
            character=self.record.char,
        )
        reader_service = get_calculator_buff_attribute_reader_service()
        crit_rate = reader_service.read_personal_crit_rate(context)

        """「扳机」的暴击率高于40%时，每超过1%暴击率会使自身发动[追加攻击]造成的失衡值提升1.5%，最多提升75%。"""
        count = min(max(crit_rate - 0.4, 0) / 0.01 * 1.5, 75)
        # print(f'当前暴击率：{crit_rate}, 层数：{count}')

        self.buff_instance.simple_start(tick, self.record.sub_exist_buff_dict, no_count=1)
        self.buff_instance.dy.count = count
        self.buff_instance.update_to_buff_0(self.buff_0)
