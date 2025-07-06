from .. import Buff, JudgeTools, check_preparation, find_tick


class TimeweaverApBonusRecord:
    def __init__(self):
        self.equipper = None
        self.char = None
        self.enemy = None


class TimeweaverApBonus(Buff.BuffLogic):
    """时流贤者的电属性积蓄相关Buff逻辑。"""

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
                "时流贤者", sim_instance=self.buff_instance.sim_instance
            )
        if self.buff_0 is None:
            self.buff_0 = JudgeTools.find_exist_buff_dict(
                sim_instance=self.buff_instance.sim_instance
            )[self.equipper][self.buff_instance.ft.index]
        if self.buff_0.history.record is None:
            self.buff_0.history.record = TimeweaverApBonusRecord()
        self.record = self.buff_0.history.record

    def special_judge_logic(self, **kwargs):
        """时流贤者的电属性积蓄相关Buff的核心逻辑。"""
        self.check_record_module()
        self.get_prepared(equipper="时流贤者", enemy=1)
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

        # 判断skill node的trigger_buff_level是否为1或2
        if skill_node.skill.trigger_buff_level not in [1, 2]:
            return False

        # 判断当前是否是hit节点
        if not skill_node.loading_mission.is_hit_now(
            find_tick(sim_instance=self.buff_instance.sim_instance)
        ):
            return False

        # 判断敌人是否处于异常状态
        if not self.record.enemy.dynamic.is_under_anomaly():
            return False

        return True
