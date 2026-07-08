from typing import TYPE_CHECKING

from zsim.define import YIXUAN_REPORT

from .. import Buff, check_preparation
from ..JudgeTools import build_preparation_context_from_buff
from ._preparation_helpers import ensure_owner_template_record, prepare_with_context
from .enemy_state_read import read_enemy_stun_active

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
        return prepare_with_context(
            self,
            check_preparation_func=check_preparation,
            context_builder=build_preparation_context_from_buff,
            **kwargs,
        )

    def check_record_module(self):
        ensure_owner_template_record(
            self,
            owner_name="仪玄",
            record_factory=YixuanCinema2StunTimeLimitBonusRecord,
            context_builder=build_preparation_context_from_buff,
        )

    def special_judge_logic(self, **kwargs):
        self.check_record_module()
        self.get_prepared(char_CID=1371, enemy=1)
        skill_node: "SkillNode | None" = kwargs.get("skill_node", None)
        if skill_node is None:
            return False
        if skill_node.skill_tag != self.record.required_skill_tag:
            return False
        if not read_enemy_stun_active(self.record.enemy):
            return False
        if skill_node.preload_tick != self.buff_instance.sim_instance.tick:
            return False
        if YIXUAN_REPORT:
            print(
                "2画：检测到仪玄释放喧响值大招！敌人正处于失衡状态，2画效果生效，延长敌人3秒失衡时间！"
            )
            self.buff_instance.sim_instance.schedule_data.change_process_state()
        return True

    def special_exit_logic(self, **kwargs):
        self.check_record_module()
        self.get_prepared(char_CID=1371, enemy=1)
        if not read_enemy_stun_active(self.record.enemy):
            if YIXUAN_REPORT:
                print("2画：检测到敌人从失衡状态中恢复，仪玄2画的失衡时间延长效果结束！")
                self.buff_instance.sim_instance.schedule_data.change_process_state()
            return True
        return False
