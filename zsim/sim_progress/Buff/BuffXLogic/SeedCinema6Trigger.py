from dataclasses import dataclass
from typing import cast

from zsim.define import SEED_REPORT

from .. import Buff, check_preparation
from ..JudgeTools import build_preparation_context_from_buff
from ._buff_record_base_class import BuffRecordBaseClass as BRBC
from ._preparation_helpers import ensure_owner_template_record, prepare_with_context


@dataclass(frozen=True)
class SeedCinema6RunSnapshot:
    tick: int
    trigger_skill_tag: str
    additional_damage_skill_tag: str

    def preload_tick_list(self) -> list[int]:
        return [self.tick, self.tick, self.tick]

    def skill_tag_list(self) -> list[str]:
        return [
            self.additional_damage_skill_tag,
            self.additional_damage_skill_tag,
            self.additional_damage_skill_tag,
        ]


class SeedCinema6TriggerRecord(BRBC):
    def __init__(self):
        super().__init__()
        self.cd = 180
        self.additional_damage_skill_tag = "1461_Cinema_6"
        self.trigger_skill_tag = "1461_SNA_1"

    def build_run_snapshot(self, *, tick: int) -> SeedCinema6RunSnapshot:
        assert self.trigger_skill_tag is not None
        assert self.additional_damage_skill_tag is not None
        return SeedCinema6RunSnapshot(
            tick=tick,
            trigger_skill_tag=self.trigger_skill_tag,
            additional_damage_skill_tag=self.additional_damage_skill_tag,
        )


class SeedCinema6Trigger(Buff.BuffLogic):
    def __init__(self, buff_instance):
        """这是席德6画触发器Buff的脚本"""
        super().__init__(buff_instance)
        self.buff_instance: Buff = buff_instance
        self.xjudge = self.special_judge_logic
        self.xstart = self.special_start_logic
        self.buff_0: "Buff | None" = None
        self.record: BRBC | None = None

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
            owner_name="席德",
            record_factory=SeedCinema6TriggerRecord,
            context_builder=build_preparation_context_from_buff,
        )
        assert self.buff_0 is not None, (
            "【Buff初始化警告】席德的复杂逻辑模块未正确初始化，请检查函数"
        )
        self.record = cast(SeedCinema6TriggerRecord, self.buff_0.history.record)

    def special_judge_logic(self, **kwargs):
        self.check_record_module()
        self.get_prepared(char_CID=1461)
        assert self.record is not None, (
            f"【Buff初始化警告】{self.buff_instance.ft.index}的复杂逻辑模块未正确初始化，请检查函数"
        )
        skill_node = kwargs.get("skill_node", None)
        if skill_node is None:
            return False
        from zsim.sim_progress.Preload import SkillNode

        assert isinstance(skill_node, SkillNode)
        tick = self.buff_instance.sim_instance.tick
        run_snapshot = self.record.build_run_snapshot(tick=tick)
        if skill_node.skill_tag != run_snapshot.trigger_skill_tag:
            return False
        if run_snapshot.tick != skill_node.preload_tick:
            return False
        if not self.record.check_cd(tick_now=run_snapshot.tick):
            return False
        return True

    def special_start_logic(self, **kwargs):
        self.check_record_module()
        self.get_prepared(char_CID=1461)
        assert self.record is not None

        tick = self.buff_instance.sim_instance.tick
        run_snapshot = self.record.build_run_snapshot(tick=tick)
        preparation_context = build_preparation_context_from_buff(self.buff_instance)
        preparation_context.preload_commands.schedule_preload_events(
            preload_tick_list=run_snapshot.preload_tick_list(),
            skill_tag_list=run_snapshot.skill_tag_list(),
        )
        self.record.last_active_tick = run_snapshot.tick
        if SEED_REPORT:
            self.buff_instance.sim_instance.schedule_data.change_process_state()
            print("【席德6画】检测到席德发动了 落华·重戮，添加三次协同攻击！")
