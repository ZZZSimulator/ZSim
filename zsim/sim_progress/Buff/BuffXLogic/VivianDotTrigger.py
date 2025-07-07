from zsim.define import VIVIAN_REPORT

from .. import Buff, JudgeTools, check_preparation, find_tick


class VivianDotTriggerRecord:
    def __init__(self):
        self.char = None
        self.enemy = None


class VivianDotTrigger(Buff.BuffLogic):
    def __init__(self, buff_instance):
        """薇薇安的Dot（薇薇安的预言）触发器"""
        super().__init__(buff_instance)
        self.buff_instance: Buff = buff_instance
        self.buff_0 = None
        self.record = None
        self.xjudge = self.special_judge_logic
        self.xhit = self.special_hit_logic

    def get_prepared(self, **kwargs):
        return check_preparation(
            buff_instance=self.buff_instance, buff_0=self.buff_0, **kwargs
        )

    def check_record_module(self):
        if self.buff_0 is None:
            self.buff_0 = JudgeTools.find_exist_buff_dict(
                sim_instance=self.buff_instance.sim_instance
            )["薇薇安"][self.buff_instance.ft.index]
        if self.buff_0.history.record is None:
            self.buff_0.history.record = VivianDotTriggerRecord()
        self.record = self.buff_0.history.record

    def special_judge_logic(self, **kwargs):
        """检测到敌人处于属性异常状态，并且是SNA2或者是协同攻击时，放行"""
        self.check_record_module()
        self.get_prepared(char_CID=1331, enemy=1)
        skill_node = kwargs.get("skill_node", None)
        if skill_node is None:
            return False
        from zsim.sim_progress.Preload import SkillNode

        if not isinstance(skill_node, SkillNode):
            raise TypeError(
                f"{self.buff_instance.ft.index}的Xjudge函数获取到的skill_node不是SkillNode类型，请检查！"
            )
        # 筛选出能够触发dot的SNA_2和生花
        if skill_node.skill_tag not in ["1331_SNA_2", "1331_CoAttack_A"]:
            return False

        # 检测到当前tick有命中时，放行。
        tick = find_tick(sim_instance=self.buff_instance.sim_instance)
        if not skill_node.loading_mission.is_hit_now(tick):
            return False

        # 如果敌人不处于异常状态，不放行
        if not self.record.enemy.dynamic.is_under_anomaly():
            return False

        return True

    def special_hit_logic(self, **kwargs):
        """xjudge放行后，直接生成dot。但是如果dot已经存在，就不重复生成。"""
        self.check_record_module()
        self.get_prepared(char_CID=1361, enemy=1)
        # 如果敌人身上已经存在这个dot，直接不执行
        if self.record.enemy.find_dot("ViviansProphecy") is not None:
            return
        from zsim.sim_progress.Load import LoadingMission
        from zsim.sim_progress.Update.UpdateAnomaly import spawn_normal_dot

        dot = spawn_normal_dot(
            "ViviansProphecy", sim_instance=self.buff_instance.sim_instance
        )
        dot.start(find_tick(sim_instance=self.buff_instance.sim_instance))
        event_list = JudgeTools.find_event_list(
            sim_instance=self.buff_instance.sim_instance
        )
        dot.skill_node_data.loading_mission = LoadingMission(dot.skill_node_data)
        dot.skill_node_data.loading_mission.mission_start(
            find_tick(sim_instance=self.buff_instance.sim_instance)
        )
        self.record.enemy.dynamic.dynamic_dot_list.append(dot)
        event_list.append(dot.skill_node_data)
        print("核心被动：薇薇安对敌人施加Dot——薇薇安的预言") if VIVIAN_REPORT else None
