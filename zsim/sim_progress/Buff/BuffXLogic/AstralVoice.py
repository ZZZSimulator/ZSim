from .. import Buff, check_preparation, find_tick
from ..JudgeTools import (
    TriggerBuffRef,
    build_preparation_context_from_buff,
    read_trigger_buff_state,
)
from ._preparation_helpers import ensure_equipper_template_record, prepare_with_context


class AstralVoiceRecord:
    def __init__(self):
        self.equipper = None
        self.char = None
        self.trigger_buff_0 = None
        self.sub_exist_buff_dict = None
        self.action_stack = None


class AstralVoice(Buff.BuffLogic):
    """
    这是静听佳音四件套的生效逻辑。该Buff有一个“触发器”，
    该触发器由简单逻辑控制，会根据支援突击触发、叠层和刷新；
    而触发器本身并无效果，真正实现增伤和复杂判定的是本buff的逻辑模块。
    本模块由 复杂判定（xjudge）  和 复杂生效（xstart） 两个部分构成
    """

    def __init__(self, buff_instance):
        super().__init__(buff_instance)
        self.buff_instance: Buff = buff_instance
        self.xjudge = self.special_judge_logic
        self.xeffect = self.special_effect_logic
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
            item_name="静听嘉音",
            record_factory=AstralVoiceRecord,
            context_builder=build_preparation_context_from_buff,
        )

    def special_judge_logic(self, **kwargs):
        """
        复杂判定逻辑：首先要检测触发器Buff的激活情况；
        即：trigger_buff_0.dy.active
        然后是对比trigger_buff_level，对比通过才能输出True
        """
        self.check_record_module()
        self.get_prepared(
            equipper="静听嘉音",
            trigger_buff_0=TriggerBuffRef.owner(
                self.buff_instance.ft.operator,
                "Buff-驱动盘-静听嘉音-嘉音",
            ),
            action_stack=1,
        )
        tick_now = find_tick(sim_instance=self.buff_instance.sim_instance)
        trigger_state = read_trigger_buff_state(self.record)

        skill_node = kwargs.get("skill_node", None)
        if skill_node is None:
            return False
        from zsim.sim_progress.Load import LoadingMission
        from zsim.sim_progress.Preload import SkillNode

        if isinstance(skill_node, SkillNode):
            pass
        elif isinstance(skill_node, LoadingMission):
            skill_node = skill_node.mission_node
        if trigger_state.active and skill_node.skill.trigger_buff_level == 7:
            if skill_node.loading_mission.mission_dict.get(tick_now, None) == "start":
                return True
            else:
                return False
        else:
            return False

    def special_effect_logic(self, **kwargs):
        self.check_record_module()
        self.get_prepared(
            equipper="静听嘉音",
            trigger_buff_0=TriggerBuffRef.owner(
                self.buff_instance.ft.operator,
                "Buff-驱动盘-静听嘉音-嘉音",
            ),
            sub_exist_buff_dict=1,
        )
        tick_now = find_tick(sim_instance=self.buff_instance.sim_instance)
        self.buff_instance.simple_start(tick_now, self.record.sub_exist_buff_dict)
        self.buff_instance.dy.count = read_trigger_buff_state(self.record).count
        self.buff_instance.update_to_buff_0(self.buff_0)
