from __future__ import annotations

from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, TypeAlias, TypedDict, cast

import numpy as np
import pandas as pd

from zsim.define import (
    BUFF_LOADING_CONDITION_TRANSLATION_DICT,
    EXIST_FILE_PATH,
    JUDGE_FILE_PATH,
)
from zsim.sim_progress.Character.skill_class import Skill

from .buff_class import Buff

if TYPE_CHECKING:
    from zsim.sim_progress.Load import LoadingMission
    from zsim.sim_progress.ScheduledEvent.buff_runtime import (
        BuffTemplateRegistry,
        PendingBuffQueue,
    )
    from zsim.simulator.simulator_class import Simulator

    PendingQueueLike: TypeAlias = "PendingBuffQueue"
else:
    PendingQueueLike = object


class BuffLoadLoopCandidatePlanSummary(TypedDict):
    pending_queue_order: tuple[str, ...]
    mission_order: tuple[Any, ...]
    mission_count: int
    character_count: int
    candidate_count: int
    on_field_candidate_count: int
    backend_candidate_count: int


class BuffLoadLoopCandidatePlanDetail(BuffLoadLoopCandidatePlanSummary):
    steps: tuple[dict[str, object], ...]


class BuffLoadLoopRegistryLengthSnapshot(TypedDict):
    character_registry_lengths: tuple[tuple[str, int], ...]
    registered_candidate_count: int


@dataclass(frozen=True)
class _StaticJudgeCondition:
    skill_attribute: str
    allowed_values: frozenset[int | float | str]


@dataclass(frozen=True)
class _BuffLoadCandidateEntry:
    key: str
    buff: object
    judge_mode: str
    judge_conditions: tuple[_StaticJudgeCondition, ...] = ()
    prefilter_mode: str | None = None
    beneficiaries: tuple[str, ...] | None = None


@dataclass(frozen=True)
class _ProcessorCandidateEntries:
    entries: tuple[_BuffLoadCandidateEntry, ...]
    statically_skipped_count: int
    full_scan_candidate_count: int
    signature_skill_attributes: tuple[str, ...]
    has_prefilter: bool


@dataclass(frozen=True)
class _BuffJudgeStaticInfo:
    simple_logic: bool
    all_simple: bool
    alltime: bool
    blank_simple_judge: bool


@dataclass(frozen=True)
class BuffLoadCandidateSelection:
    processor: str
    owner: str
    registry: dict
    mission: "LoadingMission"
    candidate_keys: tuple[str, ...]
    beneficiaries_by_key: Mapping[str, Sequence[str]]
    full_scan_candidate_count: int
    selected_candidate_count: int
    skipped_candidate_count: int
    fallback_candidate_count: int


EXIST_FILE = pd.read_csv(EXIST_FILE_PATH, index_col="BuffName")
JUDGE_FILE = pd.read_csv(JUDGE_FILE_PATH, index_col="BuffName")
JUDGE_FILE = JUDGE_FILE.replace({np.nan: None})
EXIST_FILE = EXIST_FILE.replace({np.nan: None})


class BuffInitCache:
    def __init__(self):
        self.cache = {}

    def get(self, key):
        return self.cache.get(key)

    def add(self, key, value):
        self.cache[key] = value
        max_cache = 128
        while len(self.cache) > max_cache:
            self.cache.popitem()

    def __getitem__(self, key):
        return self.cache[key]


class BuffJudgeCache(BuffInitCache):
    def __init__(self):
        super().__init__()

    def static_info(
        self,
        buff_now: Buff,
        judge_condition_dict: dict,
    ) -> _BuffJudgeStaticInfo:
        cache_key = ("static_info", id(buff_now), id(judge_condition_dict))
        cached_info = self.cache.get(cache_key)
        if cached_info is not None:
            return cached_info
        simple_logic = bool(buff_now.ft.simple_judge_logic)
        all_simple = (
            simple_logic
            and bool(buff_now.ft.simple_start_logic)
            and bool(buff_now.ft.simple_hit_logic)
            and bool(buff_now.ft.simple_end_logic)
            and bool(buff_now.ft.simple_effect_logic)
            and bool(buff_now.ft.simple_exit_logic)
        )
        blank_simple_judge = simple_logic and not any(
            value is not None for value in judge_condition_dict.values()
        )
        static_info = _BuffJudgeStaticInfo(
            simple_logic=simple_logic,
            all_simple=all_simple,
            alltime=bool(buff_now.ft.alltime),
            blank_simple_judge=blank_simple_judge,
        )
        self.cache[cache_key] = static_info
        return static_info


class SimpleJudgeConditionCache(BuffInitCache):
    def __init__(self):
        super().__init__()


class BuffLoadLifecycleCache:
    def __init__(self) -> None:
        self.init_cache = BuffInitCache()
        self.judge_cache = BuffJudgeCache()
        self.simple_judge_condition_cache = SimpleJudgeConditionCache()


def _buff_judge_mission_cache_key(mission: "LoadingMission") -> tuple:
    mission_node = mission.mission_node
    skill = mission_node.skill
    tick_list = tuple(getattr(skill, "tick_list", ()) or ())
    return (
        mission.mission_tag,
        mission.preload_tick,
        mission.mission_start_tick,
        mission.mission_end_tick,
        tick_list,
    )


