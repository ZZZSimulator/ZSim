from zsim.define import ASTRAYAO_REPORT

from .. import Buff, check_preparation, find_tick
from ..JudgeTools import build_preparation_context_from_buff
from ._preparation_helpers import ensure_owner_template_record, prepare_with_context


class AstraYaoChordManagerTriggerRecord:
    def __init__(self):
        self.char = None
        self.last_update_node = None


class AstraYaoChordManagerTrigger(Buff.BuffLogic):
    def __init__(self, buff_instance):
        """耀嘉音震音管理器触发器，负责调用震音管理器并尝试添加协同攻击。"""
        super().__init__(buff_instance)
        self.buff_instance: Buff = buff_instance
        self.buff_0 = None
        self.record = None
        self.xjudge = self.special_judge_logic
        self.xstart = self.special_start_logic

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
            record_factory=AstraYaoChordManagerTriggerRecord,
            context_builder=build_preparation_context_from_buff,
        )

    def special_judge_logic(self, **kwargs):
        """放行所有的符合条件的技能"""
        self.check_record_module()
        self.get_prepared(char_CID=1311)
        skill_node = kwargs["skill_node"]
        if skill_node.skill.trigger_buff_level in [5, 7, 8]:
            if find_tick(sim_instance=self.buff_instance.sim_instance) == skill_node.preload_tick:
                self.record.last_update_node = skill_node
                return True
        return False

    def special_start_logic(self, **kwargs):
        """special_start函数只会在动作开始时执行，控制了执行的次数，防止重复触发。"""
        self.check_record_module()
        self.get_prepared(char_CID=1311)
        char = self.record.char
        skill_node = self.record.last_update_node
        from zsim.sim_progress.Character.AstraYao import AstraYao

        if not isinstance(char, AstraYao):
            raise TypeError("record.char is not AstraYao")
        char.chord_manager.chord_trigger.try_spawn_chord_coattack(
            find_tick(sim_instance=self.buff_instance.sim_instance),
            skill_node=skill_node,
        )
        if ASTRAYAO_REPORT:
            self.buff_instance.sim_instance.schedule_data.change_process_state()
            print(f"检测到入场动作{skill_node.skill_tag}，尝试调用震音管理器，触发协同攻击！")
