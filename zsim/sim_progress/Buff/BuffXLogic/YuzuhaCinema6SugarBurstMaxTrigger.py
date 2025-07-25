from .. import Buff, JudgeTools, check_preparation


class YuzuhaCinema6SugarBurstMaxTriggerRecord:
    def __init__(self):
        self.char = None
        self.enemy = None


class YuzuhaCinema6SugarBurstMaxTrigger(Buff.BuffLogic):
    """炮弹命中甜蜜惊吓状态的敌人时，会触发一次彩糖花火·极"""
    def __init__(self, buff_instance):
        super().__init__(buff_instance)
        self.buff_instance: Buff = buff_instance
        self.xjudge = self.special_judge_logic
        self.xhit = self.special_hit_logic
        self.buff_0 = None
        self.record: YuzuhaCinema6SugarBurstMaxTriggerRecord | None = None

    def get_prepared(self, **kwargs):
        return check_preparation(
            buff_instance=self.buff_instance, buff_0=self.buff_0, **kwargs
        )

    def check_record_module(self):
        if self.buff_0 is None:
            self.buff_0 = JudgeTools.find_exist_buff_dict(
                sim_instance=self.buff_instance.sim_instance
            )["柚叶"][self.buff_instance.ft.index]
        if self.buff_0.history.record is None:
            self.buff_0.history.record = YuzuhaCinema6SugarBurstMaxTriggerRecord()
        self.record = self.buff_0.history.record

    def special_judge_logic(self, **kwargs):
        self.check_record_module()
        self.get_prepared(char_CID=1411, enemy=1)
        skill_node = kwargs.get("skill_node")
        if skill_node is None:
            return False
        if skill_node.skill_tag != "1411_Cinema_6":
            return False
        if self.record.enemy.special_state_manager:
            pass
        return False
