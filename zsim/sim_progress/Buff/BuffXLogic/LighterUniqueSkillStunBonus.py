from .. import Buff, JudgeTools, check_preparation


class LighterUniqueSkillStunBonusRecord:
    def __init__(self):
        self.last_morale = 0
        self.last_morale_delta = 0
        self.buff_count = 0
        self.sub_exist_buff_dict = None
        self.char = None


class LighterUniqueSkillStunBonus(Buff.BuffLogic):
    """
    该buff是复杂判断 + 复杂生效双代码控制。
    检测莱特士气的变化。如果发生了变化，则返回True
    """

    def __init__(self, buff_instance):
        super().__init__(buff_instance)
        self.buff_instance: Buff = buff_instance
        self.xjudge = self.special_judge_logic
        self.xeffect = self.special_effect_logic
        self.buff_0 = None
        self.record = None

    def get_prepared(self, **kwargs):
        return check_preparation(
            buff_instance=self.buff_instance, buff_0=self.buff_0, **kwargs
        )

    def check_record_module(self):
        if self.buff_0 is None:
            self.buff_0 = JudgeTools.find_exist_buff_dict(
                sim_instance=self.buff_instance.sim_instance
            )["莱特"][self.buff_instance.ft.index]
        if self.buff_0.history.record is None:
            self.buff_0.history.record = LighterUniqueSkillStunBonusRecord()
        self.record = self.buff_0.history.record

    def special_judge_logic(self, **kwargs):
        """
        调用这个方法的位置，应该是buff_0的xjudge，所以，有效的self.buff_count也是存在buff_0里面的。
        """
        self.check_record_module()
        self.get_prepared(char_CID=1161)

        if self.record.last_morale > self.record.char.morale:
            # 检测到士气的下降之后，计算士气差，并且转化为层数预存起来。
            self.record.last_morale_delta = (
                self.record.last_morale - self.record.char.morale
            ) / 100
            self.record.buff_count = self.record.last_morale_delta
            self.record.last_morale = self.record.char.morale
            #   暂时假设不向下取整。
            return True
        else:
            self.record.last_morale = self.record.char.morale
            return False

    def special_effect_logic(self):
        """
        这个方法需要在xjudge通过之后调用，此时调用的是buff_new的xeffect。
        所以这里需要向buff_0获取它的的层数。
        """
        self.check_record_module()
        self.get_prepared(char_CID=1161, sub_exist_buff_dict=1)
        buff_i = self.buff_instance
        tick = JudgeTools.find_tick(sim_instance=self.buff_instance.sim_instance)
        buff_i.simple_start(tick, self.record.sub_exist_buff_dict)
        buff_i.dy.count -= buff_i.ft.step
        buff_i.dy.count = min(
            buff_i.dy.count + self.record.buff_count, buff_i.ft.maxcount
        )
        buff_i.update_to_buff_0(self.buff_0)
