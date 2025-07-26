from .. import Buff, JudgeTools, check_preparation, find_tick


class RiotSuppressorMarkVIRecord:
    def __init__(self):
        self.equipper = None
        self.char = None
        self.max_effect_times = 8
        self.available_effect_times = 0
        self.active_signal = None
        self.sub_exist_buff_dict = None


class RiotSuppressorMarkVI(Buff.BuffLogic):
    """防暴者Ⅵ型的复杂逻辑"""

    def __init__(self, buff_instance):
        super().__init__(buff_instance)
        self.buff_instance: Buff = buff_instance
        self.xjudge = self.special_judge_logic
        self.xeffect = self.special_effect_logic
        self.xexit = self.special_exit_logic
        self.equipper = None
        self.buff_0 = None
        self.record = None

    def get_prepared(self, **kwargs):
        return check_preparation(buff_instance=self.buff_instance, buff_0=self.buff_0, **kwargs)

    def check_record_module(self):
        if self.equipper is None:
            self.equipper = JudgeTools.find_equipper(
                "防暴者Ⅵ型", sim_instance=self.buff_instance.sim_instance
            )
        if self.buff_0 is None:
            self.buff_0 = JudgeTools.find_exist_buff_dict(
                sim_instance=self.buff_instance.sim_instance
            )[self.equipper][self.buff_instance.ft.index]
        if self.buff_0.history.record is None:
            self.buff_0.history.record = RiotSuppressorMarkVIRecord()
        self.record = self.buff_0.history.record

    def special_judge_logic(self, **kwargs):
        """检测到强化E和普攻都放行。强化E叠层，普攻消层。"""
        self.check_record_module()
        self.get_prepared(equipper="防暴者Ⅵ型")
        if self.buff_0.dy.active and self.record.available_effect_times < 1:
            raise ValueError(f"{self.buff_instance.ft.index}在可用层数耗尽的情况下仍保持激活状态！")
        skill_node = kwargs.get("skill_node", None)
        if skill_node is None:
            return False
        from zsim.sim_progress.Preload import SkillNode

        if not isinstance(skill_node, SkillNode):
            raise ValueError(
                f"{self.buff_instance.ft.index}的xjudge函数获取的skill_node不是SkillNode类型！"
            )
        if self.record.char.NAME != skill_node.char_name:
            return False
        if skill_node.skill.trigger_buff_level not in [2, 0]:
            return False

        """Buff的触发，还有生效次数的消耗，都只有在技能释放时才会执行。"""
        if skill_node.preload_tick == find_tick(sim_instance=self.buff_instance.sim_instance):
            signal = skill_node.skill.trigger_buff_level
            if skill_node.skill.trigger_buff_level == 0:
                if not self.buff_0.dy.active:
                    signal = None
        else:
            signal = None
        if signal is not None:
            if self.record.active_signal is not None:
                raise ValueError(
                    f"{self.buff_instance.ft.index}的Xjudge函数检测到尚未结算的更新信号{self.record.active_signal}！"
                )
            self.record.active_signal = signal
            return True
        else:
            return False

    def special_effect_logic(self, **kwargs):
        self.check_record_module()
        self.get_prepared(equipper="防暴者Ⅵ型", sub_exist_buff_dict=1)
        if self.record.active_signal == 2:
            """更新信号为2是时，刷新Buff，叠加生效层数。"""
            self.record.available_effect_times = min(
                self.record.available_effect_times + self.record.max_effect_times,
                self.record.max_effect_times,
            )
            self.buff_instance.simple_start(
                find_tick(sim_instance=self.buff_instance.sim_instance),
                self.record.sub_exist_buff_dict,
            )
            # print(
            #     f"防暴者VI型Buff触发了！当前可用次数为{self.record.available_effect_times}！"
            # )
        elif self.record.active_signal == 0:
            """更新信号为0时，消耗层数。"""
            if self.record.available_effect_times < 1:
                raise ValueError(f"{self.buff_instance.ft.index}的剩余层数不足，无法消耗层数！")
            self.record.available_effect_times -= 1
            # print(
            #     f"检测到普攻发动！消耗1层！当前层数为：{self.record.available_effect_times}！"
            # )
        else:
            raise ValueError(
                f"{self.buff_instance.ft.index}的Xeffect函数获取到了无法解析的信号{self.record.active_signal}！"
            )
        self.record.active_signal = None

    def special_exit_logic(self, **kwargs):
        self.check_record_module()
        self.get_prepared(equipper="防暴者Ⅵ型")

        if self.record.available_effect_times < 1:
            return True
        else:
            return False
