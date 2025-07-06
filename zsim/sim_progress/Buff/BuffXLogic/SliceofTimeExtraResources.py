from .. import Buff, JudgeTools, check_preparation


class SliceofTimeExtraResourcesRecord:
    def __init__(self):
        self.equipper = None
        self.char = None
        self.action_stack = None
        self.sub_exist_buff_dict = None
        self.decibel_value_dict = {
            1: {4: 20, 2: 25, 7: 30, 8: 30, 9: 30, 5: 35},
            2: {4: 23, 2: 28.5, 7: 34.5, 8: 34.5, 9: 34.5, 5: 40},
            3: {4: 26, 2: 32, 7: 39, 8: 39, 9: 39, 5: 45},
            4: {4: 29, 2: 35.5, 7: 43.5, 8: 43.5, 9: 43.5, 5: 50},
            5: {4: 32, 2: 40, 7: 48, 8: 48, 9: 48, 5: 55},
        }
        self.energy_value_dict = {1: 0.7, 2: 0.8, 3: 0.9, 4: 1.0, 5: 1.1}
        self.last_update_tick_box = {"E_EX": 0, "Sup": 0, "QTE": 0, "CA": 0}
        self.update_key_dict = {
            2: "E_EX",
            4: "CA",
            5: "QTE",
            7: "Sup",
            8: "Sup",
            9: "Sup",
        }


class SliceofTimeExtraResources(Buff.BuffLogic):
    """
    这是时光切片的复杂效果逻辑。
    虽然该buff的buff effect为空，但是在special_start逻辑中，内置了恢复能量和喧响值的方法。
    通过构建Schedule Refresh Data的实例，并向event list中添加，
    就可以实现角色的喧响值和能量值的修改。
    """

    def __init__(self, buff_instance):
        super().__init__(buff_instance)
        self.buff_instance: Buff = buff_instance
        self.xjudge = self.special_judge_logic
        self.xstart = self.special_start_logic
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
                "时光切片", sim_instance=self.buff_instance.sim_instance
            )
        if self.buff_0 is None:
            self.buff_0 = JudgeTools.find_exist_buff_dict(
                sim_instance=self.buff_instance.sim_instance
            )[self.equipper][self.buff_instance.ft.index]
        if self.buff_0.history.record is None:
            self.buff_0.history.record = SliceofTimeExtraResourcesRecord()
        self.record = self.buff_0.history.record

    def special_judge_logic(self, **kwargs):
        """
        第一层判定是trigger_buff_level的判定
        通过第一层判定后，再过内置CD检测。
        """
        self.check_record_module()
        self.get_prepared(equipper="时光切片", action_stack=1)
        action_now = self.record.action_stack.peek()
        trigger_buff_level = action_now.mission_node.skill.trigger_buff_level
        tick_now = JudgeTools.find_tick(sim_instance=self.buff_instance.sim_instance)
        if trigger_buff_level in [4, 2, 7, 8, 9, 5]:
            ready = self.check_update_cd(trigger_buff_level, tick_now)
            if ready:
                return True
            else:
                return False
        else:
            return False

    def special_start_logic(self):
        """
        这部分的代码主要是负责构建一个ScheduleRefreshData实例的，
        而simple_start只是为了启动一次，让Log记录到这个buff。
        Buff自身没有效果。
        """
        self.check_record_module()
        self.get_prepared(equipper="时光切片", action_stack=1, sub_exist_buff_dict=1)
        tick_now = JudgeTools.find_tick(sim_instance=self.buff_instance.sim_instance)
        self.buff_instance.simple_start(tick_now, self.record.sub_exist_buff_dict)
        action_now = self.record.action_stack.peek()
        trigger_buff_level = action_now.mission_node.skill.trigger_buff_level
        decibel_value = self.record.decibel_value_dict[
            self.buff_instance.ft.refinement
        ][trigger_buff_level]
        energy_value = self.record.energy_value_dict[self.buff_instance.ft.refinement]
        actor_name = action_now.mission_character
        event_list = JudgeTools.find_event_list(
            sim_instance=self.buff_instance.sim_instance
        )
        from zsim.sim_progress.data_struct import ScheduleRefreshData

        refresh_data = ScheduleRefreshData(
            sp_target=(self.record.char.NAME,),
            sp_value=energy_value,
            decibel_target=(actor_name,),
            decibel_value=decibel_value,
        )
        event_list.append(refresh_data)

    def check_update_cd(self, tbl: int, tick_now: int):
        """
        检测内置CD！由于闪避反击、强化E、支援技、QTE的触发CD是分开计算的，
        所以，这里也要根据trigger buff level进行分流，分别检测各自的CD。
        """
        if tbl not in self.record.update_key_dict:
            raise ValueError(f"传入的Trigger Buff Level为{tbl}，不在检测范围内！")
        key = self.record.update_key_dict[tbl]
        last_update_tick = self.record.last_update_tick_box[key]
        if last_update_tick == 0:
            self.record.last_update_tick_box[key] = tick_now
            return True
        if tick_now - last_update_tick > self.buff_instance.ft.cd:
            self.record.last_update_tick_box[key] = tick_now
            return True
        else:
            return False
