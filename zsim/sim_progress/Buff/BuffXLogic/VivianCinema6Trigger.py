import math
from typing import Any

from zsim.define import VIVIAN_REPORT
from zsim.sim_progress.calculation.calculator import (
    create_calculator_runtime_read_context_from_sim_instance,
    get_calculator_buff_attribute_reader_service,
)
from zsim.sim_progress.data_struct.schedule_dispatch import (
    ScheduledEventEmitter,
    ScheduledEventEmitterProvider,
)

from .. import Buff, check_preparation
from ..JudgeTools import build_preparation_context_from_buff
from ._preparation_helpers import ensure_owner_template_record, prepare_with_context
from .enemy_anomaly_read import (
    read_enemy_active_anomaly_list,
    read_enemy_anomaly_active,
)


class VivianCinema6TriggerRecord:
    def __init__(self):
        self.char = None
        self.preload_data = None
        self.last_update_node = None
        self.enemy = None
        self.dynamic_buff_list = None
        self.sub_exist_buff_dict = None
        self.cinema_ratio = None
        self.guard_feather = None

    @property
    def c6_ratio(self):
        return self.guard_feather * 0.8


class VivianCinema6Trigger(Buff.BuffLogic):
    def __init__(
        self,
        buff_instance,
        scheduled_event_emitter_provider: ScheduledEventEmitterProvider | None = None,
    ):
        """薇薇安的核心被动触发器"""
        super().__init__(buff_instance)
        self.buff_instance: Buff = buff_instance
        self._scheduled_event_emitter_provider = (
            scheduled_event_emitter_provider
            or ScheduledEventEmitterProvider.from_sim_instance_getter(
                lambda: self.buff_instance.sim_instance
            )
        )
        self.buff_0: Any = None
        self.record: Any = None
        self.xjudge = self.special_judge_logic
        self.xeffect = self.special_effect_logic
        self.ANOMALY_RATIO_MUL = {
            0: 0.0075,
            1: 0.08,
            2: 0.0108,
            3: 0.032,
            4: 0.0615,
            5: 0.0108,
        }

    def get_prepared(self, **kwargs):
        return prepare_with_context(
            self,
            check_preparation_func=check_preparation,
            context_builder=build_preparation_context_from_buff,
            **kwargs,
        )

    def _scheduled_event_emitter(self) -> ScheduledEventEmitter:
        return self._scheduled_event_emitter_provider.create_emitter()

    def check_record_module(self):
        ensure_owner_template_record(
            self,
            owner_name="薇薇安",
            record_factory=VivianCinema6TriggerRecord,
            context_builder=build_preparation_context_from_buff,
        )

    def special_judge_logic(self, **kwargs):
        """
        薇薇安的核心被动触发器：
        触发机制为：全队任意角色触发属性异常的第一跳时，构造一个新的属性异常放到Evenlist中
        """
        self.check_record_module()
        self.get_prepared(char_CID=1331, enemy=1)
        skill_node = kwargs.get("skill_node", None)
        from zsim.sim_progress.Preload import SkillNode

        if not isinstance(skill_node, SkillNode):
            raise TypeError(
                f"{self.buff_instance.ft.index}的xjudge函数获取到的skill_node不是SkillNode类型！"
            )
        if skill_node.skill_tag != "1331_SNA_2":
            return False
        if not read_enemy_anomaly_active(self.record.enemy):
            if VIVIAN_REPORT:
                self.buff_instance.sim_instance.schedule_data.change_process_state()
                print(" APL警告：怪物没异常你打什么SNA_2！豆子全没了吧傻子！")
        if self.record.last_update_node is None:
            self.c6_pre_active(skill_node)
            return True
        else:
            if skill_node.UUID != self.record.last_update_node.UUID:
                self.c6_pre_active(skill_node)
                return True
        return False

    def c6_pre_active(self, skill_node):
        self.record.last_update_node = skill_node
        guard_feather_cost = min(self.record.char.feather_manager.guard_feather, 5)
        if VIVIAN_REPORT:
            self.buff_instance.sim_instance.schedule_data.change_process_state()
            print(
                f"6画触发器：检测到【悬落】，即将消耗全部护羽！消耗前的资源情况为：{self.record.char.get_special_stats()}"
            )
        self.record.guard_feather = guard_feather_cost
        self.record.char.feather_manager.guard_feather = 0
        self.record.char.feather_manager.c1_counter += guard_feather_cost
        while self.record.char.feather_manager.c1_counter >= 4:
            self.record.char.feather_manager.c1_counter -= 4
            self.record.char.feather_manager.flight_feather = min(
                self.record.char.feather_manager.flight_feather + 1, 5
            )
            if VIVIAN_REPORT:
                self.buff_instance.sim_instance.schedule_data.change_process_state()
                print(
                    f"6画触发器：因6画触发、联动1画，恢复一点飞羽！当前资源情况为：{self.record.char.get_special_stats()}"
                )

    def special_effect_logic(self, **kwargs):
        """当Xjudge检测到AnomalyBar传入时通过判定，并且执行xeffect"""
        self.check_record_module()
        self.get_prepared(
            char_CID=1361,
            preload_data=1,
            enemy=1,
            sub_exist_buff_dict=1,
        )
        from zsim.sim_progress.anomaly_bar import AnomalyBar

        get_result = read_enemy_active_anomaly_list(self.record.enemy)
        if not get_result:
            self.record.char.feather_manager.update_myself(c6_signal=True)
            if VIVIAN_REPORT:
                self.buff_instance.sim_instance.schedule_data.change_process_state()
                print(
                    "6画触发器：在怪物没有异常的情况下打了【悬落】，虽然不能触发额外的异放，但是依然可以进行羽毛转化！"
                )
        else:
            active_anomaly_bar = get_result[0]
            copyed_anomaly = AnomalyBar.create_new_from_existing(active_anomaly_bar)
            if not copyed_anomaly.settled:
                copyed_anomaly.anomaly_settled()
            # copyed_anomaly = self.record.last_update_anomaly
            context = create_calculator_runtime_read_context_from_sim_instance(
                sim_instance=self.buff_instance.sim_instance,
                enemy=self.record.enemy,
                character=self.record.char,
            )
            reader_service = get_calculator_buff_attribute_reader_service()
            ap = reader_service.read_anomaly_proficiency(context)
            from zsim.sim_progress.anomaly_bar.CopyAnomalyForOutput import (
                DirgeOfDestinyAnomaly,
            )

            dirge_of_destiny_anomaly = DirgeOfDestinyAnomaly(
                copyed_anomaly,
                active_by="1331",
                sim_instance=self.buff_instance.sim_instance,
            )
            ratio = self.ANOMALY_RATIO_MUL.get(copyed_anomaly.element_type)
            if self.record.cinema_ratio is None:
                self.record.cinema_ratio = 1 if self.record.char.cinema < 2 else 1.3
            final_ratio = (
                math.floor(ap / 10) * ratio * self.record.cinema_ratio * self.record.c6_ratio
            )
            dirge_of_destiny_anomaly.anomaly_dmg_ratio = final_ratio

            # 在柚叶版本更新后，异常计算的逻辑改变了。current_ndarray不再动态变更，而是在属性异常触发后集中计算。
            # 所以，这里获取到的current_ndarray是已经计算好的，所以这里不需要除以当前异常值
            # dirge_of_destiny_anomaly.current_ndarray = (
            #     dirge_of_destiny_anomaly.current_ndarray
            #     / dirge_of_destiny_anomaly.current_anomaly
            # )
            self._scheduled_event_emitter().emit_scheduled(dirge_of_destiny_anomaly)
            if VIVIAN_REPORT:
                self.buff_instance.sim_instance.schedule_data.change_process_state()
                print(
                    f"6画触发器：触发额外异放！本次触发消耗额外护羽数量为：{self.record.guard_feather}，当前资源情况为：{self.record.char.get_special_stats()}"
                )
        self.record.guard_feather = 0
        self.record.char.feather_manager.update_myself(c6_signal=True)