class BuffLoadCandidateIndex:
    """单次模拟内用于 BuffLoadLoop 候选池的保守索引。"""

    def __init__(
        self,
        buff_registry_by_character: dict,
        character_name_box: Sequence[str],
        all_name_order_box: Mapping[str, Sequence[str]] | None = None,
    ) -> None:
        self._registry_by_character = buff_registry_by_character
        self._character_name_box = tuple(character_name_box)
        self._all_name_order_snapshot = self._all_name_order_fingerprint(
            all_name_order_box,
            self._character_name_box,
        )
        self._registry_root_id = id(buff_registry_by_character)
        self._registry_identity_snapshot = self._registry_identity(
            buff_registry_by_character,
            self._character_name_box,
        )
        self._registry_fingerprint = self.registry_fingerprint(
            buff_registry_by_character,
            self._character_name_box,
        )
        self._registries_by_owner: dict[str, dict] = {
            owner: buff_registry_by_character[owner] for owner in self._character_name_box
        }
        self._entries_by_owner: dict[str, tuple[_BuffLoadCandidateEntry, ...]] = {
            owner: tuple(
                _BuffLoadCandidateEntry(
                    key=buff_key,
                    buff=buff,
                    judge_mode=judge_mode,
                    judge_conditions=judge_conditions,
                    prefilter_mode=self._classify_prefilter(buff),
                    beneficiaries=self._precompute_beneficiaries(
                        buff,
                        all_name_order_box,
                    ),
                )
                for buff_key, buff in registry.items()
                for judge_mode, judge_conditions in [self._classify_static_judge(buff)]
            )
            for owner, registry in self._registries_by_owner.items()
        }
        self._processor_entries_by_owner: dict[
            tuple[str, str],
            _ProcessorCandidateEntries,
        ] = {
            (owner, processor): self._build_processor_entries(
                entries,
                processor,
            )
            for owner, entries in self._entries_by_owner.items()
            for processor in ("on_field", "backend")
        }
        self._selection_cache: dict[
            tuple[str, str, tuple[tuple[str, object], ...]],
            tuple[tuple[str, ...], int, int],
        ] = {}

    @staticmethod
    def registry_fingerprint(
        buff_registry_by_character: dict,
        character_name_box: Sequence[str],
    ) -> tuple[tuple[str, int, tuple[tuple[str, int], ...]], ...]:
        return tuple(
            (
                owner,
                id(buff_registry_by_character[owner]),
                tuple(
                    (buff_key, id(buff))
                    for buff_key, buff in buff_registry_by_character[owner].items()
                ),
            )
            for owner in character_name_box
        )

    @staticmethod
    def _registry_identity(
        buff_registry_by_character: dict,
        character_name_box: Sequence[str],
    ) -> tuple[tuple[str, int, int], ...]:
        return tuple(
            (
                owner,
                id(buff_registry_by_character.get(owner)),
                len(buff_registry_by_character.get(owner, {})),
            )
            for owner in character_name_box
        )

    @staticmethod
    def _all_name_order_fingerprint(
        all_name_order_box: Mapping[str, Sequence[str]] | None,
        character_name_box: Sequence[str],
    ) -> tuple[tuple[str, tuple[str, ...]], ...] | None:
        if all_name_order_box is None:
            return None
        try:
            return tuple((owner, tuple(all_name_order_box[owner])) for owner in character_name_box)
        except (KeyError, TypeError):
            return None

    def matches_registry(
        self,
        buff_registry_by_character: dict,
        character_name_box: Sequence[str],
        all_name_order_box: Mapping[str, Sequence[str]] | None = None,
    ) -> bool:
        character_name_tuple = tuple(character_name_box)
        if character_name_tuple != self._character_name_box:
            return False
        if self._all_name_order_snapshot != self._all_name_order_fingerprint(
            all_name_order_box,
            character_name_tuple,
        ):
            return False
        if id(
            buff_registry_by_character
        ) == self._registry_root_id and self._registry_identity_snapshot == self._registry_identity(
            buff_registry_by_character,
            character_name_tuple,
        ):
            return True
        return self._registry_fingerprint == self.registry_fingerprint(
            buff_registry_by_character,
            character_name_tuple,
        )

    def iter_candidate_steps(
        self,
        load_mission_dict: dict,
    ) -> Iterator[BuffLoadCandidateSelection]:
        for mission in load_mission_dict.values():
            actor_name = mission.mission_character
            if actor_name not in self._registry_by_character:
                raise ValueError("当前角色的Buff源并未创建！")

            for owner in self._character_name_box:
                processor = "on_field" if owner == actor_name else "backend"
                yield self.select_candidates(
                    processor=processor,
                    owner=owner,
                    mission=mission,
                )

    def select_candidates(
        self,
        *,
        processor: str,
        owner: str,
        mission: "LoadingMission",
    ) -> BuffLoadCandidateSelection:
        registry = self._registries_by_owner[owner]
        processor_entries = self._processor_entries_by_owner[(owner, processor)]
        entries = processor_entries.entries
        static_signature = self._mission_static_signature(processor_entries, mission)
        cache_key = (owner, processor, static_signature)
        cached_selection = self._selection_cache.get(cache_key)
        if cached_selection is not None:
            (
                cached_candidate_keys,
                skipped_candidate_count,
                fallback_candidate_count,
            ) = cached_selection
            return BuffLoadCandidateSelection(
                processor=processor,
                owner=owner,
                registry=registry,
                mission=mission,
                candidate_keys=cached_candidate_keys,
                beneficiaries_by_key=self._beneficiaries_for_candidate_keys(
                    entries,
                    cached_candidate_keys,
                ),
                full_scan_candidate_count=processor_entries.full_scan_candidate_count,
                selected_candidate_count=len(cached_candidate_keys),
                skipped_candidate_count=skipped_candidate_count,
                fallback_candidate_count=fallback_candidate_count,
            )

        selected_candidate_keys: list[str] = []
        skipped_candidate_count = processor_entries.statically_skipped_count
        fallback_candidate_count = 0

        for entry in entries:
            selected, fallback = self._entry_matches_mission(entry, mission)
            if not selected:
                skipped_candidate_count += 1
                continue

            selected_candidate_keys.append(entry.key)
            if fallback:
                fallback_candidate_count += 1

        candidate_keys_tuple = tuple(selected_candidate_keys)
        selection = BuffLoadCandidateSelection(
            processor=processor,
            owner=owner,
            registry=registry,
            mission=mission,
            candidate_keys=candidate_keys_tuple,
            beneficiaries_by_key=self._beneficiaries_for_candidate_keys(
                entries,
                candidate_keys_tuple,
            ),
            full_scan_candidate_count=processor_entries.full_scan_candidate_count,
            selected_candidate_count=len(candidate_keys_tuple),
            skipped_candidate_count=skipped_candidate_count,
            fallback_candidate_count=fallback_candidate_count,
        )
        self._selection_cache[cache_key] = (
            candidate_keys_tuple,
            skipped_candidate_count,
            fallback_candidate_count,
        )
        return selection

    @staticmethod
    def _beneficiaries_for_candidate_keys(
        entries: tuple[_BuffLoadCandidateEntry, ...],
        candidate_keys: Sequence[str],
    ) -> dict[str, tuple[str, ...]]:
        selected_key_set = frozenset(candidate_keys)
        return {
            entry.key: entry.beneficiaries
            for entry in entries
            if entry.key in selected_key_set and entry.beneficiaries is not None
        }

    @staticmethod
    def _mission_static_signature(
        processor_entries: _ProcessorCandidateEntries,
        mission: "LoadingMission",
    ) -> tuple[tuple[str, object], ...]:
        skill_now = mission.mission_node.skill
        signature = [
            (skill_attribute, getattr(skill_now, skill_attribute, "<missing>"))
            for skill_attribute in processor_entries.signature_skill_attributes
        ]
        if processor_entries.has_prefilter:
            skill_node = mission.mission_node
            signature.extend(
                [
                    ("skill_tag", getattr(skill_node, "skill_tag", "<missing>")),
                    ("mission_tag", getattr(mission, "mission_tag", "<missing>")),
                    ("element_type", getattr(skill_node, "element_type", "<missing>")),
                    (
                        "trigger_buff_level",
                        getattr(
                            getattr(skill_node, "skill", None),
                            "trigger_buff_level",
                            "<missing>",
                        ),
                    ),
                    ("labels", _skill_label_keys(getattr(skill_node, "skill", None))),
                ]
            )
        return tuple(signature)

    @classmethod
    def _build_processor_entries(
        cls,
        entries: tuple[_BuffLoadCandidateEntry, ...],
        processor: str,
    ) -> _ProcessorCandidateEntries:
        selected_entries = tuple(
            entry for entry in entries if not cls._processor_statically_skips(entry.buff, processor)
        )
        signature_skill_attributes = tuple(
            sorted(
                {
                    condition.skill_attribute
                    for entry in selected_entries
                    for condition in entry.judge_conditions
                }
            )
        )
        return _ProcessorCandidateEntries(
            entries=selected_entries,
            statically_skipped_count=len(entries) - len(selected_entries),
            full_scan_candidate_count=len(entries),
            signature_skill_attributes=signature_skill_attributes,
            has_prefilter=any(entry.prefilter_mode is not None for entry in selected_entries),
        )

    def _classify_static_judge(
        self,
        buff: object,
    ) -> tuple[str, tuple[_StaticJudgeCondition, ...]]:
        if not isinstance(buff, Buff):
            return "fallback", ()

        feature = buff.ft
        if bool(getattr(feature, "alltime", False)):
            return "always_true", ()
        if not bool(getattr(feature, "simple_judge_logic", False)):
            return "fallback", ()

        buff_index = getattr(feature, "index", None)
        if not isinstance(buff_index, str) or buff_index not in JUDGE_FILE.index:
            return "fallback", ()
        try:
            judge_condition_dict = dict(JUDGE_FILE.loc[buff_index])
        except Exception:
            return "fallback", ()

        all_judge_conditions_blank = all(
            self._is_blank_judge_condition(value) for value in judge_condition_dict.values()
        )
        conditions: list[_StaticJudgeCondition] = []
        for condition, skill_attribute in BUFF_LOADING_CONDITION_TRANSLATION_DICT.items():
            if condition not in judge_condition_dict:
                return "fallback", ()
            csv_judge_condition = judge_condition_dict[condition]
            if self._is_blank_judge_condition(csv_judge_condition):
                continue
            try:
                allowed_values = frozenset(process_string(csv_judge_condition))
            except Exception:
                return "fallback", ()
            conditions.append(
                _StaticJudgeCondition(
                    skill_attribute=skill_attribute,
                    allowed_values=allowed_values,
                )
            )

        if not conditions:
            if all_judge_conditions_blank:
                return "always_false", ()
            return "always_true", ()
        return "simple", tuple(conditions)

    @staticmethod
    def _is_blank_judge_condition(value: object) -> bool:
        if value is None:
            return True
        try:
            return bool(pd.isna(value))
        except (TypeError, ValueError):
            return False

    @staticmethod
    def _processor_statically_skips(buff: object, processor: str) -> bool:
        if not isinstance(buff, Buff):
            return False

        feature = buff.ft
        if bool(feature.schedule_judge):
            return True
        if bool(feature.passively_updating):
            return True
        if processor == "backend" and not bool(feature.backend_acitve):
            return True
        return False

    @staticmethod
    def _entry_matches_mission(
        entry: _BuffLoadCandidateEntry,
        mission: "LoadingMission",
    ) -> tuple[bool, bool]:
        if entry.prefilter_mode is not None and not _prefilter_matches_mission(
            entry.prefilter_mode,
            mission,
        ):
            return False, False
        if entry.judge_mode == "fallback":
            return True, True
        if entry.judge_mode == "always_true":
            return True, False
        if entry.judge_mode == "always_false":
            return False, False
        if entry.judge_mode != "simple":
            return True, True

        skill_now = mission.mission_node.skill
        for condition in entry.judge_conditions:
            try:
                skill_value = getattr(skill_now, condition.skill_attribute)
            except AttributeError:
                return True, True
            if skill_value not in condition.allowed_values:
                return False, False
        return True, False

    @staticmethod
    def _classify_prefilter(buff: object) -> str | None:
        if not isinstance(buff, Buff):
            return None
        buff_index = getattr(buff.ft, "index", None)
        if not isinstance(buff_index, str):
            return None
        if "扳机-核心被动-失衡易伤" in buff_index:
            return "trigger_core_aftershock"
        if "扳机-1画-失衡易伤提升" in buff_index:
            return "trigger_aftershock_label"
        if "扳机-协同攻击-触发器" in buff_index:
            return "trigger_aftershock_source"
        if "耀佳音-震音管理器-触发器" in buff_index:
            return "astra_chord_manager"
        if "索魂影眸-减防" in buff_index:
            return "electric_aftershock"
        if "索魂影眸-魂锁" in buff_index:
            return "electric_aftershock"
        if "如影相随-四件套" in buff_index:
            return "shadow_harmony"
        if "仪玄-1画-落雷触发器" in buff_index:
            return "yixuan_c1_teammate"
        if "仪玄-4画-静心" in buff_index:
            return "yixuan_c4_tranquility"
        if "仪玄-额外能力-对失衡敌人增伤" in buff_index:
            return "yixuan_ex_b"
        if "仪玄-2画-失衡时间提升" in buff_index:
            return "yixuan_q"
        return None

    @staticmethod
    def _precompute_beneficiaries(
        buff: object,
        all_name_order_box: Mapping[str, Sequence[str]] | None,
    ) -> tuple[str, ...] | None:
        if all_name_order_box is None or not isinstance(buff, Buff):
            return None
        operator = getattr(buff.ft, "operator", None)
        if not isinstance(operator, str):
            return None
        try:
            all_name_box = all_name_order_box[operator]
        except (AttributeError, KeyError, TypeError):
            return None
        return tuple(_select_buff_beneficiaries(buff.ft.add_buff_to, all_name_box))


