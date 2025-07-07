from zsim.sim_progress.ScheduledEvent import Calculator
from zsim.sim_progress.ScheduledEvent.Calculator import MultiplierData

from .. import Buff, JudgeTools, check_preparation, find_tick


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
        return check_preparation(
            buff_instance=self.buff_instance, buff_0=self.buff_0, **kwargs
        )

    def check_record_module(self):
        if self.buff_0 is None:
            self.buff_0 = JudgeTools.find_exist_buff_dict(
                sim_instance=self.buff_instance.sim_instance
            )["扳机"][self.buff_instance.ft.index]
        if self.buff_0.history.record is None:
            self.buff_0.history.record = TriggerAdditionalAbilityStunBonusRecord()
        self.record = self.buff_0.history.record

    def special_judge_logic(self, **kwargs):
        """首先，扳机组队被动的判断逻辑和核心被动没有区别"""
        self.check_record_module()
        self.get_prepared(char_CID=1361)
        from zsim.sim_progress.Preload import SkillNode

        skill_node: SkillNode | None
        skill_node = kwargs.get("skill_node", None)
        if skill_node is None:
            raise ValueError(
                f"{self.buff_instance.ft.index}的xjudge中缺少skill_node参数"
            )
        if "1361" not in skill_node.skill_tag or not skill_node.skill.labels:
            return False
        if "aftershock_attack" in skill_node.skill.labels.keys():
            return True
        return False

    def special_hit_logic(self, **kwargs):
        """判定通过后，执行Buff激活，计算实时暴击率，替换当前层数。"""
        self.check_record_module()
        self.get_prepared(
            char_CID=1361, sub_exist_buff_dict=1, enemy=1, dynamic_buff_list=1
        )
        tick = find_tick(sim_instance=self.buff_instance.sim_instance)
        mul_data = MultiplierData(
            self.record.enemy, self.record.dynamic_buff_list, self.record.char
        )
        crit_rate = Calculator.RegularMul.cal_personal_crit_rate(mul_data)

        """「扳机」的暴击率高于40%时，每超过1%暴击率会使自身发动[追加攻击]造成的失衡值提升1.5%，最多提升75%。"""
        count = min(max(crit_rate - 0.4, 0) / 0.01 * 1.5, 75)
        # print(f'当前暴击率：{crit_rate}, 层数：{count}')

        self.buff_instance.simple_start(
            tick, self.record.sub_exist_buff_dict, no_count=1
        )
        self.buff_instance.dy.count = count
        self.buff_instance.update_to_buff_0(self.buff_0)
