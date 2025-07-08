from .. import Buff, JudgeTools, check_preparation, find_tick


class CannonRotorRecord:
    def __init__(self):
        self.equipper = None
        self.char = None
        self.enemy = None
        self.dynamic_buff_list = None
        self.skill_tag = "CannonRotorAdditionalDamage"
        self.preload_data = None
        self.sub_exist_buff_dict = None


class CannonRotor(Buff.BuffLogic):
    def __init__(self, buff_instance):
        super().__init__(buff_instance)
        self.buff_instance: Buff = buff_instance
        self.xjudge = self.special_judge_logic
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
                "加农转子", sim_instance=self.buff_instance.sim_instance
            )
        if self.buff_0 is None:
            self.buff_0 = JudgeTools.find_exist_buff_dict(
                sim_instance=self.buff_instance.sim_instance
            )[self.equipper][self.buff_instance.ft.index]
        if self.buff_0.history.record is None:
            self.buff_0.history.record = CannonRotorRecord()
        self.record = self.buff_0.history.record

    def special_judge_logic(self, **kwargs):
        self.check_record_module()
        self.get_prepared(
            equipper="加农转子", enemy=1, dynamic_buff_list=1, sub_exist_buff_dict=1
        )
        skill_node = kwargs.get("skill_node", None)
        if skill_node is None:
            return False
        from zsim.sim_progress.Preload import SkillNode

        if not isinstance(skill_node, SkillNode):
            raise ValueError(
                f"{self.buff_instance.ft.index}的Xjudge函数获取的skill_node不是SkillNode类型！"
            )
        if skill_node.char_name != self.record.char.NAME:
            return False
        if not skill_node.is_hit_now(
            find_tick(sim_instance=self.buff_instance.sim_instance)
        ):
            return False

        from zsim.sim_progress.RandomNumberGenerator import RNG
        from zsim.sim_progress.ScheduledEvent.Calculator import MultiplierData
        from zsim.sim_progress.ScheduledEvent import Calculator

        mul_data = MultiplierData(
            self.record.enemy, self.record.dynamic_buff_list, self.record.char
        )
        rng: RNG = self.buff_instance.sim_instance.rng_instance
        normalized_value = rng.random_float()
        cric_rate = Calculator.RegularMul.cal_crit_rate(mul_data)
        if normalized_value <= cric_rate:
            return True
        return False

    def special_hit_logic(self, **kwargs):
        self.check_record_module()
        self.get_prepared(
            equipper="加农转子", enemy=1, dynamic_buff_list=1, preload_data=1
        )
        event_list = JudgeTools.find_event_list(
            sim_instance=self.buff_instance.sim_instance
        )
        from zsim.sim_progress.Preload.SkillsQueue import spawn_node

        whole_skill_tag = str(self.record.char.CID) + "_" + self.record.skill_tag

        node = spawn_node(
            whole_skill_tag,
            find_tick(sim_instance=self.buff_instance.sim_instance),
            self.record.preload_data.skills,
        )
        from zsim.sim_progress.Load import LoadingMission

        mission = LoadingMission(node)
        mission.mission_start(find_tick(sim_instance=self.buff_instance.sim_instance))
        node.loading_mission = mission

        event_list.append(node)
        self.buff_instance.simple_start(
            find_tick(sim_instance=self.buff_instance.sim_instance),
            self.record.sub_exist_buff_dict,
        )