def _skill_label_keys(skill: object) -> tuple[str, ...]:
    labels = getattr(skill, "labels", None)
    if not labels:
        return ()
    try:
        return tuple(sorted(labels.keys()))
    except AttributeError:
        return tuple(sorted(labels))


def _skill_has_label(skill: object, label: str) -> bool:
    labels = getattr(skill, "labels", None)
    if not labels:
        return False
    return label in cast(Any, labels)


def _prefilter_matches_mission(
    prefilter_mode: str,
    mission: "LoadingMission",
) -> bool:
    skill_node = mission.mission_node
    skill = skill_node.skill
    skill_tag = getattr(skill_node, "skill_tag", "")
    mission_tag = getattr(mission, "mission_tag", "")
    element_type = getattr(skill_node, "element_type", None)
    trigger_buff_level = getattr(skill, "trigger_buff_level", None)

    if prefilter_mode == "trigger_core_aftershock":
        return "1361" in skill_tag and _skill_has_label(skill, "aftershock_attack")
    if prefilter_mode == "trigger_aftershock_label":
        return "1361" in skill_tag and _skill_has_label(skill, "aftershock_attack")
    if prefilter_mode == "trigger_aftershock_source":
        return "1361" not in mission_tag
    if prefilter_mode == "astra_chord_manager":
        return trigger_buff_level in (5, 7, 8)
    if prefilter_mode == "electric_aftershock":
        return element_type == 3 and _skill_has_label(skill, "aftershock_attack")
    if prefilter_mode == "shadow_harmony":
        if _skill_has_label(skill, "aftershock_attack"):
            return True
        return not getattr(skill, "labels", None) and trigger_buff_level == 3
    if prefilter_mode == "yixuan_c1_teammate":
        return getattr(skill_node, "char_name", None) != "仪玄"
    if prefilter_mode == "yixuan_c4_tranquility":
        return getattr(skill_node, "char_name", None) == "仪玄" and (
            trigger_buff_level == 6 or skill_tag == "1371_E_EX_B_3"
        )
    if prefilter_mode == "yixuan_ex_b":
        return "1371_E_EX_B_" in skill_tag
    if prefilter_mode == "yixuan_q":
        return skill_tag == "1371_Q"
    return True


def _get_buff_load_candidate_index(
    sim_instance: "Simulator",
    buff_registry_by_character: dict,
    character_name_box: Sequence[str],
    all_name_order_box: Mapping[str, Sequence[str]] | None = None,
) -> BuffLoadCandidateIndex:
    existing_index = getattr(sim_instance, "_buff_load_candidate_index", None)
    if isinstance(existing_index, BuffLoadCandidateIndex) and existing_index.matches_registry(
        buff_registry_by_character,
        character_name_box,
        all_name_order_box,
    ):
        return existing_index

    candidate_index = BuffLoadCandidateIndex(
        buff_registry_by_character,
        character_name_box,
        all_name_order_box,
    )
    try:
        setattr(sim_instance, "_buff_load_candidate_index", candidate_index)
    except Exception:
        pass
    return candidate_index


def _json_safe_mapping(value: Mapping[str, object]) -> dict[str, object]:
    return {str(key): _json_safe_value(item) for key, item in value.items()}


def _json_safe_value(value: object) -> object:
    if isinstance(value, Mapping):
        return _json_safe_mapping(value)
    if isinstance(value, tuple | list):
        return [_json_safe_value(item) for item in value]
    return value


