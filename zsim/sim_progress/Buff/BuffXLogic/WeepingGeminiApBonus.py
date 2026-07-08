from .. import Buff, check_preparation, find_tick
from ..JudgeTools import build_preparation_context_from_buff
from ._preparation_helpers import ensure_equipper_template_record, prepare_with_context
from .enemy_edge_state_read import read_enemy_stun_edge_state


class WeepingGeminiApBonusRecord:
    def __init__(self):
        self.equipper = None
        self.char = None
        self.last_update_anomaly = None
        self.enemy = None
        self.last_update_stun = False
        self.sub_exist_buff_dict = None


class WeepingGeminiApBonus(Buff.BuffLogic):
    """双生泣星的精通增幅判定。"""

    def __init__(self, buff_instance):
        super().__init__(buff_instance)
        self.buff_instance: Buff = buff_instance
        self.xjudge = self.special_judge_logic
        self.xeffect = self.special_effect_logic
        self.xexit = self.special_exit_logic
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
            item_name="双生泣星",
            record_factory=WeepingGeminiApBonusRecord,
            context_builder=build_preparation_context_from_buff,
        )

    def special_judge_logic(self, **kwargs):
        """检测到新属性异常触发，直接放行。"""
        self.check_record_module()
        self.get_prepared(equipper="双生泣星")
        anomaly_bar = kwargs.get("anomaly_bar", None)

        if anomaly_bar is None:
            return False
        from zsim.sim_progress.anomaly_bar import AnomalyBar

        if not isinstance(anomaly_bar, AnomalyBar):
            raise TypeError(
                f"{self.buff_instance.ft.index}的xjudge函数获取的{anomaly_bar}不是AnomalyBar类！"
            )
        if anomaly_bar.activated_by:
            if self.record.equipper != anomaly_bar.activated_by.char_name:
                return False

        if self.record.last_update_anomaly is None:
            self.record.last_update_anomaly = anomaly_bar
            return True

        # 如果是同一异常，则不放行。
        if id(anomaly_bar) == id(self.record.last_update_anomaly):
            return False

        self.record.last_update_anomaly = anomaly_bar
        return True

    def special_effect_logic(self, **kwargs):
        self.check_record_module()
        self.get_prepared(equipper="双生泣星", enemy=1, sub_exist_buff_dict=1)
        self.buff_instance.simple_start(
            find_tick(sim_instance=self.buff_instance.sim_instance),
            self.record.sub_exist_buff_dict,
        )
        # print(f'检测到新的异常状态！层数更新！当前层数：{self.buff_instance.dy.built_in_buff_box}')

    def special_exit_logic(self, **kwargs):
        self.check_record_module()
        self.get_prepared(equipper="双生泣星", enemy=1)
        enemy = self.record.enemy
        current_stun = read_enemy_stun_edge_state(enemy)
        if self.record.last_update_stun:
            if not current_stun:
                self.record.last_update_stun = current_stun
                # print(f'检测到敌人失衡状态的下降沿，Buff清空！')
                return True
        self.record.last_update_stun = current_stun
        return False
