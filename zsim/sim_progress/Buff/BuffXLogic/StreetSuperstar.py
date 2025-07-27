from .. import Buff, JudgeTools, check_preparation, find_tick


class StreetSuperstarRecord:
    def __init__(self):
        self.equipper = None
        self.char = None
        self.sub_exist_buff_dict = None
        self.qte_counter = 0
        self.max_qte = 3
        self.active_signal = None


class StreetSuperstar(Buff.BuffLogic):
    """街头巨星的逻辑核心：任意角色释放QTE叠层、装备者释放大招触发。"""

    def __init__(self, buff_instance):
        super().__init__(buff_instance)
        self.buff_instance: Buff = buff_instance
        self.xjudge = self.special_judge_logic
        self.xstart = self.special_start_logic
        self.equipper = None
        self.buff_0 = None
        self.record = None

    def get_prepared(self, **kwargs):
        return check_preparation(buff_instance=self.buff_instance, buff_0=self.buff_0, **kwargs)

    def check_record_module(self):
        if self.equipper is None:
            self.equipper = JudgeTools.find_equipper(
                "街头巨星", sim_instance=self.buff_instance.sim_instance
            )
        if self.buff_0 is None:
            self.buff_0 = JudgeTools.find_exist_buff_dict(
                sim_instance=self.buff_instance.sim_instance
            )[self.equipper][self.buff_instance.ft.index]
        if self.buff_0.history.record is None:
            self.buff_0.history.record = StreetSuperstarRecord()
        self.record = self.buff_0.history.record

    def special_judge_logic(self, **kwargs):
        self.check_record_module()
        self.get_prepared(equipper="街头巨星")
        skill_node = kwargs.get("skill_node", None)
        if skill_node is None:
            return False
        from zsim.sim_progress.Preload import SkillNode

        if not isinstance(skill_node, SkillNode):
            raise TypeError(
                f"{self.buff_instance.ft.index}的xjudge函数获取到的skill_node不是SkillNode类型"
            )
        if not skill_node.preload_tick == find_tick(sim_instance=self.buff_instance.sim_instance):
            return False
        if skill_node.skill.trigger_buff_level == 5:
            self.record.qte_counter = min(self.record.qte_counter + 1, self.record.max_qte)
        elif skill_node.skill.trigger_buff_level == 6:
            if skill_node.char_name == self.record.char.NAME:
                self.record.active_signal = skill_node
                return True
        return False

    def special_start_logic(self, **kwargs):
        self.check_record_module()
        self.get_prepared(equipper="街头巨星", sub_exist_buff_dict=1)
        if self.record.qte_counter == 0:
            return
        self.buff_instance.simple_start(
            find_tick(sim_instance=self.buff_instance.sim_instance),
            self.record.sub_exist_buff_dict,
            specified_count=self.record.qte_counter,
            no_end=1,
        )
        self.buff_instance.dy.endticks = (
            find_tick(sim_instance=self.buff_instance.sim_instance)
            + self.record.active_signal.skill.ticks
        )
        self.buff_instance.update_to_buff_0(self.buff_0)

        self.record.qte_counter = 0
        self.active_signal = None