def process_buff(
    buff_0,
    sub_exist_buff_dict,
    mission,
    time_now,
    selected_characters,
    pending_buff_queue,
    registry_by_character: dict,
    sim_instance: "Simulator",
    *,
    load_lifecycle_cache: BuffLoadLifecycleCache | None = None,
):
    """
    该函数是公用的buff逻辑处理函数，主要是通过BuffJudge来判断Buff是否应该触发。
    注意，此处的buff_0是operator的buff_0，哪怕buff是要加给别的角色，这里也是operator的buff_0
    """
    if load_lifecycle_cache is None:
        load_lifecycle_cache = BuffLoadLifecycleCache()
    due_sub_missions = None
    if buff_0.ft.simple_effect_logic:
        due_sub_missions = [
            sub_mission
            for sub_mission_start_tick, sub_mission in mission.mission_dict.items()
            if time_now - 1 < sub_mission_start_tick <= time_now
        ]
        if not due_sub_missions:
            # 简单效果只会在 start/hit/end 子任务命中 tick 改变状态；空 tick 不需要进入 BuffJudge。
            return
    all_match, judge_condition_dict, active_condition_dict = BuffInitialize(
        buff_0.ft.index,
        sub_exist_buff_dict,
        cache=load_lifecycle_cache.init_cache,
    )
    all_match = BuffJudge(
        buff_0,
        judge_condition_dict,
        mission,
        cache=load_lifecycle_cache.judge_cache,
        simple_condition_cache=load_lifecycle_cache.simple_judge_condition_cache,
    )
    if not all_match:
        return
    # if not buff_0.ft.is_debuff:
    """
    在20241114的更新中，我删除了debuff分支。因为buff的add_buff_to被拓展成了4字段，所以就没有必要判断是否是debuff了
    如果一个buff是debuff，那么它的add_buff_to字段的最后一位肯定是1，比如0001，
    这样，它就一定会在buff_go_to函数中导致'enemy'字段进入selected_characters列表，这样一来，enemy会被当成正常角色来执行正常的buff添加和update。
    """
    for char in selected_characters:
        # if buff_0.ft.simple_judge_logic:
        if buff_0.ft.simple_effect_logic:
            assert due_sub_missions is not None
            for sub_mission in due_sub_missions:
                """
                筛选出正在发生的子任务，如果子任务正在发生就直接执行update，把子任务的str传进buff.update()函数
                并且触发对应的分支（start、hit、end），完成符合buff属性的时间、层数更新。
                """
                buff_new = Buff(
                    active_condition_dict,
                    judge_condition_dict,
                    sim_instance=sim_instance,
                )
                buff_new.update(
                    char,
                    time_now,
                    mission.mission_node.skill.ticks,
                    sub_exist_buff_dict,
                    sub_mission,
                )
                buff_new.ft.operator = buff_0.ft.operator
                buff_new.ft.passively_updating = buff_0.ft.passively_updating
                buff_new.ft.beneficiary = buff_0.ft.beneficiary
                if buff_new.dy.is_changed:
                    _enqueue_pending_buff(pending_buff_queue, char, buff_new)
                    """
                    这里要注意：process_buff函数中传入的buff_0，只会来自于角色，
                    所以，如果有上个Enemy的debuff，那么角色自身作为触发源头，正常更新以外，
                    需要向Enemy的buff_0同步广播。否则，record就无法记录enemy身上Buff的正常层数。
                    """
                if char == "enemy":
                    enemy_buff_0 = registry_by_character["enemy"][buff_0.ft.index]
                    buff_new.update_to_buff_0(enemy_buff_0)
        else:
            """
            这个分支主要是为了处理复杂的effect类的buff的
            此类buff的更新往往不依赖start、hit、end三大子标签进行，
            所以单独进行处理
            """
            buff_new = Buff(active_condition_dict, judge_condition_dict, sim_instance=sim_instance)
            assert buff_new.logic.xeffect is not None, f"{buff_new.ft.index} 的 xeffect 不能为空"
            buff_new.logic.xeffect()
            if buff_new.dy.is_changed:
                buff_new.ft.operator = buff_0.ft.operator
                buff_new.ft.passively_updating = buff_0.ft.passively_updating
                buff_new.ft.beneficiary = buff_0.ft.beneficiary
                _enqueue_pending_buff(pending_buff_queue, char, buff_new)
                if char == "enemy":
                    enemy_buff_0 = registry_by_character["enemy"][buff_0.ft.index]
                    buff_new.update_to_buff_0(enemy_buff_0)


def _reset_pending_queues(
    pending_queue_owner: PendingQueueLike,
    beneficiaries: list[str],
) -> None:
    pending_queue_owner.reset_for_beneficiaries(beneficiaries)


def _enqueue_pending_buff(
    pending_queue_owner: PendingQueueLike,
    beneficiary: str,
    buff: Buff,
) -> None:
    pending_queue_owner.enqueue(beneficiary, buff)


def _count_pending_buffs(pending_queue_owner: PendingQueueLike) -> int:
    return int(pending_queue_owner.count())


def _pending_queue_result(pending_queue_owner: PendingQueueLike) -> dict[str, list[Buff]]:
    return pending_queue_owner.mutable_queues()


def _record_buff_load_loop_scan_metrics(
    sim_instance: "Simulator",
    *,
    mission_count: int,
    character_count: int,
    registered_buff_count: int,
    trigger_candidate_count: int,
    on_field_candidate_count: int,
    backend_candidate_count: int,
    full_scan_candidate_count: int,
    full_scan_on_field_candidate_count: int,
    full_scan_backend_candidate_count: int,
    skipped_candidate_count: int,
    skipped_on_field_candidate_count: int,
    skipped_backend_candidate_count: int,
    fallback_candidate_count: int,
    fallback_on_field_candidate_count: int,
    fallback_backend_candidate_count: int,
    pending_queue_count: int,
    candidate_plan: BuffLoadLoopCandidatePlanSummary | None = None,
) -> None:
    metrics = cast(
        dict[str, int] | None,
        getattr(sim_instance, "_buff_load_loop_scan_metrics", None),
    )
    zero_values: dict[str, int] = {
        "processed_tick_count": 0,
        "mission_count": 0,
        "character_count": 0,
        "registered_buff_count": 0,
        "trigger_candidate_count": 0,
        "on_field_candidate_count": 0,
        "backend_candidate_count": 0,
        "full_scan_candidate_count": 0,
        "full_scan_on_field_candidate_count": 0,
        "full_scan_backend_candidate_count": 0,
        "selected_candidate_count": 0,
        "selected_on_field_candidate_count": 0,
        "selected_backend_candidate_count": 0,
        "skipped_candidate_count": 0,
        "skipped_on_field_candidate_count": 0,
        "skipped_backend_candidate_count": 0,
        "fallback_candidate_count": 0,
        "fallback_on_field_candidate_count": 0,
        "fallback_backend_candidate_count": 0,
        "pending_queue_count": 0,
        "candidate_plan_count": 0,
        "candidate_plan_on_field_candidate_count": 0,
        "candidate_plan_backend_candidate_count": 0,
        "candidate_plan_mission_count": 0,
        "candidate_plan_character_count": 0,
        "candidate_plan_mismatch_count": 0,
    }
    if metrics is None:
        metrics = dict(zero_values)
        setattr(sim_instance, "_buff_load_loop_scan_metrics", metrics)
    else:
        for metric_name, default_value in zero_values.items():
            metrics.setdefault(metric_name, default_value)

    candidate_plan_count = 0
    candidate_plan_on_field_candidate_count = 0
    candidate_plan_backend_candidate_count = 0
    candidate_plan_mission_count = 0
    candidate_plan_character_count = 0
    candidate_plan_mismatch_count = 0
    if candidate_plan is not None:
        candidate_plan_count = candidate_plan["candidate_count"]
        candidate_plan_on_field_candidate_count = candidate_plan["on_field_candidate_count"]
        candidate_plan_backend_candidate_count = candidate_plan["backend_candidate_count"]
        candidate_plan_mission_count = candidate_plan["mission_count"]
        candidate_plan_character_count = candidate_plan["character_count"]
        candidate_plan_mismatch_count = sum(
            [
                candidate_plan_count != full_scan_candidate_count,
                candidate_plan_on_field_candidate_count != full_scan_on_field_candidate_count,
                candidate_plan_backend_candidate_count != full_scan_backend_candidate_count,
                candidate_plan_mission_count != mission_count,
                candidate_plan_character_count != character_count,
                full_scan_candidate_count != trigger_candidate_count + skipped_candidate_count,
                full_scan_on_field_candidate_count
                != on_field_candidate_count + skipped_on_field_candidate_count,
                full_scan_backend_candidate_count
                != backend_candidate_count + skipped_backend_candidate_count,
            ]
        )

    metrics["processed_tick_count"] += 1
    metrics["mission_count"] += mission_count
    metrics["character_count"] += character_count
    metrics["registered_buff_count"] += registered_buff_count
    metrics["trigger_candidate_count"] += trigger_candidate_count
    metrics["on_field_candidate_count"] += on_field_candidate_count
    metrics["backend_candidate_count"] += backend_candidate_count
    metrics["full_scan_candidate_count"] += full_scan_candidate_count
    metrics["full_scan_on_field_candidate_count"] += full_scan_on_field_candidate_count
    metrics["full_scan_backend_candidate_count"] += full_scan_backend_candidate_count
    metrics["selected_candidate_count"] += trigger_candidate_count
    metrics["selected_on_field_candidate_count"] += on_field_candidate_count
    metrics["selected_backend_candidate_count"] += backend_candidate_count
    metrics["skipped_candidate_count"] += skipped_candidate_count
    metrics["skipped_on_field_candidate_count"] += skipped_on_field_candidate_count
    metrics["skipped_backend_candidate_count"] += skipped_backend_candidate_count
    metrics["fallback_candidate_count"] += fallback_candidate_count
    metrics["fallback_on_field_candidate_count"] += fallback_on_field_candidate_count
    metrics["fallback_backend_candidate_count"] += fallback_backend_candidate_count
    metrics["pending_queue_count"] += pending_queue_count
    metrics["candidate_plan_count"] += candidate_plan_count
    metrics["candidate_plan_on_field_candidate_count"] += candidate_plan_on_field_candidate_count
    metrics["candidate_plan_backend_candidate_count"] += candidate_plan_backend_candidate_count
    metrics["candidate_plan_mission_count"] += candidate_plan_mission_count
    metrics["candidate_plan_character_count"] += candidate_plan_character_count
    metrics["candidate_plan_mismatch_count"] += candidate_plan_mismatch_count


