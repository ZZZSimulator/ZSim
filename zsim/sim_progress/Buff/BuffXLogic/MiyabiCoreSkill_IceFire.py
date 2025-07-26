from zsim.sim_progress import Preload
from zsim.sim_progress.ScheduledEvent import Calculator
from zsim.sim_progress.ScheduledEvent.Calculator import MultiplierData

from .. import Buff, JudgeTools, check_preparation


class MiyabiCoreSkillIF:
    def __init__(self):
        self.char = None
        self.sub_exist_buff_dict = None
        self.dynamic_buff_list = None
        self.last_frostbite = False
        self.enemy = None
        self.action_stack = None


class MiyabiCoreSkill_IceFire(Buff.BuffLogic):
    """
    该buff是雅的核心被动中的【冰焰】，冰焰在判断TrigerBuffLevel的同时，
    还需要检索当前enemy_debuff_list中是否含有【霜灼】，如果有就返回False
    """

    def __init__(self, buff_instance):
        super().__init__(buff_instance)
        self.buff_instance: Buff = buff_instance
        self.xjudge = self.special_judge_logic
        self.xexit = self.special_exit_logic
        self.xhit = self.special_hit_logic
        self.buff_0 = None
        self.record = None

    def get_prepared(self, **kwargs):
        return check_preparation(buff_instance=self.buff_instance, buff_0=self.buff_0, **kwargs)

    def check_record_module(self):
        if self.buff_0 is None:
            self.buff_0 = JudgeTools.find_exist_buff_dict(
                sim_instance=self.buff_instance.sim_instance
            )["雅"][self.buff_instance.ft.index]
        if self.buff_0.history.record is None:
            self.buff_0.history.record = MiyabiCoreSkillIF()
        self.record = self.buff_0.history.record

    def special_judge_logic(self, **kwargs):
        """
        这个复杂判断逻辑需要同时检索当前技能的element_type，
        以及enemy的debuff_list有没有霜灼，
        两者都通过，才会return True
        """
        self.check_record_module()
        self.get_prepared(enemy=1, action_stack=1)

        enemy = self.record.enemy
        mission_now = self.record.action_stack.peek()
        debuff_list = enemy.dynamic.dynamic_debuff_list

        if mission_now.mission_node.element_type != 5:
            return False
        else:
            for debuff in debuff_list:
                if not isinstance(debuff, Buff):
                    raise TypeError(f"{debuff}不是Buff类！")
                if debuff.ft.index == "Buff-角色-雅-核心被动-霜灼":
                    return False
            else:
                return True

    def special_exit_logic(self):
        """
        冰焰buff的退出机制是检测到霜寒的上升沿就退出
        """
        self.check_record_module()
        self.get_prepared(char_CID=1091, enemy=1)
        enemy = self.record.enemy
        frostbite_now = enemy.dynamic.frost_frostbite
        if frostbite_now is None:
            frostbite_now = False

        frostbite_statement = [self.record.last_frostbite, frostbite_now]

        def mode_func(a, b):
            return a is False and b is True

        result = JudgeTools.detect_edge(frostbite_statement, mode_func)
        self.record.last_frostbite = frostbite_now
        # print(f'当前tick，冰焰退出情况：{result}')
        if result:
            event_list = JudgeTools.find_event_list(sim_instance=self.buff_instance.sim_instance)
            skill_obj = self.record.char.skills_dict["1091_Core_Passive"]
            skill_node = Preload.SkillNode(skill_obj, 0)
            event_list.append(skill_node)
            self.record.char.special_resources(skill_node)
        return result

    def special_hit_logic(self):
        """
        冰焰的生效机制是：根据当前的暴击率，得出当前的Buff层数。
        这个效果本应该是随动的，不需要buff判定通过才改变层数，
        但是如果buff判定不通过，那么烈霜伤害，该buff层数的变动就没有实际意义，
        """
        self.check_record_module()
        self.get_prepared(char_CID=1091, enemy=1, dynamic_buff_list=1, sub_exist_buff_dict=1)
        enemy = self.record.enemy
        dynamic_buff = self.record.dynamic_buff_list
        tick_now = JudgeTools.find_tick(sim_instance=self.buff_instance.sim_instance)
        buff_i = self.buff_instance
        buff_i.simple_start(tick_now, self.record.sub_exist_buff_dict)
        buff_i.dy.count -= buff_i.ft.step

        mul_data = MultiplierData(enemy, dynamic_buff, self.record.char)
        crit_rate = Calculator.RegularMul.cal_crit_rate(mul_data)
        count = min(crit_rate, 0.8) * 100

        # print(crit_rate, count)
        buff_i.dy.count = min(count, self.buff_0.ft.maxcount)
        buff_i.update_to_buff_0(self.buff_0)
