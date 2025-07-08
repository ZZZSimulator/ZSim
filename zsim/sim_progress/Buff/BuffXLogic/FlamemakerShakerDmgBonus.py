from .. import Buff, JudgeTools, check_preparation, find_tick


class FlamemakerShakerDmgBonusRecord:
    def __init__(self):
        self.equipper = None
        self.char = None
        self.preload_data = None
        self.sub_exist_buff_dict = None


class FlamemakerShakerDmgBonus(Buff.BuffLogic):
    """灼心摇壶的增伤逻辑判定"""

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
                "灼心摇壶", sim_instance=self.buff_instance.sim_instance
            )
        if self.buff_0 is None:
            self.buff_0 = JudgeTools.find_exist_buff_dict(
                sim_instance=self.buff_instance.sim_instance
            )[self.equipper][self.buff_instance.ft.index]
        if self.buff_0.history.record is None:
            self.buff_0.history.record = FlamemakerShakerDmgBonusRecord()
        self.record = self.buff_0.history.record

    def special_judge_logic(self, **kwargs):
        """检测到强化E标签或是支援攻击标签，则放行。如果角色处于前台则更新1层，若角色处于后台则更新两层。"""
        self.check_record_module()
        self.get_prepared(equipper="灼心摇壶")
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
        if self.record is not None and self.record.equipper != skill_node.char_name:
            return False

        if skill_node.skill.trigger_buff_level == 2:
            return True
        else:
            if skill_node.skill.labels is not None:
                # 若技能有标签，则判断是否是支援攻击标签。
                if "Assist_Attack" in skill_node.skill.labels:
                    return True
                else:
                    return False

    def special_hit_logic(self, **kwargs):
        self.check_record_module()
        self.get_prepared(equipper="灼心摇壶", preload_data=1, sub_exist_buff_dict=1)
        if self.record.preload_data.operating_now != self.record.char.CID:
            # 说明此时角色正位于后台，更新两层。
            self.buff_instance.simple_start(
                find_tick(sim_instance=self.buff_instance.sim_instance),
                self.record.sub_exist_buff_dict,
                no_count=1,
            )
            self.buff_instance.dy.count = min(
                self.buff_instance.dy.count + 2, self.buff_instance.ft.maxcount
            )
        else:
            self.buff_instance.simple_start(
                find_tick(sim_instance=self.buff_instance.sim_instance),
                self.record.sub_exist_buff_dict,
            )

        self.buff_instance.update_to_buff_0(self.buff_0)
        # print(f'灼心摇壶更新了{update_count}层，当前层数为：{self.buff_0.dy.count}')
