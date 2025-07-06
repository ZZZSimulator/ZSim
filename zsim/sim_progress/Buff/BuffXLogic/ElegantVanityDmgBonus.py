from .. import Buff, JudgeTools, check_preparation


class ElegantVanityDmgBonusRecord:
    def __init__(self):
        self.equipper = None
        self.char = None
        self.last_update_tick_node = None


class ElegantVanityDmgBonus(Buff.BuffLogic):
    """玲珑妆匣的全队增伤Buff逻辑。"""

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
                "玲珑妆匣", sim_instance=self.buff_instance.sim_instance
            )
        if self.buff_0 is None:
            self.buff_0 = JudgeTools.find_exist_buff_dict(
                sim_instance=self.buff_instance.sim_instance
            )[self.equipper][self.buff_instance.ft.index]
        if self.buff_0.history.record is None:
            self.buff_0.history.record = ElegantVanityDmgBonusRecord()
        self.record = self.buff_0.history.record

    def special_judge_logic(self, **kwargs):
        """
        判断传入的skill_node的能耗是否>=25，如果是则放行
        """
        self.check_record_module()
        self.get_prepared(equipper="玲珑妆匣")
        skill_node = kwargs.get("skill_node", None)
        if skill_node is None:
            raise ValueError(
                f"{self.buff_instance.ft.index}的Xjudge函数获取到的skill_node为None！"
            )
        from zsim.sim_progress.Preload import SkillNode

        if not isinstance(skill_node, SkillNode):
            raise TypeError(
                f"{self.buff_instance.ft.index}的Xjudge函数获取到的skill_node类型错误！"
            )
        # 过滤不是自己的skill_node
        if skill_node.char_name != self.record.char.NAME:
            return False
        if skill_node.preload_tick < JudgeTools.find_tick(
            sim_instance=self.buff_instance.sim_instance
        ):
            return False
        if skill_node.skill.sp_consume >= 25:
            if self.record.last_update_tick_node is None:
                self.record.last_update_tick_node = skill_node
                # print(f'增伤Buff因{skill_node.skill_tag}触发！')
                return True
            else:
                if self.record.last_update_tick_node.UUID != skill_node.UUID:
                    self.record.last_update_tick_node = skill_node
                    # print(f'增伤Buff因{skill_node.skill_tag}触发！')
                    return True
        return False
