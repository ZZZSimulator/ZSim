from .. import Buff, JudgeTools, check_preparation, find_tick


class HeartstringNocturneRecord:
    def __init__(self):
        self.equipper = None
        self.char = None
        self.listener_exist = False
        self.listener = None


class HeartstringNocturne(Buff.BuffLogic):
    """心弦夜响的复杂逻辑：进入战斗或是释放连携技、大招时触发。"""

    def __init__(self, buff_instance):
        super().__init__(buff_instance)
        self.buff_instance: Buff = buff_instance
        self.xjudge = self.special_judge_logic
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
                "心弦夜响", sim_instance=self.buff_instance.sim_instance
            )
        if self.buff_0 is None:
            self.buff_0 = JudgeTools.find_exist_buff_dict(
                sim_instance=self.buff_instance.sim_instance
            )[self.equipper][self.buff_instance.ft.index]
        if self.buff_0.history.record is None:
            self.buff_0.history.record = HeartstringNocturneRecord()
        self.record = self.buff_0.history.record

    def special_judge_logic(self, **kwargs):
        self.check_record_module()
        self.get_prepared(equipper="心弦夜响")
        if not self.record.listener_exist:
            self.record.listener = (
                self.buff_instance.sim_instance.listener_manager.get_listener(
                    listener_owner=self.record.char,
                    listener_id="Heartstring_Nocturne_1",
                )
            )
            # self.record.listener = self.buff_instance.sim_instance.listener_manager.listener_factory(
            #     initiate_signal="Heartstring_Nocturne_1", sim_instance=self.buff_instance.sim_instance
            # )
            self.record.listener_exist = True
            # print(f"为{self.record.char.NAME}创建了一个心弦夜响的监听器！")
        skill_node = kwargs.get("skill_node", None)
        if skill_node is None:
            return False
        from zsim.sim_progress.Preload import SkillNode

        if not isinstance(skill_node, SkillNode):
            raise ValueError(
                f"{self.buff_instance.ft.index}的Xjudge函数获取的skill_node不是SkillNode类型！"
            )
        active_signal = self.record.listener.active_signal
        if active_signal is not None:
            event_obj: SkillNode = active_signal[0]
            if event_obj.char_name == self.record.char.NAME:
                return True
        else:
            if skill_node.char_name == self.record.char.NAME:
                if skill_node.preload_tick == find_tick(
                    sim_instance=self.buff_instance.sim_instance
                ) and skill_node.skill.trigger_buff_level in [5, 6]:
                    return True
        return False
