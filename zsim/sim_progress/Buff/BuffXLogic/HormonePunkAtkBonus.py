from .. import Buff, check_preparation, find_tick
from ..JudgeTools import build_preparation_context_from_buff
from ._preparation_helpers import ensure_equipper_template_record, prepare_with_context


class HormonePunkAtkBonusRecord:
    def __init__(self):
        self.equipper = None
        self.char = None
        self.listener_exist = False
        self.listener = None


class HormonePunkAtkBonus(Buff.BuffLogic):
    """激素朋克的复杂逻辑模块，检测到监听器更新信号时更新。"""

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
            item_name="激素朋克",
            record_factory=HormonePunkAtkBonusRecord,
            context_builder=build_preparation_context_from_buff,
        )

    def special_judge_logic(self, **kwargs):
        """检测到更新信号时，返回True，并且置空监听器的active_signal。"""
        self.check_record_module()
        self.get_prepared(equipper="激素朋克")
        if not self.record.listener_exist:
            self.record.listener = self.buff_instance.sim_instance.listener_manager.get_listener(
                listener_owner=self.record.char, listener_id="Hormone_Punk_1"
            )
            self.record.listener_exist = True
            # print(f"为{self.record.char.NAME}创建了一个激素朋克的监听器！")

        active_signal = self.record.listener.active_signal
        if active_signal is None:
            return False
        if active_signal[0].NAME != self.record.char.NAME:
            return False
        else:
            self.record.listener.active_signal = None
            if self.buff_0.is_ready(find_tick(sim_instance=self.buff_instance.sim_instance)):
                # print(
                #     f"{self.buff_instance.ft.index}接收到了匹配的更新信号（佩戴者为{active_signal[0].NAME}），buff更新时间{self.buff_0.dy.startticks}， buff结束时间为{self.buff_0.dy.endticks}"
                # )
                return True
            else:
                return False
