from .. import Buff, JudgeTools


class BackendJudge(Buff.BuffLogic):
    """
    后台判定的通用逻辑模块
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
                self.buff_instance.ft.bufffrom,
                sim_instance=self.buff_instance.sim_instance,
            )
        name_box = JudgeTools.find_init_data(sim_instance=self.buff_instance.sim_instance).name_box
        if name_box[0] != self.equipper:
            return True
        else:
            return False

    def special_exit_logic(self):
        result = self.xjudge()
        if result:
            return False
        else:
            return True
