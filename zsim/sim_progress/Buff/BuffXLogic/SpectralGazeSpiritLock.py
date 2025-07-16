from .. import Buff, JudgeTools, check_preparation, find_tick


class SpectralGazeSpiritLockRecord:
    def __init__(self):
        self.equipper = None
        self.char = None
        self.preload_data = None
        self.last_update_node_id = None


class SpectralGazeSpiritLock(Buff.BuffLogic):
    """扳机专武索魂影眸第二特效——魂锁，"""

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
                "索魂影眸", sim_instance=self.buff_instance.sim_instance
            )
        if self.buff_0 is None:
            """
            这里的初始化，找到的buff_0实际上是佩戴者的buff_0
            """
            self.buff_0 = JudgeTools.find_exist_buff_dict(
                sim_instance=self.buff_instance.sim_instance
            )[self.equipper][self.buff_instance.ft.index]
        if self.buff_0.history.record is None:
            self.buff_0.history.record = SpectralGazeSpiritLockRecord()
        self.record = self.buff_0.history.record

    def special_judge_logic(self, **kwargs):
        """
        装备者的[追加攻击]命中敌人并造成电属性伤害时,
        若当前角色处于后台（并非主操角色），返回True，
        同一招式内最多触发一次（这里利用了skill_node 的一个新增功能：独立ID）
        """
        self.check_record_module()
        self.get_prepared(equipper="索魂影眸", preload_data=1)
        tick = find_tick(sim_instance=self.buff_instance.sim_instance)
        skill_node = kwargs.get("skill_node")
        loading_mission = kwargs.get("loading_mission")
        """逻辑外壳和专武的第一特效没有区别"""
        if skill_node is None:
            raise ValueError(
                f"{self.buff_instance.ft.index}的xjudge中缺少skill_node参数"
            )
        from zsim.sim_progress.Preload import SkillNode

        if not isinstance(skill_node, SkillNode):
            raise TypeError
        if not loading_mission.is_hit_now(tick):
            return False
        if str(self.record.char.CID) not in skill_node.skill_tag:
            return False
        if not skill_node.skill.labels:
            return False
        if (
            skill_node.element_type == 3
            and "aftershock_attack" in skill_node.skill.labels
        ):
            if self.record.preload_data.operating_now != self.record.char.CID:
                node_id = skill_node.get_total_instances()
                if node_id != self.record.last_update_node_id:
                    self.record.last_update_node_id = node_id
                    return True
        return False
