from .. import Buff, JudgeTools, check_preparation
from zsim.sim_progress.ScheduledEvent import Calculator
from zsim.sim_progress.ScheduledEvent.Calculator import MultiplierData


class QingYiAdditionalSkillRecord:
    def __init__(self):
        self.char = None
        self.enemy = None
        self.sub_exist_buff_dict = None
        self.dynamic_buff_list = None


class QingYiAdditionalAbilityStunConvertToATK(Buff.BuffLogic):
    def __init__(self, buff_instance):
        """
        青衣的组队被动之冲击力转模部分。
        """
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
            )["青衣"][self.buff_instance.ft.index]
        if self.buff_0.history.record is None:
            self.buff_0.history.record = QingYiAdditionalSkillRecord()
        self.record = self.buff_0.history.record

    def special_judge_logic(self, **kwargs):
        return True

    def special_hit_logic(self):
        """
        找冲击力，并且构建mul现场算。算完出层数即可。
        """
        self.check_record_module()
        self.get_prepared(
            char_CID=1251, enemy=1, dynamic_buff_list=1, sub_exist_buff_dict=1
        )
        tick_now = JudgeTools.find_tick(sim_instance=self.buff_instance.sim_instance)
        self.buff_instance.simple_start(tick_now, self.record.sub_exist_buff_dict)
        self.buff_0.dy.count -= self.buff_0.ft.step
        mul_data = MultiplierData(
            self.record.enemy, self.record.dynamic_buff_list, self.record.char
        )
        stun_value = Calculator.StunMul.cal_imp(mul_data)
        count = min((stun_value - 120) * 6, self.buff_instance.ft.maxcount)
        self.buff_instance.dy.count = count
        self.buff_instance.update_to_buff_0(self.buff_0)