def _summarize_buff_load_loop_candidate_plan(
    load_mission_dict: dict,
    buff_registry_by_character: dict,
    character_name_box: list,
) -> BuffLoadLoopCandidatePlanSummary:
    registry_snapshot = _snapshot_buff_load_loop_registry_lengths(
        load_mission_dict,
        buff_registry_by_character,
        character_name_box,
    )
    registry_lengths_by_character = dict(registry_snapshot["character_registry_lengths"])
    registered_candidate_count = registry_snapshot["registered_candidate_count"]
    mission_count_by_actor: dict[str, int] = {}
    for mission in load_mission_dict.values():
        actor_name = mission.mission_character
        mission_count_by_actor[actor_name] = mission_count_by_actor.get(actor_name, 0) + 1

    on_field_candidate_count = 0
    backend_candidate_count = 0
    for actor_name, mission_count in mission_count_by_actor.items():
        actor_candidate_count = registry_lengths_by_character.get(actor_name, 0)
        on_field_candidate_count += actor_candidate_count * mission_count
        backend_candidate_count += (
            registered_candidate_count - actor_candidate_count
        ) * mission_count

    return {
        "pending_queue_order": tuple([*character_name_box, "enemy"]),
        "mission_order": tuple(load_mission_dict),
        "mission_count": len(load_mission_dict),
        "character_count": len(character_name_box),
        "candidate_count": on_field_candidate_count + backend_candidate_count,
        "on_field_candidate_count": on_field_candidate_count,
        "backend_candidate_count": backend_candidate_count,
    }


def _snapshot_buff_load_loop_registry_lengths(
    load_mission_dict: dict,
    buff_registry_by_character: dict,
    character_name_box: list,
) -> BuffLoadLoopRegistryLengthSnapshot:
    registry_lengths_by_character: dict[str, int] = {}

    for mission in load_mission_dict.values():
        actor_name = mission.mission_character
        if actor_name not in buff_registry_by_character:
            raise ValueError("当前角色的Buff源并未创建！")

        for char_name in character_name_box:
            if char_name not in registry_lengths_by_character:
                registry_lengths_by_character[char_name] = len(
                    buff_registry_by_character[char_name]
                )

    character_registry_lengths = tuple(
        (char_name, registry_lengths_by_character[char_name])
        for char_name in character_name_box
        if char_name in registry_lengths_by_character
    )
    return {
        "character_registry_lengths": character_registry_lengths,
        "registered_candidate_count": sum(
            candidate_count for _, candidate_count in character_registry_lengths
        ),
    }


def _describe_buff_load_loop_candidate_plan(
    load_mission_dict: dict,
    buff_registry_by_character: dict,
    character_name_box: list,
) -> BuffLoadLoopCandidatePlanDetail:
    steps = []
    on_field_candidate_count = 0
    backend_candidate_count = 0

    for mission_key, mission in load_mission_dict.items():
        actor_name = mission.mission_character
        if actor_name not in buff_registry_by_character:
            raise ValueError("当前角色的Buff源并未创建！")

        for char_name in character_name_box:
            registry = buff_registry_by_character[char_name]
            candidate_count = len(registry)
            processor = "on_field" if char_name == actor_name else "backend"
            if processor == "on_field":
                on_field_candidate_count += candidate_count
            else:
                backend_candidate_count += candidate_count
            steps.append(
                {
                    "mission_key": mission_key,
                    "mission_character": actor_name,
                    "character_name": char_name,
                    "processor": processor,
                    "buff_keys": tuple(registry),
                    "candidate_count": candidate_count,
                }
            )

    return {
        "pending_queue_order": tuple([*character_name_box, "enemy"]),
        "mission_order": tuple(load_mission_dict),
        "mission_count": len(load_mission_dict),
        "character_count": len(character_name_box),
        "candidate_count": on_field_candidate_count + backend_candidate_count,
        "on_field_candidate_count": on_field_candidate_count,
        "backend_candidate_count": backend_candidate_count,
        "steps": tuple(steps),
    }


def _iter_buff_load_loop_candidate_steps(
    load_mission_dict: dict,
    buff_registry_by_character: dict,
    character_name_box: list,
) -> Iterator[tuple[str, dict, "LoadingMission"]]:
    for mission in load_mission_dict.values():
        actor_name = mission.mission_character
        if actor_name not in buff_registry_by_character:
            raise ValueError("当前角色的Buff源并未创建！")

        for char_name in character_name_box:
            registry = buff_registry_by_character[char_name]
            processor = "on_field" if char_name == actor_name else "backend"
            yield processor, registry, mission


