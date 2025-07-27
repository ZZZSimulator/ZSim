from .. import Buff, JudgeTools, check_preparation


class NicoleCoreSkillRecord:
    def __init__(self):
        self.action_stack = None
        self.char = None
        self.enemy = None
        self.dynamic_buff_list = None
        self.sub_exist_buff_dict = None


class NicoleCoreSkillDefReduction(Buff.BuffLogic):
    def __init__(self, buff_instance):
        """
        妮可的核心被动，减防。
        """
        super().__init__(buff_instance)
        self.buff_instance: Buff = buff_instance
        self.buff_0 = None
        self.record = None
        self.xjudge = self.special_judge_logic

    def get_prepared(self, **kwargs):
        return check_preparation(buff_instance=self.buff_instance, buff_0=self.buff_0, **kwargs)

    def check_record_module(self):
        if self.buff_0 is None:
            self.buff_0 = JudgeTools.find_exist_buff_dict(
                sim_instance=self.buff_instance.sim_instance
            )["妮可"][self.buff_instance.ft.index]
        if self.buff_0.history.record is None:
            self.buff_0.history.record = NicoleCoreSkillRecord()
        self.record = self.buff_0.history.record

    def special_judge_logic(self, **kwargs):
        """
        目前这个buff的触发条件是简化过的。本来应该是检测“强化子弹”
        """
        self.check_record_module()
        self.get_prepared(action_stack=1)
        if self.record.action_stack.peek().mission_tag == "1211_SNA_1":
            return False
        else:
            return True
