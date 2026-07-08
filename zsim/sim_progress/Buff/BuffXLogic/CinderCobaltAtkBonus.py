from zsim.sim_progress.Buff import Buff, check_preparation, find_tick
from zsim.sim_progress.Buff.BuffXLogic._preparation_helpers import (
    ensure_equipper_template_record,
    prepare_with_context,
)
from zsim.sim_progress.Buff.JudgeTools import build_preparation_context_from_buff


class CinderCobaltAtkBonusRecord:
    def __init__(self):
        self.equipper = None
        self.char = None
        self.listener = None


class CinderCobaltAtkBonus(Buff.BuffLogic):
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
            item_name="「灰烬」-钴蓝",
            record_factory=CinderCobaltAtkBonusRecord,
            context_builder=build_preparation_context_from_buff,
        )

    def special_judge_logic(self, **kwargs):
        self.check_record_module()
        self.get_prepared(equipper="「灰烬」-钴蓝")
        if self.record.listener is None:
            self.record.listener = self.buff_instance.sim_instance.listener_manager.get_listener(
                listener_owner=self.record.char,
                listener_id=self.buff_instance.ft.listener_id,
            )
        active_signal = self.record.listener.active_signal
        if active_signal is None:
            return False
        if active_signal[0].NAME != self.record.char.NAME:
            return False
        else:
            self.record.listener.active_signal = None
            if self.buff_0.is_ready(find_tick(sim_instance=self.buff_instance.sim_instance)):
                # print(
                #     f"{self.buff_instance.ft.index}接收到了匹配的更新信号（佩戴者为{active_signal[0].NAME}）"
                # )
                return True
            else:
                return False
