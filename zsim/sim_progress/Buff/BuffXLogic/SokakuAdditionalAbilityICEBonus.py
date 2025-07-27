from .. import Buff, JudgeTools, check_preparation


class SokakuAdditionalAbilityIBRecord:
    def __init__(self):
        self.char = None
        self.action_stack = None
        self.last_update_resource = 0


class SokakuAdditionalAbilityICEBonus(Buff.BuffLogic):
    """
    苍角组队被动：
    消耗涡流发动展旗时激活
    """

    def __init__(self, buff_instance):
        super().__init__(buff_instance)
        self.buff_instance: Buff = buff_instance
        # 初始化特定逻辑
        self.xjudge = self.special_judge_logic
        self.buff_0 = None
        self.record = None

    def get_prepared(self, **kwargs):
        return check_preparation(buff_instance=self.buff_instance, buff_0=self.buff_0, **kwargs)

    def check_record_module(self):
        if self.buff_0 is None:
            self.buff_0 = JudgeTools.find_exist_buff_dict(
                sim_instance=self.buff_instance.sim_instance
            )["苍角"][self.buff_instance.ft.index]
        if self.buff_0.history.record is None:
            self.buff_0.history.record = SokakuAdditionalAbilityIBRecord()
        self.record = self.buff_0.history.record

    def special_judge_logic(self, **kwargs):
        self.check_record_module()
        self.get_prepared(char_CID=1131, action_stack=1)
        action_now = self.record.action_stack.peek()
        resource_now = self.record.char.get_resources()[1]
        if action_now.mission_tag != "1131_E_EX_A":
            return False
        if self.record.last_update_resource <= resource_now:
            self.record.last_update_resource = resource_now
            return False
        else:
            self.record.last_update_resource = resource_now
            return True
