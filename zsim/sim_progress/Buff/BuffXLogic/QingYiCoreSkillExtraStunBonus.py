from .. import Buff, JudgeTools, check_preparation


class QintYiCoreSkillExtraStunRecord:
    """
    记录信息的类。从青衣开始，这些类要统一管理。
    """

    def __init__(self):
        self.last_update_voltage = 0
        self.sub_exist_buff_dict = None
        self.action_stack = None
        self.count = 0
        self.char = None


class QingYiCoreSkillExtraStunBonus(Buff.BuffLogic):
    """
    青衣的核心被动：消耗电压时，
    溢出的电压，每1%都会转化为一层额外的失衡值提升作为补偿；
    """

    def __init__(self, buff_instance):
        super().__init__(buff_instance)
        self.buff_instance: Buff = buff_instance
        self.xjudge = self.special_judge_logic
        self.xstart = self.special_start_logic
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
            )["青衣"][self.buff_instance.ft.index]
        if self.buff_0.history.record is None:
            self.buff_0.history.record = QintYiCoreSkillExtraStunRecord()
        self.record = self.buff_0.history.record

    def special_judge_logic(self, **kwargs):
        """
        检测到SNA_1就为True，否则为False。
        这个模块优先于Buff的Start逻辑，所以可以前置更新电压。
        并且将计算出的触发情况，放到record里面预存起来。
        SNA_1分支，会直接return True，不更新电压，但是直接计算层数。
        SNA_2分支，会return True，因为也能吃到这个补偿Buff，且更新电压为0
        其他分支，更新电压后，直接返回False
        """
        self.check_record_module()
        self.get_prepared(char_CID=1300, action_stack=1)
        if self.record.action_stack.peek().mission_tag == "1300_SNA_1":
            # 这个count哪怕每次SNA_1都计算也不要紧，因为SNA_1分支不会清空电压记录，
            # 所以每次算出来都是一样的。
            self.record.count = max(self.record.last_update_voltage - 75, 0)
            return True
        elif self.record.action_stack.peek().mission_tag == "1300_SNA_2":
            self.record.last_update_voltage = 0
            return True
        else:
            self.record.last_update_voltage = self.record.char.get_resources()[1]
            return False

    def special_start_logic(self):
        """
        这里是启动逻辑。进入这一逻辑说明是SNA_1或者SNA_2的start标签。
        此时，应该从record获取层数，并且激活buff。
        """
        self.check_record_module()
        self.get_prepared(char_CID=1300, sub_exist_buff_dict=1, action_stack=1)
        tick_now = JudgeTools.find_tick(sim_instance=self.buff_instance.sim_instance)
        self.buff_instance.simple_start(tick_now, self.record.sub_exist_buff_dict)
        self.buff_0.dy.count -= self.buff_0.ft.step
        count = min(self.record.count, self.buff_instance.ft.maxcount)
        self.buff_instance.dy.count = count - 1
        self.buff_instance.update_to_buff_0(self.buff_0)
        if self.record.action_stack.peek().mission_tag == "1300_SNA_2":
            # 在增幅完SNA_2后，本轮次的record.count使命完成，进行重置。
            self.record.count = 0
