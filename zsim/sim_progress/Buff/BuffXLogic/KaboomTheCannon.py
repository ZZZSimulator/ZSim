from .. import Buff, JudgeTools, check_preparation


class KaboomTheCannonRecord:
    def __init__(self):
        self.equipper = None
        self.char = None
        self.action_stack = None
        self.active_char_dict = {}
        self.sub_exist_buff_dict = None


class KaboomTheCannon(Buff.BuffLogic):
    """
    好斗的阿炮的复杂逻辑模块。主要是“1人只能提供1层”这个部分的约束
    """

    def __init__(self, buff_instance):
        super().__init__(buff_instance)
        self.buff_instance: Buff = buff_instance
        self.xhit = self.special_hit_logic
        self.equipper = None
        self.buff_0 = None
        self.record = None

    def get_prepared(self, **kwargs):
        return check_preparation(
            buff_instance=self.buff_instance, buff_0=self.buff_0, **kwargs
        )

    def check_record_module(self):
        if self.equipper is None:
            self.equipper = JudgeTools.find_equipper(
                "好斗的阿炮", sim_instance=self.buff_instance.sim_instance
            )
        if self.buff_0 is None:
            """
            这里的初始化，找到的buff_0实际上是佩戴者的buff_0
            """
            self.buff_0 = JudgeTools.find_exist_buff_dict(
                sim_instance=self.buff_instance.sim_instance
            )[self.equipper][self.buff_instance.ft.index]
        if self.buff_0.history.record is None:
            self.buff_0.history.record = KaboomTheCannonRecord()
        self.record = self.buff_0.history.record

    def special_hit_logic(self):
        """主要归档触发源。"""
        # TODO: 等三只小猪加入了，可能还得重新弄。
        self.check_record_module()
        self.get_prepared(equipper="好斗的阿炮", action_stack=1, sub_exist_buff_dict=1)
        action_now = self.record.action_stack.peek()
        tick_now = JudgeTools.find_tick(sim_instance=self.buff_instance.sim_instance)
        self.record.active_char_dict[action_now.mission_character] = [
            tick_now,
            tick_now + self.buff_instance.ft.maxduration,
        ]
        for names, tick_list in self.record.active_char_dict.copy().items():
            if tick_list[1] <= tick_now:
                del self.record.active_char_dict[names]
        self.buff_instance.simple_start(
            tick_now, self.record.sub_exist_buff_dict, not_count=True
        )
        input_list = list(self.record.active_char_dict.values())
        self.buff_instance.dy.built_in_buff_box = input_list
        self.buff_instance.update_to_buff_0(self.buff_0)
