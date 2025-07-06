from .. import Buff, JudgeTools, check_preparation, find_tick
from zsim.define import ASTRAYAO_REPORT


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
        return check_preparation(
            buff_instance=self.buff_instance, buff_0=self.buff_0, **kwargs
        )

    def check_record_module(self):
        if self.buff_0 is None:
            self.buff_0 = JudgeTools.find_exist_buff_dict(
                sim_instance=self.buff_instance.sim_instance
            )["耀嘉音"][self.buff_instance.ft.index]
        if self.buff_0.history.record is None:
            self.buff_0.history.record = AstraYaoChordManagerTriggerRecord()
        self.record = self.buff_0.history.record

    def special_judge_logic(self, **kwargs):
        """放行所有的符合条件的技能"""
        self.check_record_module()
        self.get_prepared(char_CID=1311)
        skill_node = kwargs["skill_node"]
        if skill_node.skill.trigger_buff_level in [5, 7, 8]:
            if (
                find_tick(sim_instance=self.buff_instance.sim_instance)
                == skill_node.preload_tick
            ):
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
            print(
                f"检测到入场动作{skill_node.skill_tag}，尝试调用震音管理器，触发协同攻击！"
            )
