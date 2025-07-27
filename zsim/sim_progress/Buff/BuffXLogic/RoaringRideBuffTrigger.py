from .. import Buff, JudgeTools, check_preparation, find_tick


class RoaringRideBuffTriggerRecord:
    def __init__(self):
        self.equipper = None
        self.char = None
        self.buff_map = None
        self.sub_exist_buff_dict = None


class RoaringRideBuffTrigger(Buff.BuffLogic):
    """轰鸣座驾触发器"""

    def __init__(self, buff_instance):
        super().__init__(buff_instance)
        self.buff_instance: Buff = buff_instance
        self.xhit = self.special_hit_logic
        self.equipper = None
        self.buff_0 = None
        self.record: RoaringRideBuffTriggerRecord | None = None

    def get_prepared(self, **kwargs):
        return check_preparation(buff_instance=self.buff_instance, buff_0=self.buff_0, **kwargs)

    def check_record_module(self):
        if self.equipper is None:
            self.equipper = JudgeTools.find_equipper(
                "轰鸣座驾", sim_instance=self.buff_instance.sim_instance
            )
        if self.buff_0 is None:
            self.buff_0 = JudgeTools.find_exist_buff_dict(
                sim_instance=self.buff_instance.sim_instance
            )[self.equipper][self.buff_instance.ft.index]
        if self.buff_0.history.record is None:
            self.buff_0.history.record = RoaringRideBuffTriggerRecord()
        self.record = self.buff_0.history.record

    def special_hit_logic(self, **kwargs):
        """
        轰鸣座驾的判定是简单逻辑，只要是强化E命中即可。
        命中后，会执行special_hit函数，该函数会抽取随机数，并且为自己添加对应的Buff
        """
        self.check_record_module()
        self.get_prepared(equipper="轰鸣座驾", sub_exist_buff_dict=1)
        if self.record.buff_map is None:
            self.record.buff_map = {
                0: f"Buff-武器-精{int(self.buff_instance.ft.refinement)}轰鸣座驾-攻击力",
                1: f"Buff-武器-精{int(self.buff_instance.ft.refinement)}轰鸣座驾-精通提升",
                2: f"Buff-武器-精{int(self.buff_instance.ft.refinement)}轰鸣座驾-属性异常积蓄",
            }
        from zsim.sim_progress.RandomNumberGenerator import RNG
        from zsim.sim_progress.Buff.BuffAddStrategy import buff_add_strategy

        rng: RNG = self.buff_instance.sim_instance.rng_instance
        normalized_value = rng.random_float()
        if 0 <= normalized_value < 1 / 3:
            buff_add_strategy(self.record.buff_map[0], sim_instance=self.buff_instance.sim_instance)
            # print(f'轰鸣座驾触发了攻击力Buff')
        elif 1 / 3 <= normalized_value < 2 / 3:
            buff_add_strategy(self.record.buff_map[1], sim_instance=self.buff_instance.sim_instance)
            # print(f'轰鸣座驾触发了精通Buff')
        else:
            # print(f'轰鸣座驾触发了积蓄效率Buff')
            buff_add_strategy(self.record.buff_map[2], sim_instance=self.buff_instance.sim_instance)

        self.buff_instance.simple_start(
            find_tick(sim_instance=self.buff_instance.sim_instance),
            self.record.sub_exist_buff_dict,
        )