def _process_on_field_buff_candidates(
    candidate_keys: Sequence[str],
    sub_exist_buff_dict: dict,
    mission: "LoadingMission",
    time_now: int,
    pending_buff_queue: PendingQueueLike,
    all_name_order_box: dict,
    registry_by_character: dict,
    sim_instance: "Simulator",
    *,
    load_lifecycle_cache: BuffLoadLifecycleCache | None = None,
    beneficiaries_by_key: Mapping[str, Sequence[str]] | None = None,
) -> None:
    for buff_key in candidate_keys:
        buff_0 = sub_exist_buff_dict[buff_key]
        if not isinstance(buff_0, Buff):
            raise TypeError(f"当前{buff_key}不是Buff类！")
        if buff_0.ft.schedule_judge:
            continue
        if buff_0.ft.passively_updating:
            continue

        main_char = buff_0.ft.operator
        all_name_box = all_name_order_box[main_char]
        selected_characters = (
            beneficiaries_by_key.get(buff_key) if beneficiaries_by_key is not None else None
        )
        if selected_characters is None:
            selected_characters = buff_go_to(buff_0, all_name_box)
        process_buff(
            buff_0,
            sub_exist_buff_dict,
            mission,
            time_now,
            selected_characters,
            pending_buff_queue,
            registry_by_character,
            sim_instance=sim_instance,
            load_lifecycle_cache=load_lifecycle_cache,
        )


def _process_backend_buff_candidates(
    candidate_keys: Sequence[str],
    sub_exist_buff_dict: dict,
    all_name_order_box: dict,
    mission: "LoadingMission",
    time_now: int,
    pending_buff_queue: PendingQueueLike,
    registry_by_character: dict,
    sim_instance: "Simulator",
    *,
    load_lifecycle_cache: BuffLoadLifecycleCache | None = None,
    beneficiaries_by_key: Mapping[str, Sequence[str]] | None = None,
) -> None:
    for other_buff_key in candidate_keys:
        other_buff_0 = sub_exist_buff_dict[other_buff_key]
        if not isinstance(other_buff_0, Buff):
            raise TypeError(f"当前{other_buff_key}不是Buff类！")
        if other_buff_0.ft.schedule_judge:
            continue
        if not other_buff_0.ft.backend_acitve:
            continue
        if other_buff_0.ft.passively_updating:
            continue
        main_char = other_buff_0.ft.operator
        name_order_box = all_name_order_box[main_char]
        selected_characters_back = (
            beneficiaries_by_key.get(other_buff_key) if beneficiaries_by_key is not None else None
        )
        if selected_characters_back is None:
            selected_characters_back = buff_go_to(other_buff_0, name_order_box)
        process_buff(
            other_buff_0,
            sub_exist_buff_dict,
            mission,
            time_now,
            selected_characters_back,
            pending_buff_queue,
            registry_by_character,
            sim_instance=sim_instance,
            load_lifecycle_cache=load_lifecycle_cache,
        )


def _execute_buff_load_loop_candidate_step(
    *,
    processor: str,
    registry: dict,
    mission: "LoadingMission",
    time_now: int,
    pending_buff_queue: PendingQueueLike,
    all_name_order_box: dict,
    registry_by_character: dict,
    sim_instance: "Simulator",
    load_lifecycle_cache: BuffLoadLifecycleCache,
    candidate_keys: Sequence[str] | None = None,
    beneficiaries_by_key: Mapping[str, Sequence[str]] | None = None,
) -> None:
    if processor == "on_field":
        if candidate_keys is None:
            process_on_field_buff(
                registry,
                mission,
                time_now,
                pending_buff_queue,
                all_name_order_box,
                registry_by_character,
                sim_instance=sim_instance,
                load_lifecycle_cache=load_lifecycle_cache,
            )
        else:
            _process_on_field_buff_candidates(
                candidate_keys,
                registry,
                mission,
                time_now,
                pending_buff_queue,
                all_name_order_box,
                registry_by_character,
                sim_instance=sim_instance,
                load_lifecycle_cache=load_lifecycle_cache,
                beneficiaries_by_key=beneficiaries_by_key,
            )
        return
    if processor == "backend":
        if candidate_keys is None:
            process_backend_buff(
                registry,
                all_name_order_box,
                mission,
                time_now,
                pending_buff_queue,
                registry_by_character,
                sim_instance=sim_instance,
                load_lifecycle_cache=load_lifecycle_cache,
            )
        else:
            _process_backend_buff_candidates(
                candidate_keys,
                registry,
                all_name_order_box,
                mission,
                time_now,
                pending_buff_queue,
                registry_by_character,
                sim_instance=sim_instance,
                load_lifecycle_cache=load_lifecycle_cache,
                beneficiaries_by_key=beneficiaries_by_key,
            )
        return
    raise ValueError(f"未知的BuffLoadLoop候选执行器：{processor}")


