from .. import Buff, JudgeTools, check_preparation


class MagneticStormCharlieSpRecoverRecord:
    def __init__(self):
        self.equipper = None
        self.char = None
        self.sub_exist_buff_dict = None
        self.energy_value_dict = {1: 3.5, 2: 4, 3: 4.5, 4: 5, 5: 5.5}


class MagneticStormCharlieSpRecover(Buff.BuffLogic):
    """电磁暴3式判定逻辑"""

    def __init__(self, buff_instance):
        super().__init__(buff_instance)
        self.buff_instance: Buff = buff_instance
        self.xjudge = self.special_judge_logic
        self.xhit = self.special_hit_logic
        self.equipper = None
        self.buff_0 = None
        self.record = None

    def get_prepared(self, **kwargs):
        return check_preparation(buff_instance=self.buff_instance, buff_0=self.buff_0, **kwargs)

    def check_record_module(self):
        if self.equipper is None:
            self.equipper = JudgeTools.find_equipper(
                "「电磁暴」-叁式", sim_instance=self.buff_instance.sim_instance
            )
        if self.buff_0 is None:
            self.buff_0 = JudgeTools.find_exist_buff_dict(
                sim_instance=self.buff_instance.sim_instance
            )[self.equipper][self.buff_instance.ft.index]
        if self.buff_0.history.record is None:
            self.buff_0.history.record = MagneticStormCharlieSpRecoverRecord()
        self.record = self.buff_0.history.record

    def special_judge_logic(self, **kwargs):
        """只要造成了积蓄值，就放行"""
        self.check_record_module()
        self.get_prepared(equipper="「电磁暴」-叁式")
        skill_node = kwargs.get("skill_node", None)
        if skill_node is None:
            return False
        from zsim.sim_progress.Preload import SkillNode
        from zsim.sim_progress.Load import LoadingMission

        if isinstance(skill_node, SkillNode):
            pass
        elif isinstance(skill_node, LoadingMission):
            skill_node = skill_node.mission_node
        else:
            return False
        # 滤去不是自己的技能
        if self.record.equipper != skill_node.char_name:
            return False

        if (
            skill_node.skill.anomaly_accumulation != 0
            and skill_node.skill.element_damage_percent > 0
        ):
            return True
        return False

    def special_hit_logic(self, **kwargs):
        self.check_record_module()
        self.get_prepared(equipper="「电磁暴」-叁式", sub_exist_buff_dict=1)
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
        print("电磁暴3式回能触发！")
