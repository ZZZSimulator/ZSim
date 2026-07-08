# 这是席德额外能力重击大招增伤无视电抗Buff的脚本
from typing import Any

from define import SEED_REPORT

from zsim.sim_progress.data_struct.schedule_dispatch import (
    ScheduledEventEmitterProvider,
)

from .. import Buff, check_preparation
from ..JudgeTools import build_preparation_context_from_buff
from ..JudgeTools.PreparationContext import ResourceRefreshCommandPort
from ._buff_record_base_class import BuffRecordBaseClass as BRBC
from ._preparation_helpers import ensure_owner_template_record, prepare_with_context


class SeedAdditionalAbilityTriggerRecord(BRBC):
    def __init__(self):
        super().__init__()
        self.cd = 60
        self.energy_value = 2  # 回能值，2点能量。


class SeedAdditionalAbilityTrigger(Buff.BuffLogic):
    def __init__(
        self,
        buff_instance,
        scheduled_event_emitter_provider: ScheduledEventEmitterProvider | None = None,
    ):
        """这是席德额外能力给正兵回能的触发器"""
        super().__init__(buff_instance)
        self.buff_instance: Buff = buff_instance
        self._scheduled_event_emitter_provider = (
            scheduled_event_emitter_provider
            or ScheduledEventEmitterProvider.from_sim_instance_getter(
                lambda: self.buff_instance.sim_instance
            )
        )
        self.xjudge = self.special_judge_logic
        self.xhit = self.special_hit_logic
        self.buff_0: Any = None
        self.record: Any = None

    def get_prepared(self, **kwargs):
        return prepare_with_context(
            self,
            check_preparation_func=check_preparation,
            context_builder=build_preparation_context_from_buff,
            **kwargs,
        )

    def _emit_scheduled_refresh(
        self,
        *,
        sp_target: tuple[str, ...],
        sp_value: float | int,
    ) -> None:
        refresh_commands = ResourceRefreshCommandPort(self._scheduled_event_emitter_provider)
        refresh_commands.publish_refresh(sp_target=sp_target, sp_value=sp_value)

    def check_record_module(self):
        ensure_owner_template_record(
            self,
            owner_name="席德",
            record_factory=SeedAdditionalAbilityTriggerRecord,
            context_builder=build_preparation_context_from_buff,
        )
        assert self.buff_0 is not None, (
            "【Buff初始化警告】席德的复杂逻辑模块未正确初始化，请检查函数"
        )

    def special_judge_logic(self, **kwargs):
        self.check_record_module()
        self.get_prepared(char_CID=1461)
        assert self.record is not None, (
            f"【Buff初始化警告】{self.buff_instance.ft.index}的复杂逻辑模块未正确初始化，请检查函数"
        )
        skill_node = kwargs.get("skill_node")
        if skill_node is None:
            return False
        from zsim.sim_progress.Preload import SkillNode

        assert isinstance(skill_node, SkillNode)
        preload_data = self.buff_instance.sim_instance.preload.preload_data
        # 当前操作角色不是席德时，直接返回False
        if preload_data.operating_now != 1461:
            return False
        # 过滤掉不是席德的技能
        if skill_node.char_name != self.record.char.NAME:
            return False
        # 过滤掉所有非命中帧
        tick = self.buff_instance.sim_instance.tick
        if not skill_node.is_hit_now(tick=tick):
            return False
        # 检查内置CD
        if not self.record.check_cd(tick_now=tick):
            return False
        return True

    def special_hit_logic(self, **kwargs):
        self.check_record_module()
        self.get_prepared(char_CID=1461)
        assert isinstance(self.record, SeedAdditionalAbilityTriggerRecord), (
            f"【Buff初始化警告】{self.buff_instance.ft.index}的复杂逻辑模块未正确初始化，请检查函数"
        )
        assert self.record.char.vanguard is not None, (
            "席德在激活了组队被动的情况下没有指定正兵，请检查"
        )
        vanguard = self.record.char.vanguard

        energy_value = self.record.energy_value
        self._emit_scheduled_refresh(
            sp_target=(vanguard.NAME,),
            sp_value=energy_value,
        )
        self.record.last_active_tick = self.buff_instance.sim_instance.tick
        if SEED_REPORT:
            self.buff_instance.sim_instance.schedule_data.change_process_state()
            print(f"【席德事件】额外能力触发，为{vanguard}回恢 {energy_value} 点能量")
