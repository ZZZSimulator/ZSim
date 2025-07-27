from .. import Buff, JudgeTools, check_preparation


class ElegantVanitySpRecoverRecord:
    def __init__(self):
        self.equipper = None
        self.char = None
        self.sub_exist_buff_dict = None
        self.energy_value_dict = {1: 5, 2: 5.5, 3: 6, 4: 6.5, 5: 7}


class ElegantVanitySpRecover(Buff.BuffLogic):
    """玲珑妆匣的回能Buff逻辑。"""

    def __init__(self, buff_instance):
        super().__init__(buff_instance)
        self.buff_instance: Buff = buff_instance
        self.xstart = self.special_start_logic
        self.equipper = None
        self.buff_0 = None
        self.record = None

    def get_prepared(self, **kwargs):
        return check_preparation(buff_instance=self.buff_instance, buff_0=self.buff_0, **kwargs)

    def check_record_module(self):
        if self.equipper is None:
            self.equipper = JudgeTools.find_equipper(
                "玲珑妆匣", sim_instance=self.buff_instance.sim_instance
            )
        if self.buff_0 is None:
            self.buff_0 = JudgeTools.find_exist_buff_dict(
                sim_instance=self.buff_instance.sim_instance
            )[self.equipper][self.buff_instance.ft.index]
        if self.buff_0.history.record is None:
            self.buff_0.history.record = ElegantVanitySpRecoverRecord()
        self.record = self.buff_0.history.record

    def special_start_logic(self):
        """
        这部分的代码主要是负责构建一个ScheduleRefreshData实例的，
        而simple_start只是为了启动一次，让Log记录到这个buff。
        Buff自身没有效果。
        """
        self.check_record_module()
        self.get_prepared(equipper="玲珑妆匣", sub_exist_buff_dict=1)
        tick_now = JudgeTools.find_tick(sim_instance=self.buff_instance.sim_instance)
        self.buff_instance.simple_start(tick_now, self.record.sub_exist_buff_dict)
        energy_value = self.record.energy_value_dict[int(self.buff_instance.ft.refinement)]
        event_list = JudgeTools.find_event_list(sim_instance=self.buff_instance.sim_instance)
        from zsim.sim_progress.data_struct import ScheduleRefreshData

        refresh_data = ScheduleRefreshData(
            sp_target=(self.record.char.NAME,),
            sp_value=energy_value,
        )
        event_list.append(refresh_data)
        # print(f'玲珑妆匣回能触发！')