def BuffLoadLoop(
    time_now: int,
    load_mission_dict: dict,
    template_registry: "BuffTemplateRegistry",
    character_name_box: list,
    pending_buff_queue: PendingQueueLike,
    all_name_order_box: dict,
    sim_instance: "Simulator",
    *,
    load_lifecycle_cache: BuffLoadLifecycleCache | None = None,
):
    """
    这是buff修改三部曲的第二步,也是最核心的一个步骤，
    该函数会通过 runtime-owned pending queue 记录本tick触发了多少BUFF/DEBUFF，
    并移交给 pending activation 执行buff的添加。
    本函数的核心调用函数是ProcessBuff函数。
    """
    from zsim.sim_progress.Load import LoadingMission

    buff_registry_by_character = template_registry.mutable_registry()
    pending_queue_owner = pending_buff_queue
    if not hasattr(pending_queue_owner, "reset_for_beneficiaries"):
        raise TypeError(
            "BuffLoadLoop requires BuffRuntimeState.pending_queue_owner(); "
            "raw pending dictionaries are no longer accepted."
        )
    if load_lifecycle_cache is None:
        load_lifecycle_cache = BuffLoadLifecycleCache()
    record_rebuild_count = getattr(sim_instance, "_record_buff_runtime_rebuild_count", None)
    if record_rebuild_count is not None:
        record_rebuild_count("buff_load_loop")
    record_scan_metrics = getattr(sim_instance, "_buff_runtime_rebuild_counts", None) is not None
    use_indexed_execution = bool(getattr(sim_instance, "use_indexed_buff_load_loop", False))
    registered_buff_count = 0
    trigger_candidate_count = 0
    on_field_candidate_count = 0
    backend_candidate_count = 0
    full_scan_candidate_count = 0
    full_scan_on_field_candidate_count = 0
    full_scan_backend_candidate_count = 0
    skipped_candidate_count = 0
    skipped_on_field_candidate_count = 0
    skipped_backend_candidate_count = 0
    fallback_candidate_count = 0
    fallback_on_field_candidate_count = 0
    fallback_backend_candidate_count = 0
    if record_scan_metrics:
        registered_buff_count = sum(
            len(buff_registry_by_character.get(character, {})) for character in character_name_box
        )

    all_name_box = character_name_box + ["enemy"]
    _reset_pending_queues(pending_queue_owner, all_name_box)

    candidate_plan = None
    if use_indexed_execution:
        for mission in load_mission_dict.values():
            if not isinstance(mission, LoadingMission):
                raise TypeError(f"当前{mission}不是LoadingMission类！")
        if record_scan_metrics:
            candidate_plan = _summarize_buff_load_loop_candidate_plan(
                load_mission_dict,
                buff_registry_by_character,
                character_name_box,
            )
        candidate_index = _get_buff_load_candidate_index(
            sim_instance,
            buff_registry_by_character,
            character_name_box,
            all_name_order_box,
        )
        for selection in candidate_index.iter_candidate_steps(load_mission_dict):
            processor = selection.processor
            full_scan_candidate_count += selection.full_scan_candidate_count
            skipped_candidate_count += selection.skipped_candidate_count
            fallback_candidate_count += selection.fallback_candidate_count
            trigger_candidate_count += selection.selected_candidate_count
            if processor == "on_field":
                full_scan_on_field_candidate_count += selection.full_scan_candidate_count
                skipped_on_field_candidate_count += selection.skipped_candidate_count
                fallback_on_field_candidate_count += selection.fallback_candidate_count
                on_field_candidate_count += selection.selected_candidate_count
            else:
                full_scan_backend_candidate_count += selection.full_scan_candidate_count
                skipped_backend_candidate_count += selection.skipped_candidate_count
                fallback_backend_candidate_count += selection.fallback_candidate_count
                backend_candidate_count += selection.selected_candidate_count
            if processor == "on_field":
                _process_on_field_buff_candidates(
                    selection.candidate_keys,
                    selection.registry,
                    selection.mission,
                    time_now,
                    pending_queue_owner,
                    all_name_order_box,
                    buff_registry_by_character,
                    sim_instance=sim_instance,
                    load_lifecycle_cache=load_lifecycle_cache,
                    beneficiaries_by_key=selection.beneficiaries_by_key,
                )
            else:
                _process_backend_buff_candidates(
                    selection.candidate_keys,
                    selection.registry,
                    all_name_order_box,
                    selection.mission,
                    time_now,
                    pending_queue_owner,
                    buff_registry_by_character,
                    sim_instance=sim_instance,
                    load_lifecycle_cache=load_lifecycle_cache,
                    beneficiaries_by_key=selection.beneficiaries_by_key,
                )
    else:
        # 遍历load_mission_dict中的任务
        for mission in load_mission_dict.values():
            if not isinstance(mission, LoadingMission):
                raise TypeError(f"当前{mission}不是LoadingMission类！")
            actor_name = mission.mission_character
            if actor_name not in buff_registry_by_character:
                raise ValueError("当前角色的Buff源并未创建！")
            # 提取当前角色的 Buff 列表
            # 敌人模板由 runtime 持有的注册表统一处理。

            for char_name in character_name_box:
                registry = buff_registry_by_character[char_name]
                candidate_count = len(registry)
                if record_scan_metrics:
                    trigger_candidate_count += candidate_count
                    full_scan_candidate_count += candidate_count
                    if char_name == actor_name:
                        on_field_candidate_count += candidate_count
                        full_scan_on_field_candidate_count += candidate_count
                    else:
                        backend_candidate_count += candidate_count
                        full_scan_backend_candidate_count += candidate_count
                if char_name == actor_name:
                    process_on_field_buff(
                        registry,
                        mission,
                        time_now,
                        pending_queue_owner,
                        all_name_order_box,
                        buff_registry_by_character,
                        sim_instance=sim_instance,
                        load_lifecycle_cache=load_lifecycle_cache,
                    )
                else:
                    process_backend_buff(
                        registry,
                        all_name_order_box,
                        mission,
                        time_now,
                        pending_queue_owner,
                        buff_registry_by_character,
                        sim_instance=sim_instance,
                        load_lifecycle_cache=load_lifecycle_cache,
                    )
    if record_scan_metrics:
        if candidate_plan is None:
            candidate_plan = _summarize_buff_load_loop_candidate_plan(
                load_mission_dict,
                buff_registry_by_character,
                character_name_box,
            )
        _record_buff_load_loop_scan_metrics(
            sim_instance,
            mission_count=len(load_mission_dict),
            character_count=len(character_name_box),
            registered_buff_count=registered_buff_count,
            trigger_candidate_count=trigger_candidate_count,
            on_field_candidate_count=on_field_candidate_count,
            backend_candidate_count=backend_candidate_count,
            full_scan_candidate_count=full_scan_candidate_count,
            full_scan_on_field_candidate_count=full_scan_on_field_candidate_count,
            full_scan_backend_candidate_count=full_scan_backend_candidate_count,
            skipped_candidate_count=skipped_candidate_count,
            skipped_on_field_candidate_count=skipped_on_field_candidate_count,
            skipped_backend_candidate_count=skipped_backend_candidate_count,
            fallback_candidate_count=fallback_candidate_count,
            fallback_on_field_candidate_count=fallback_on_field_candidate_count,
            fallback_backend_candidate_count=fallback_backend_candidate_count,
            pending_queue_count=_count_pending_buffs(pending_queue_owner),
            candidate_plan=candidate_plan,
        )
    return _pending_queue_result(pending_queue_owner)


def process_on_field_buff(
    sub_exist_buff_dict: dict,
    mission: "LoadingMission",
    time_now: int,
    pending_buff_queue: PendingQueueLike,
    all_name_order_box: dict,
    registry_by_character: dict,
    sim_instance: "Simulator",
    *,
    load_lifecycle_cache: BuffLoadLifecycleCache | None = None,
):
    """
    处理前台Buff的逻辑模块
        注意，这部分的分支，指的是以当前的前台角色为第一视角来给自己或是其他人添加Buff。
        由于这个循环的前置参数——character_name是从mission里面拿来的，所以“前台角色”不可能是enemy
        这意味enemy的所有buff必须是别人添加给它的，目前enemy没有主动更新buff的逻辑。
    """
    for buff_key, buff_0 in sub_exist_buff_dict.items():
        if not isinstance(buff_0, Buff):
            raise TypeError(f"当前{buff_key}不是Buff类！")
        if buff_0.ft.schedule_judge:
            #   跳过schedule阶段处理的buff
            continue
        if buff_0.ft.passively_updating:
            # 目前正是前台角色触发前台buff，而passively_updating为True时，
            # 意味着“当前buff的触发我说了不算，别人说了算”，那么本函数自然无法处理，要直接跳过。
            continue

        # 提前计算添加Buff的角色列表
        main_char = buff_0.ft.operator
        all_name_box = all_name_order_box[main_char]
        selected_characters = buff_go_to(buff_0, all_name_box)
        process_buff(
            buff_0,
            sub_exist_buff_dict,
            mission,
            time_now,
            selected_characters,
            pending_buff_queue,
            registry_by_character,
            sim_instance=sim_instance,
            load_lifecycle_cache=load_lifecycle_cache,
        )


def process_backend_buff(
    sub_exist_buff_dict: dict,
    all_name_order_box: dict,
    mission: "LoadingMission",
    time_now: int,
    pending_buff_queue: PendingQueueLike,
    registry_by_character: dict,
    sim_instance: "Simulator",
    *,
    load_lifecycle_cache: BuffLoadLifecycleCache | None = None,
):
    """
    处理后台Buff的逻辑，
    尽管当前的动作是别的角色（actor ≠ char_name），但是，两位后台角色身上，依旧存在着可能发生更新的Buff
    这些Buff都拥有backend_active标签。但并非所有拥有这一标签的buff都应该执行更新。
    比如，后台角色A会给所有人叠层，当前台动作满足该Buff的触发条件时，
    应只执行该buff所有者（operator）的buff更新，而不执行受益者（beneficiary）的更新，
    这样就可以避免buff的重复更新。

    以 静听佳音4件套 为例：套装佩戴者位于后台时，如果前台角色使用了快速支援，
    那么，在process_on_field_buff函数中，前台角色的嘉音层数不会被更新；
    而在此函数中，该buff属于耀佳音的那个buff_0会触发更新，从而实现全队层数+1
    """
    for other_buff_key, other_buff_0 in sub_exist_buff_dict.items():
        if not isinstance(other_buff_0, Buff):
            raise TypeError(f"当前{other_buff_key}不是Buff类！")
        if other_buff_0.ft.schedule_judge:
            continue
        if not other_buff_0.ft.backend_acitve:
            continue
        if other_buff_0.ft.passively_updating:
            continue
        main_char = other_buff_0.ft.operator
        name_order_box = all_name_order_box[main_char]
        selected_characters_back = buff_go_to(other_buff_0, name_order_box)
        process_buff(
            other_buff_0,
            sub_exist_buff_dict,
            mission,
            time_now,
            selected_characters_back,
            pending_buff_queue,
            registry_by_character,
            sim_instance=sim_instance,
            load_lifecycle_cache=load_lifecycle_cache,
        )


