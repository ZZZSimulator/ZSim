from .. import Buff, check_preparation, find_tick
from ..JudgeTools import build_preparation_context_from_buff
from ._preparation_helpers import ensure_equipper_template_record, prepare_with_context
from .enemy_anomaly_read import read_enemy_anomaly_active


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
        return prepare_with_context(
            self,
            check_preparation_func=check_preparation,
            context_builder=build_preparation_context_from_buff,
            **kwargs,
        )

    def check_record_module(self):
        ensure_equipper_template_record(
            self,
            item_name="时流贤者",
            record_factory=TimeweaverApBonusRecord,
            context_builder=build_preparation_context_from_buff,
        )

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
        prepared_char_name = (
            self.record.char.NAME if self.record.char is not None else self.record.equipper
        )
        if prepared_char_name != skill_node.char_name:
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
        if not read_enemy_anomaly_active(self.record.enemy):
            return False

        return True
