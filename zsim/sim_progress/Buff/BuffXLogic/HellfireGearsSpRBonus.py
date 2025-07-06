from .. import Buff, JudgeTools


class HellfireGearsSpRBonus(Buff.BuffLogic):
    """
    燃狱齿轮的后台回能。需要在初始化的时候就获取角色和武器配置列表
    """

    def __init__(self, buff_instance):
        super().__init__(buff_instance)
        self.buff_instance: Buff = buff_instance
        self.xjudge = self.special_judge_logic
        self.xexit = self.special_exit_logic
        self.equipper = None

    def special_judge_logic(self, **kwargs):
        if self.equipper is None:
            self.equipper = JudgeTools.find_equipper(
                "燃狱齿轮", sim_instance=self.buff_instance.sim_instance
            )
        name_box = JudgeTools.find_init_data(
            sim_instance=self.buff_instance.sim_instance
        ).name_box
        if name_box[0] != self.equipper:
            return True
        else:
            return False

    def special_exit_logic(self):
        if self.equipper is None:
            self.equipper = JudgeTools.find_equipper(
                "燃狱齿轮", sim_instance=self.buff_instance.sim_instance
            )
        name_box = JudgeTools.find_init_data(
            sim_instance=self.buff_instance.sim_instance
        ).name_box
        if name_box[0] == self.equipper:
            return True
        else:
            return False
