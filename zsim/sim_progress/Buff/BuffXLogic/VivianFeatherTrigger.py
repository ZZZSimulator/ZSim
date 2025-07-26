from .. import Buff, JudgeTools, check_preparation, find_tick


class VivianFeatherTriggerRecord:
    def __init__(self):
        self.char = None
        self.last_update_node = None


class VivianFeatherTrigger(Buff.BuffLogic):
    def __init__(self, buff_instance):
        """管理薇薇安羽毛更新的触发器"""
        super().__init__(buff_instance)
        self.buff_instance: Buff = buff_instance
        self.buff_0 = None
        self.record = None
        self.xjudge = self.special_judge_logic
        self.xhit = self.special_hit_logic

    def get_prepared(self, **kwargs):
        return check_preparation(buff_instance=self.buff_instance, buff_0=self.buff_0, **kwargs)

    def check_record_module(self):
        if self.buff_0 is None:
            self.buff_0 = JudgeTools.find_exist_buff_dict(
                sim_instance=self.buff_instance.sim_instance
            )["薇薇安"][self.buff_instance.ft.index]
        if self.buff_0.history.record is None:
            self.buff_0.history.record = VivianFeatherTriggerRecord()
        self.record = self.buff_0.history.record

    def special_judge_logic(self, **kwargs):
        """检测到最后一跳时放行"""
        self.check_record_module()
        self.get_prepared(char_CID=1331)
        skill_node = kwargs.get("skill_node", None)
        if skill_node is None:
            return False
        from zsim.sim_progress.Preload import SkillNode

        if not isinstance(skill_node, SkillNode):
            raise TypeError(
                f"{self.buff_instance.ft.index}的xjudge函数获取的skill_node不是SkillNode类型"
            )

        # 过滤掉不是自己的skill_node
        if "1331" not in skill_node.skill_tag:
            return False

        # 放行所有正处于最后一跳的skill_node
        tick = find_tick(sim_instance=self.buff_instance.sim_instance)
        if skill_node.loading_mission.is_last_hit(tick):
            self.record.last_update_node = skill_node
            return True
        else:
            return False

    def special_hit_logic(self, **kwargs):
        """只要触发器放行了，那么special_hit就一定会执行，执行一次后，把record清空即可。"""
        self.check_record_module()
        self.get_prepared(char_CID=1331)
        self.record.char.feather_manager.update_myself(self.record.last_update_node)
        self.record.last_update_node = None
