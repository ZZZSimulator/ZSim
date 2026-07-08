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


class VivianCorePassiveTriggerRecord:
    def __init__(self):
        self.char = None
        self.preload_data = None
        self.last_update_node = None
        self.enemy = None
        self.dynamic_buff_list = None
        self.sub_exist_buff_dict = None
        self.cinema_ratio = None


class VivianCorePassiveTrigger(Buff.BuffLogic):
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
            record_factory=VivianCorePassiveTriggerRecord,
            context_builder=build_preparation_context_from_buff,
        )

    def special_judge_logic(self, **kwargs):
        """
        薇薇安的核心被动触发器：
        触发机制为：落羽生花命中处于异常状态的目标时，构造一个新的属性异常放到Evenlist中
        """
        self.check_record_module()
        self.get_prepared(char_CID=1331, enemy=1)
        skill_node = kwargs.get("skill_node", None)
        if skill_node is None:
            return False
        from zsim.sim_progress.Preload import SkillNode

        if not isinstance(skill_node, SkillNode):
            raise TypeError(
                f"{self.buff_instance.ft.index}的xjudge函数获取到的skill_node 不是SkillNode类型"
            )
        if skill_node.skill_tag != "1331_CoAttack_A":
            return False
        if not read_enemy_anomaly_active(self.record.enemy):
            return False
        if self.record.last_update_node is None:
            self.record.last_update_node = skill_node
            return True
        else:
            if skill_node.UUID != self.record.last_update_node.UUID:
                self.record.last_update_node = skill_node
                return True
            else:
                return False

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
            raise ValueError(
                f"{self.buff_instance.ft.index}的xeffect函数中，enemy.get_active_anomlay函数返回空列表，说明此时没有异常。但是xjudge函数却放行了。"
            )
        active_anomaly_bar = get_result[0]
        copyed_anomaly = AnomalyBar.create_new_from_existing(active_anomaly_bar)
        if not copyed_anomaly.settled:
            copyed_anomaly.anomaly_settled()
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
        """20250424参考波波獭视频，该倍率是每一点精通平滑收益，并非向下取整，故此调整模型，去掉floor。"""
        """final_ratio = math.floor(ap/10) * ratio * self.record.cinema_ratio"""
        final_ratio = ap / 10 * ratio * self.record.cinema_ratio
        dirge_of_destiny_anomaly.anomaly_dmg_ratio = final_ratio
        # dirge_of_destiny_anomaly.current_ndarray = (
        #     dirge_of_destiny_anomaly.current_ndarray
        #     / dirge_of_destiny_anomaly.current_anomaly
        # )
        self._scheduled_event_emitter().emit_scheduled(dirge_of_destiny_anomaly)
        if VIVIAN_REPORT:
            self.buff_instance.sim_instance.schedule_data.change_process_state()
            print("核心被动：检测到【落羽生花】命中异常状态下的敌人，触发一次异放！！！")
