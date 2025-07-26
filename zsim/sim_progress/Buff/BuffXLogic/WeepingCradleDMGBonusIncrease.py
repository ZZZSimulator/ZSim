from .. import Buff, JudgeTools, check_preparation


class WeepingCradleDMGBRecord:
    def __init__(self):
        self.equipper = None
        self.char = None
        self.sub_exist_buff_dict = None
        self.trigger_buff_0 = None
        self.sub_exist_buff_dict = None
        self.last_update_tick = 0


class WeepingCradleDMGBonusIncrease(Buff.BuffLogic):
    """
    这是啜泣摇篮的自增伤模组。
    它需要检测触发器buff [Buff-武器-啜泣摇篮-全队增伤]的 状态来判定自身的状态，这里还涉及一个字符串拼接问题，保证该逻辑能在各个buff中通用。
    同时，它还需要判定自身更新的CD，来规避绝无效运算。
    判定通过后，它通过special effect来启动，并且进行自叠层。
    启动阶段，它的起止时间是触发器buff的时间，这点比较特殊，所以在simple start之后，要修改起止时间并且重新update
    而在自叠层阶段，它只修改层数，不修改起止时间。
    """

    def __init__(self, buff_instance):
        super().__init__(buff_instance)
        self.buff_instance: Buff = buff_instance
        # 初始化特定逻辑
        self.xjudge = self.special_judge_logic
        self.xeffect = self.special_effect_logic
        self.equipper = None
        self.buff_0 = None
        self.record = None

    def get_prepared(self, **kwargs):
        return check_preparation(buff_instance=self.buff_instance, buff_0=self.buff_0, **kwargs)

    def check_record_module(self):
        if self.equipper is None:
            self.equipper = JudgeTools.find_equipper(
                "啜泣摇篮", sim_instance=self.buff_instance.sim_instance
            )
        if self.buff_0 is None:  # 这里的初始化，找到的buff_0实际上是佩戴者的buff_0，
            self.buff_0 = JudgeTools.find_exist_buff_dict(
                sim_instance=self.buff_instance.sim_instance
            )[self.equipper][self.buff_instance.ft.index]
        if self.buff_0.history.record is None:
            self.buff_0.history.record = WeepingCradleDMGBRecord()
        self.record = self.buff_0.history.record

    def special_judge_logic(self, **kwargs):
        self.check_record_module()
        trigger_index = f"Buff-武器-精{int(self.buff_instance.ft.refinement)}啜泣摇篮-全队增伤"
        self.get_prepared(
            equipper="啜泣摇篮",
            trigger_buff_0=(self.buff_instance.ft.operator, trigger_index),
        )
        if self.record.trigger_buff_0.dy.active:
            result = self.increase_cd_judge()
            if result:
                return True
            else:
                return False
        else:
            return False

    def special_effect_logic(self, **kwargs):
        self.check_record_module()
        self.get_prepared(equipper="啜泣摇篮", sub_exist_buff_dict=1)
        tick_now = JudgeTools.find_tick(sim_instance=self.buff_instance.sim_instance)
        if not self.buff_0.dy.active:
            self.buff_instance.simple_start(tick_now, self.record.sub_exist_buff_dict)
            self.buff_instance.dy.startticks = self.record.trigger_buff_0.dy.startticks
            self.buff_instance.dy.endticks = self.record.trigger_buff_0.dy.endticks
            self.buff_instance.update_to_buff_0(self.buff_0)
        else:
            self.buff_instance.simple_start(
                tick_now, self.record.sub_exist_buff_dict, no_start=True, no_end=True
            )

    def increase_cd_judge(self):
        tick_now = JudgeTools.find_tick(sim_instance=self.buff_instance.sim_instance)
        if tick_now - self.record.last_update_tick >= self.buff_instance.ft.cd:
            self.record.last_update_tick = tick_now
            return True
        else:
            return False
