from .. import Buff, JudgeTools, check_preparation


class JaneCoreSkillStrikeCritDmgBonusRecord:
    def __init__(self):
        self.char = None
        self.trigger_buff_0 = None
        self.dynamic_buff_list = None
        self.enemy = None
        self.sub_exist_buff_dict = None


class JaneCoreSkillStrikeCritDmgBonus(Buff.BuffLogic):
    def __init__(self, buff_instance):
        """简核心被动中，强击暴击伤害的复杂逻辑"""
        super().__init__(buff_instance)
        self.buff_instance: Buff = buff_instance
        self.buff_0 = None
        self.record = None
        self.xjudge = self.special_judge_logic
        self.xexit = self.special_exit_logic

    def get_prepared(self, **kwargs):
        return check_preparation(
            buff_instance=self.buff_instance, buff_0=self.buff_0, **kwargs
        )

    def check_record_module(self):
        if self.buff_0 is None:
            self.buff_0 = JudgeTools.find_exist_buff_dict(
                sim_instance=self.buff_instance.sim_instance
            )["简"][self.buff_instance.ft.index]
        if self.buff_0.history.record is None:
            self.buff_0.history.record = JaneCoreSkillStrikeCritDmgBonusRecord()
        self.record = self.buff_0.history.record

    def special_judge_logic(self, **kwargs):
        """强击的暴伤Debuff情况是和啮咬绑定的。"""
        self.check_record_module()
        self.get_prepared(
            char_CID=1301, trigger_buff_0=("enemy", "Buff-角色-简-核心被动-啮咬触发器")
        )
        if self.record.trigger_buff_0.dy.active:
            return True
        else:
            return False

    def special_exit_logic(self, **kwargs):
        """此Buff退出逻辑和触发逻辑相反"""
        return not self.special_judge_logic()
