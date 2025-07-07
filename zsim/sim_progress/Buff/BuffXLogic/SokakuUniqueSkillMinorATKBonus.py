from .. import Buff, JudgeTools, check_preparation


class SokakuUniqueSkillMinorATKRecord:
    def __init__(self):
        self.char = None
        self.sub_exist_buff_dict = None


class SokakuUniqueSkillMinorATKBonus(Buff.BuffLogic):
    """
    这里是苍角的核心被动 1，核心被动1的触发无需复杂代码控制，
    只要释放了展旗，就会判定通过。
    但是，具体的层数，却是要根据苍角的面板攻击力实时调取的。
    """

    def __init__(self, buff_instance):
        super().__init__(buff_instance)
        self.buff_instance: Buff = buff_instance
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
            )["苍角"][self.buff_instance.ft.index]
        if self.buff_0.history.record is None:
            self.buff_0.history.record = SokakuUniqueSkillMinorATKRecord()
        self.record = self.buff_0.history.record

    def special_start_logic(self):
        """
        展旗发动时，应该检索当前角色的面板攻击力。
        """
        self.check_record_module()
        self.get_prepared(char_CID=1131, sub_exist_buff_dict=1)
        atk_now = self.record.char.statement.ATK
        count = min(atk_now * 0.2, 500)
        tick_now = JudgeTools.find_tick(sim_instance=self.buff_instance.sim_instance)
        self.buff_instance.simple_start(tick_now, self.record.sub_exist_buff_dict)
        self.buff_instance.dy.count = count
        self.buff_instance.update_to_buff_0(self.buff_0)
