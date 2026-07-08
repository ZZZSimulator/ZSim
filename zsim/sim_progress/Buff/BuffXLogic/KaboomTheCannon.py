from .. import Buff, JudgeTools, check_preparation
from ..JudgeTools import build_preparation_context_from_buff
from ._preparation_helpers import ensure_equipper_template_record, prepare_with_context


class KaboomTheCannonRecord:
    def __init__(self):
        self.equipper = None
        self.char = None
        self.action_stack = None
        self.active_char_dict = {}
        self.sub_exist_buff_dict = None


class KaboomTheCannon(Buff.BuffLogic):
    """
    好斗的阿炮的复杂逻辑模块。主要是“1人只能提供1层”这个部分的约束
    """

    def __init__(self, buff_instance):
        super().__init__(buff_instance)
        self.buff_instance: Buff = buff_instance
        self.xhit = self.special_hit_logic
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
            item_name="好斗的阿炮",
            record_factory=KaboomTheCannonRecord,
            context_builder=build_preparation_context_from_buff,
        )

    def special_hit_logic(self, **kwargs):
        """主要归档触发源。"""
        # TODO: 等三只小猪加入了，可能还得重新弄。
        self.check_record_module()
        self.get_prepared(equipper="好斗的阿炮", action_stack=1, sub_exist_buff_dict=1)
        action_now = self.record.action_stack.peek()
        tick_now = JudgeTools.find_tick(sim_instance=self.buff_instance.sim_instance)
        self.record.active_char_dict[action_now.mission_character] = [
            tick_now,
            tick_now + self.buff_instance.ft.maxduration,
        ]
        for names, tick_list in self.record.active_char_dict.copy().items():
            if tick_list[1] <= tick_now:
                del self.record.active_char_dict[names]
        self.buff_instance.simple_start(tick_now, self.record.sub_exist_buff_dict, not_count=True)
        input_list = list(self.record.active_char_dict.values())
        self.buff_instance.dy.built_in_buff_box = input_list
        self.buff_instance.update_to_buff_0(self.buff_0)
