from zsim.sim_progress.Buff import Buff, JudgeTools, check_preparation, find_tick
import math


class RainforestGourmetATKBonusRecord:
    def __init__(self):
        self.equipper = None
        self.char = None
        self.sub_exist_buff_dict = None
        self.last_update_node = None


class RainforestGourmetATKBonus(Buff.BuffLogic):
    """雨林饕客的局内攻击"""

    def __init__(self, buff_instance):
        super().__init__(buff_instance)
        self.buff_instance: Buff = buff_instance
        self.xjudge = self.special_judge_logic
        self.xstart = self.special_start_logic
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
                "雨林饕客", sim_instance=self.buff_instance.sim_instance
            )
        if self.buff_0 is None:
            self.buff_0 = JudgeTools.find_exist_buff_dict(
                sim_instance=self.buff_instance.sim_instance
            )[self.equipper][self.buff_instance.ft.index]
        if self.buff_0.history.record is None:
            self.buff_0.history.record = RainforestGourmetATKBonusRecord()
        self.record = self.buff_0.history.record

    def special_judge_logic(self, **kwargs):
        """检测到强化E标签或是支援攻击标签，则放行。如果角色处于前台则更新1层，若角色处于后台则更新两层。"""
        self.check_record_module()
        self.get_prepared(equipper="雨林饕客")
        skill_node = kwargs.get("skill_node", None)
        if skill_node is None:
            return False
        from zsim.sim_progress.Preload import SkillNode

        if not isinstance(skill_node, SkillNode):
            raise TypeError
        if skill_node.char_name != self.record.char.NAME:
            return False
        if skill_node.preload_tick != find_tick(
            sim_instance=self.buff_instance.sim_instance
        ):
            return False
        if skill_node.skill.sp_consume == 0:
            return False
        self.record.last_update_node = skill_node
        return True

    def special_start_logic(self, **kwargs):
        self.check_record_module()
        self.get_prepared(equipper="雨林饕客", sub_exist_buff_dict=1)
        sp_consume = self.record.last_update_node.skill.sp_consume
        count = math.floor(sp_consume / 10)
        self.buff_instance.simple_start(
            find_tick(sim_instance=self.buff_instance.sim_instance),
            self.record.sub_exist_buff_dict,
            individule_settled_count=count,
        )
        # print(f'雨林饕客的buff触发了！当前层数{self.buff_instance.dy.count}')
