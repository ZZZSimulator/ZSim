from .. import Buff, check_preparation, find_tick
from ..JudgeTools import build_preparation_context_from_buff
from ._preparation_helpers import ensure_owner_template_record, prepare_with_context


class AstraYaoQuickAssistManagerTriggerRecord:
    def __init__(self):
        self.char = None


class AstraYaoQuickAssistManagerTrigger(Buff.BuffLogic):
    def __init__(self, buff_instance):
        """耀嘉音快支管理器的触发器，该触发器只负责把skill_node或者loading_mission扔给特殊资源模块。"""
        super().__init__(buff_instance)
        self.buff_instance: Buff = buff_instance
        self.buff_0 = None
        self.record = None
        self.xjudge = self.special_judge_logic
        self.xeffect = self.special_effect_logic

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
            owner_name="耀嘉音",
            record_factory=AstraYaoQuickAssistManagerTriggerRecord,
            context_builder=build_preparation_context_from_buff,
        )

    def special_judge_logic(self, **kwargs):
        return True

    def special_effect_logic(self, **kwargs):
        """通过简单判定之后，执行special_effect_logic"""
        self.check_record_module()
        self.get_prepared(char_CID=1311)
        skill_node = kwargs.get("skill_node", None)
        if skill_node is None:
            return
        self.record.char.chord_manager.quick_assist_trigger_manager.update_myself(
            find_tick(sim_instance=self.buff_instance.sim_instance), skill_node
        )
        # if ASTRAYAO_REPORT:
        #     print(f'检测到攻击动作命中，尝试调用快支管理器！')
