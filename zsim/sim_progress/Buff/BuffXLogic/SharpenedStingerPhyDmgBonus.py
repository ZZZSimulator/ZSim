from .. import Buff, JudgeTools, check_preparation, find_tick


class SharpenedStingerPhyDmgBonusRecord:
    def __init__(self):
        self.equipper = None
        self.char = None
        self.update_signal = None
        self.preload_data = None
        self.sub_exist_buff_dict = None


class SharpenedStingerPhyDmgBonus(Buff.BuffLogic):
    """淬锋钳刺的 猎意复杂逻辑"""

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
                "淬锋钳刺", sim_instance=self.buff_instance.sim_instance
            )
        if self.buff_0 is None:
            self.buff_0 = JudgeTools.find_exist_buff_dict(
                sim_instance=self.buff_instance.sim_instance
            )[self.equipper][self.buff_instance.ft.index]
        if self.buff_0.history.record is None:
            self.buff_0.history.record = SharpenedStingerPhyDmgBonusRecord()
        self.record = self.buff_0.history.record

    def special_judge_logic(self, **kwargs):
        """淬锋钳刺的猎意触发逻辑。"""
        self.check_record_module()
        self.get_prepared(equipper="淬锋钳刺", preload_data=1)
        skill_node = kwargs.get("skill_node", None)
        if skill_node is None:
            return False
        from zsim.sim_progress.Preload import SkillNode

        if not isinstance(skill_node, SkillNode):
            raise TypeError(
                f"{self.buff_instance.ft.index}的xjudge函数获取的skill_node不是SkillNode类！"
            )

        # 过滤不是自己的skill_node
        if self.record.char.NAME != skill_node.char_name:
            return False
        self.buff_0.ready_judge(find_tick(sim_instance=self.buff_instance.sim_instance))
        if not self.buff_0.dy.ready:
            return False

        if self.record.preload_data.personal_node_stack[self.record.char.CID].__len__() <= 1:
            self.record.update_signal = 1
            return True

        # 判断是否为冲刺攻击或闪避反击
        if skill_node.skill.trigger_buff_level not in [3, 4]:
            return False
        if skill_node.skill.trigger_buff_level in [3]:
            self.record.update_signal = 0
        elif skill_node.skill.trigger_buff_level == 4:
            self.record.update_signal = 1
        return True

    def special_start_logic(self, **kwargs):
        self.check_record_module()
        self.get_prepared(equipper="淬锋钳刺", preload_data=1, sub_exist_buff_dict=1)
        if self.record.update_signal is None:
            return
        if self.record.update_signal == 0:
            self.buff_instance.simple_start(
                find_tick(sim_instance=self.buff_instance.sim_instance),
                self.record.sub_exist_buff_dict,
            )
        elif self.record.update_signal == 1:
            self.buff_instance.simple_start(
                find_tick(sim_instance=self.buff_instance.sim_instance),
                self.record.sub_exist_buff_dict,
                no_count=1,
            )
            self.buff_instance.dy.count = self.buff_instance.ft.maxcount
            self.buff_instance.update_to_buff_0(self.buff_0)
