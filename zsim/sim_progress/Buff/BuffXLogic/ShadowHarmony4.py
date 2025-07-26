from .. import Buff, JudgeTools, check_preparation, find_tick


class ShadowHarmony4Record:
    def __init__(self):
        self.equipper = None
        self.char = None


class ShadowHarmony4(Buff.BuffLogic):
    """
    这是极地重金属的复杂逻辑判定。
    主要检测的是碎冰的变化状态，如果碎冰状态变了，就返回True
    """

    def __init__(self, buff_instance):
        super().__init__(buff_instance)
        self.buff_instance: Buff = buff_instance
        # 初始化特定逻辑
        self.xjudge = self.special_judge_logic
        self.equipper = None
        self.buff_0 = None
        self.record = None

    def get_prepared(self, **kwargs):
        return check_preparation(buff_instance=self.buff_instance, buff_0=self.buff_0, **kwargs)

    def check_record_module(self):
        if self.equipper is None:
            self.equipper = JudgeTools.find_equipper(
                "如影相随", sim_instance=self.buff_instance.sim_instance
            )
        if self.buff_0 is None:
            self.buff_0 = JudgeTools.find_exist_buff_dict(
                sim_instance=self.buff_instance.sim_instance
            )[self.equipper][self.buff_instance.ft.index]
        if self.buff_0.history.record is None:
            self.buff_0.history.record = ShadowHarmony4Record()
        self.record = self.buff_0.history.record

    def special_judge_logic(self, **kwargs):
        self.check_record_module()
        self.get_prepared(equipper="如影相随")
        loading_mission = kwargs.get("loading_mission", None)
        if loading_mission is None:
            raise ValueError(f"{self.buff_instance.ft.index}的xjuge函数中，获取loading_mission失败")
        from zsim.sim_progress.Load import LoadingMission

        if not isinstance(loading_mission, LoadingMission):
            raise TypeError
        skill_node = loading_mission.mission_node

        tick = find_tick(sim_instance=self.buff_instance.sim_instance)
        if not tick - 1 < loading_mission.get_first_hit() <= tick:
            """由于单个技能只能更新本buff一次，而本函数又只能在hit节点执行，
            所以这里需要过滤到第一个hit的节点"""
            return False
        """是冲刺攻击或是追加攻击标签时，检测技能属性是否与四件套佩戴者属性相同，如果不同则不予触发！"""
        if skill_node.element_type != self.record.char.element_type:
            return False
        if not skill_node.skill.labels:
            if skill_node.skill.trigger_buff_level == 3:
                return True
        else:
            if "aftershock_attack" in skill_node.skill.labels.keys():
                return True
        return False