def buff_go_to(buff_0, all_name_box):
    """
    运行函数前，总有：
    all_name_box  = character_name_box + ['enemy']
    该函数是用来处理buff该加给什么角色的
    比如这个buff的add_buff_to字段的内容是1100（加给自己和下一位），那么新的这个selected_characters就会输出[艾莲，莱卡恩]
    如果字段内容是1010（加给自己和上一位），那么新的selected_characters就会输出[艾莲，苍角]
    """
    cache_key = (id(all_name_box), getattr(buff_0.ft, "add_buff_to", None))
    cache = getattr(buff_0, "_zsim_buff_go_to_cache", None)
    if not isinstance(cache, dict):
        cache = {}
        try:
            setattr(buff_0, "_zsim_buff_go_to_cache", cache)
        except (AttributeError, TypeError):
            cache = None
    cached_selected_characters = cache.get(cache_key) if cache is not None else None
    if cached_selected_characters is not None:
        return cached_selected_characters
    selected_characters = _select_buff_beneficiaries(
        buff_0.ft.add_buff_to,
        all_name_box,
    )
    if cache is not None:
        cache[cache_key] = selected_characters
    return selected_characters


def _select_buff_beneficiaries(add_buff_to: object, all_name_box: Sequence[str]) -> list[str]:
    adding_code = str(int(cast(Any, add_buff_to))).zfill(4)
    return [all_name_box[i] for i in range(len(all_name_box)) if adding_code[i] == "1"]


def BuffInitialize(
    buff_name: str, template_registry: dict, *, cache: BuffInitCache | None = None
) -> tuple[bool, dict, dict]:
    if cache is None:
        cache = BuffInitCache()
    cache_key = (id(template_registry), buff_name)
    if cache_key in cache.cache:
        return cache.get(cache_key)
    # 对单个buff进行初始化，抛出一个触发状态参数，两个参数序列。
    all_match = False
    buff_now = template_registry[buff_name]
    if not isinstance(buff_now, Buff):
        raise ValueError(f"当前正在检索的Buff：{buff_name}并不是Buff类！")
    if buff_name not in JUDGE_FILE.index:
        raise ValueError(f"Buff{buff_name}不在JUDGE_FILE中！")
    judge_condition_dict = dict(JUDGE_FILE.loc[buff_name])
    active_condition_dict = dict(EXIST_FILE.loc[buff_name])
    active_condition_dict["BuffName"] = buff_name
    # 根据buff名称，直接把判断信息从JUDGE_FILE中提出来并且转化成dict。

    results = (all_match, judge_condition_dict, active_condition_dict)
    cache.add(cache_key, results)
    return results


def BuffJudge(
    buff_now: Buff,
    judge_condition_dict: dict,
    mission: "LoadingMission",
    *,
    cache: BuffJudgeCache | None = None,
    simple_condition_cache: SimpleJudgeConditionCache | None = None,
) -> bool:
    """
    如果judge_condition_dict的全部内容是None，同时buff还是简单判断逻辑
    说明是环境或是战斗系统自带的debuff，则直接返回False，跳过判断。
    """
    # 以下为缓存逻辑
    if cache is None:
        cache = BuffJudgeCache()
    static_info = cache.static_info(buff_now, judge_condition_dict)
    if static_info.all_simple:
        cache_key = (
            id(buff_now),
            id(judge_condition_dict),
            _buff_judge_mission_cache_key(mission),
        )
        if cache_key in cache.cache:
            return cache[cache_key]
    result: bool

    def save_cache_and_return(result: bool):
        """由于本函数有多个return中断，所以写了个这玩意，把直接return换成return这个函数就行"""
        if static_info.all_simple:
            cache.add(cache_key, result)
        return result

    # ——————缓存逻辑结束————————

    if static_info.alltime:
        result = True
        return save_cache_and_return(result)
    if static_info.blank_simple_judge:
        # 说明：全部数据都是None并且是简单判断逻辑
        #   这通常意味着Buff的判断不在Load阶段，而是通过某种方式在其他阶段暴力添加。
        #   但是部分alltime的buff也会进入这一分支，所以需要在判断alltime之后再进行全空判断。
        result = False
        return save_cache_and_return(result)
    """
    正常buff的判断逻辑
    """
    skill_now = mission.mission_node.skill
    if not isinstance(skill_now, Skill.InitSkill):
        raise TypeError(f"{skill_now}并非Skill类！")
    if static_info.simple_logic:
        all_match = simple_string_judge(
            judge_condition_dict,
            skill_now,
            cache=simple_condition_cache,
        )
    else:
        try:
            assert buff_now.logic.xjudge is not None, f"{buff_now.ft.index} 的 xjudge 不能为空"
            all_match = buff_now.logic.xjudge(
                loading_mission=mission, skill_node=mission.mission_node
            )
        except TypeError:
            raise TypeError(f"{buff_now.ft.index}的xjudge方法参数错误！")
    result = all_match
    return save_cache_and_return(result)


def _simple_judge_conditions(
    judge_condition_dict: dict,
    *,
    cache: SimpleJudgeConditionCache | None = None,
) -> tuple[_StaticJudgeCondition, ...]:
    if cache is None:
        cache = SimpleJudgeConditionCache()
    cache_key = id(judge_condition_dict)
    cached_conditions = cache.get(cache_key)
    if cached_conditions is not None:
        return cached_conditions

    conditions: list[_StaticJudgeCondition] = []
    for condition, judge_condition in BUFF_LOADING_CONDITION_TRANSLATION_DICT.items():
        csv_judge_condition = judge_condition_dict[condition]
        if csv_judge_condition is not None:
            conditions.append(
                _StaticJudgeCondition(
                    skill_attribute=judge_condition,
                    allowed_values=frozenset(process_string(csv_judge_condition)),
                )
            )
    result = tuple(conditions)
    cache.add(cache_key, result)
    return result


def simple_string_judge(
    judge_condition_dict: dict,
    skill_now,
    *,
    cache: SimpleJudgeConditionCache | None = None,
) -> bool:
    for condition in _simple_judge_conditions(
        judge_condition_dict,
        cache=cache,
    ):
        if getattr(skill_now, condition.skill_attribute) not in condition.allowed_values:
            return False
    return True


def process_string(source: str) -> list[int | float | str]:
    """
    在2024.11.13的更新中，从csv中读取的数据从单个数值变成了字符串，但是数据类型有点复杂。
    如果单元格内没有分隔符，那么就会被转化为单元素列表，且会自动转换其中的数字为python数字，
    如果有分隔符，则会根据分隔符打散成列表，并且将其中的数字转化成python数字。
    由于getattr方法获得的技能属性的数值永远是单个的，所以用 技能属性 in list 的判定逻辑，
    这样就可以实现“或”逻辑。
    """
    if isinstance(source, str):
        if "|" in source:
            split_list = source.split("|")
            return [int(item) if item.isdigit() else item for item in split_list]
        else:
            return [int(source) if source.isdigit() else source]
    else:
        return [source]


def process_buff_for_test(buff_0, sub_exist_buff_dict, mission):
    """
    本函数截取了process_buff函数的头部，专为Pytest服务，正常程序请勿调用！
    """
    all_match, judge_condition_dict, active_condition_dict = BuffInitialize(
        buff_0.ft.index, sub_exist_buff_dict
    )
    all_match = BuffJudge(buff_0, judge_condition_dict, mission)
    return all_match
