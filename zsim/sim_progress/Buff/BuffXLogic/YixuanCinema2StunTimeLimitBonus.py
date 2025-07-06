from typing import TYPE_CHECKING

from zsim.define import YIXUAN_REPORT

from .. import Buff, JudgeTools, check_preparation

if TYPE_CHECKING:
    from zsim.sim_progress.Preload import SkillNode


class YixuanCinema2StunTimeLimitBonusRecord:
    def __init__(self):
        self.char = None
        self.enemy = None
        self.required_skill_tag = "1371_Q"


class YixuanCinema2StunTimeLimitBonus(Buff.BuffLogic):
    """仪玄2画效果：增加怪物失衡时间"""

    def __init__(self, buff_instance):
        super().__init__(buff_instance)
        self.buff_instance: Buff = buff_instance
        self.xjudge = self.special_judge_logic
        self.xexit = self.special_exit_logic
        self.buff_0 = None
        self.record = None

    def get_prepared(self, **kwargs):
        return check_preparation(
            buff_instance=self.buff_instance, buff_0=self.buff_0, **kwargs
        )

    def check_record_module(self):
        if self.buff_0 is None:
            self.buff_0 = JudgeTools.find_exist_buff_dict(
                sim_instance=self.buff_instance.sim_instance
            )["仪玄"][self.buff_instance.ft.index]
        if self.buff_0.history.record is None:
            self.buff_0.history.record = YixuanCinema2StunTimeLimitBonusRecord()
        self.record = self.buff_0.history.record

    def special_judge_logic(self, **kwargs):
        self.check_record_module()
        self.get_prepared(char_CID=1371, enemy=1)
        skill_node: "SkillNode | None" = kwargs.get("skill_node", None)
        if skill_node is None:
            return False
        if skill_node.skill_tag != self.record.required_skill_tag:
            return False
        if not self.record.enemy.dynamic.stun:
            return False
        if skill_node.preload_tick != self.buff_instance.sim_instance.tick:
            return False
        print(
            "2画：检测到仪玄释放喧响值大招！敌人正处于失衡状态，2画效果生效，延长敌人3秒失衡时间！"
        ) if YIXUAN_REPORT else None
        return True

    def special_exit_logic(self, **kwargs):
        self.check_record_module()
        self.get_prepared(char_CID=1371, enemy=1)
        if not self.record.enemy.dynamic.stun:
            print(
                "2画：检测到敌人从失衡状态中恢复，仪玄2画的失衡时间延长效果结束！"
            ) if YIXUAN_REPORT else None
            return True
        return False
