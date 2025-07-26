from .. import Buff, JudgeTools, check_preparation


class QintYiCoreSkillRecord:
    """
    记录信息的类。从青衣开始，这些类要统一管理。
    """

    def __init__(self):
        self.pre_saved_counts = 0
        self.last_update_stun = False
        self.last_update_skill_tag = None
        self.char = None
        self.enemy = None
        self.sub_exist_buff_dict = None


class QingYiCoreSkillStunDMGBonus(Buff.BuffLogic):
    """
    青衣的核心被动：[羁服]——失衡易伤以及连携技增伤；
    该buff有两个模块，分别是：XHit以及Xexit
    Xhit根据当前的Tag来控制层数的变化；
    而Xexit则在检测到失衡状态的下降沿时执行，输出True
    """

    def __init__(self, buff_instance):
        super().__init__(buff_instance)
        self.buff_instance: Buff = buff_instance
        self.xstart = self.special_start_logic
        self.xexit = self.special_exit_logic
        self.buff_0 = None
        self.record = None

    def get_prepared(self, **kwargs):
        return check_preparation(buff_instance=self.buff_instance, buff_0=self.buff_0, **kwargs)

    def check_record_module(self):
        if self.buff_0 is None:
            self.buff_0 = JudgeTools.find_exist_buff_dict(
                sim_instance=self.buff_instance.sim_instance
            )["青衣"][self.buff_instance.ft.index]
        if self.buff_0.history.record is None:
            self.buff_0.history.record = QintYiCoreSkillRecord()
        self.record = self.buff_0.history.record

    def special_start_logic(self):
        """
        检测到当前的action_stack，判断它们的mission_tag
        SNA_1叠1层， 且预叠1层；
        SNA_2叠5层，且追加叠加所有的预叠层数。
        """
        self.check_record_module()
        self.get_prepared(char_CID=1300, sub_exist_buff_dict=1, enemy=1)
        action_stack = JudgeTools.find_stack(sim_instance=self.buff_instance.sim_instance)
        action_now = action_stack.peek()
        last_action = action_stack.peek_bottom()
        tick_now = JudgeTools.find_tick(sim_instance=self.buff_instance.sim_instance)
        self.buff_instance.simple_start(tick_now, self.record.sub_exist_buff_dict)
        self.buff_0.dy.count -= 1
        self.buff_instance.dy.count = self.buff_0.dy.count
        if action_now.mission_tag == "1300_SNA_1":
            if last_action.mission_tag != "1300_SNA_1":
                """上一个动作不是1300_SNA_1时，强制清空现有层数。"""
                self.record.pre_saved_counts = 0
            self.buff_instance.dy.count += 1
            self.record.pre_saved_counts += 1
            if self.record.pre_saved_counts > 5:
                raise ValueError(
                    f"1300_SNA_1提供的预叠层数已经超过了5，\n"
                    f"当前为：{self.record.pre_saved_counts}，\n"
                    f"应该是APL代码的逻辑有问题，请检查1300_SNA_2的释放逻辑！"
                )
        elif action_now.mission_tag == "1300_SNA_2":
            self.buff_instance.dy.count += 5
            self.buff_instance.dy.count += self.record.pre_saved_counts
            self.record.pre_saved_counts = 0
        self.buff_instance.dy.count = min(self.buff_instance.dy.count, 20)
        self.buff_instance.update_to_buff_0(self.buff_0)

    def special_exit_logic(self):
        """
        退出逻辑：检测到失衡的下降沿。
        """
        self.check_record_module()
        self.get_prepared(char_CID=1300, sub_exist_buff_dict=1, enemy=1)

        def mode_func(a, b):
            return a is True and b is False

        stun_statement_tuple = (
            self.record.last_update_stun,
            self.record.enemy.dynamic.stun,
        )
        if JudgeTools.detect_edge(stun_statement_tuple, mode_func):
            self.record.last_update_stun = self.record.enemy.dynamic.stun
            return True
        self.record.last_update_stun = self.record.enemy.dynamic.stun
        return False
