from .. import Buff, check_preparation
from ..JudgeTools import build_preparation_context_from_buff
from ._preparation_helpers import ensure_equipper_template_record, prepare_with_context


class ZanshinHerbCaseRecord:
    def __init__(self):
        self.equipper = None
        self.char = None
        self.listener_exist = False
        self.listener = None


class ZanshinHerbCase(Buff.BuffLogic):
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
            item_name="残心青囊",
            record_factory=ZanshinHerbCaseRecord,
            context_builder=build_preparation_context_from_buff,
        )

    def special_judge_logic(self, **kwargs):
        """检测到更新信号时，返回True，并且置空监听器的active_signal。"""
        self.check_record_module()
        self.get_prepared(equipper="残心青囊")
        if not self.record.listener_exist:
            self.record.listener = self.buff_instance.sim_instance.listener_manager.get_listener(
                listener_owner=self.record.char, listener_id="Zanshin_Herb_Case_1"
            )
            self.record.listener_exist = True
            # print(f"为{self.record.char.NAME}创建了一个残心青囊的监听器！")

        active_signal = self.record.listener.active_signal
        if active_signal is None:
            return False
        else:
            """置空信号"""
            self.record.listener.listener_active()
            print("检测到残心青囊 的触发信号！触发第三特效！")
            return True
