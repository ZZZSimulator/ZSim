from __future__ import annotations

import copy
import inspect
from dataclasses import dataclass, field, fields
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable, Iterator, Sequence, cast

import numpy as np
import pytest

import zsim.sim_progress.calculation.anomaly_calculator as cal_anomaly_module
import zsim.sim_progress.calculation.calculator as calculator_module
import zsim.sim_progress.data_struct.data_analyzer as data_analyzer_module
from zsim.sim_progress.anomaly_bar import AnomalyBar
from zsim.sim_progress.anomaly_bar.CopyAnomalyForOutput import (
    DirgeOfDestinyAnomaly,
    Disorder,
    NewAnomaly,
    PolarityDisorder,
)
from zsim.sim_progress.Buff import Buff
from zsim.sim_progress.Buff.BuffXLogic.BranchBladeSongCritDamageBonus import (
    BranchBladeSongCritDamageBonus,
)
from zsim.sim_progress.Buff.BuffXLogic.LinaCoreSkillPenRatioBonus import (
    LinaCoreSkillPenRatioBonus,
)
from zsim.sim_progress.Buff.BuffXLogic.TimeweaverDisorderDmgMul import (
    TimeweaverDisorderDmgMul,
)
from zsim.sim_progress.calculation.calculator import (
    BuffAttributeReadContext,
    Calculator,
    CalculatorBuffAttributeReader,
    CalculatorBuffAttributeReaderService,
    CalculatorBuffBonusReadContext,
    CalculatorRuntimeReadContext,
    MultiplierData,
    RetainedFormulaSnapshot,
    create_anomaly_attribute_read_context,
    create_calculator_buff_bonus_context_from_sim_instance,
    create_calculator_runtime_read_context,
    create_calculator_runtime_read_context_from_event_context,
    create_calculator_runtime_read_context_from_sim_instance,
    get_calculator_buff_attribute_reader_service,
)
from zsim.sim_progress.Character.character import Character
from zsim.sim_progress.data_struct.sp_update_data import SPUpdateData
from zsim.sim_progress.Preload.SkillsQueue import SkillNode
from zsim.sim_progress.ScheduledEvent.buff_runtime import BuffRuntimeReadPort, BuffRuntimeState
from zsim.sim_progress.ScheduledEvent.event_handlers.context import EventContext

PROJECT_ROOT = Path(__file__).resolve().parents[2]

_AggregationCall = tuple[tuple[object, ...], object | None, object, str | None]
_FormulaDataOracle = Callable[[Any], Any]
_ReaderContextOracle = Callable[[CalculatorBuffAttributeReader, BuffAttributeReadContext], Any]


@dataclass(frozen=True)
class _AttributeReadFixture:
    context: BuffAttributeReadContext
    active_buff_view: dict[str, list[object]]
    enemy: SimpleNamespace
    char: SimpleNamespace
    expected_enabled_buff: tuple[object, ...]
    expected_enemy_dot_buff: tuple[object, ...] = ()


class _ForbiddenEnemyDynamic:
    @property
    def dynamic_debuff_list(self) -> tuple[object, ...]:
        raise AssertionError("runtime read path must use explicit enemy_debuffs")


class _EnemyFallbackForbiddenView(dict[str, tuple[object, ...]]):
    def __getitem__(self, key: str) -> tuple[object, ...]:
        if key == "enemy":
            raise AssertionError("runtime read path must not fall back to active view enemy key")
        return super().__getitem__(key)


class _CalculatorRuntimeView(BuffRuntimeReadPort):
    def __init__(self, active_buff_view: dict[str, tuple[object, ...]]) -> None:
        self.active_buff_view = _EnemyFallbackForbiddenView(active_buff_view)
        self.active_buff_beneficiaries: list[str] = []
        self.active_view_calls = 0

    def get_active_buffs(self, beneficiary: str) -> tuple[object, ...]:
        self.active_buff_beneficiaries.append(beneficiary)
        return self.active_buff_view.get(beneficiary, ())

    def get_active_buff_view(self) -> _EnemyFallbackForbiddenView:
        self.active_view_calls += 1
        return self.active_buff_view

    def get_exist_buff_snapshot(self, beneficiary: str) -> dict[str, object]:
        return {}

    def get_exist_buff_snapshot_view(self) -> dict[str, dict[str, object]]:
        return {}


@dataclass(frozen=True)
class _AnomalyFormulaFixture:
    sim_instance: SimpleNamespace
    character: SimpleNamespace
    activation: SimpleNamespace
    enemy: SimpleNamespace
    active_buff_view: dict[str, list[object]]
    source_snapshot: np.ndarray
    anomaly_bar: AnomalyBar


@dataclass(frozen=True)
class _MigratedReaderSeamSample:
    case_id: str
    phase: str
    migrated_file: str
    formula_key: str
    fixture_kwargs: dict[str, Any]
    dynamic_attrs: dict[str, float]
    expected_value: float


@dataclass(frozen=True)
class _OracleTolerance:
    rel: float = 1e-12
    abs: float = 1e-12

    def approx(self, expected: Any) -> Any:
        return pytest.approx(expected, rel=self.rel, abs=self.abs)


@dataclass(frozen=True)
class _FormulaOracleExpectation:
    label: str
    expected_value: float
    retained_value: _FormulaDataOracle
    reader_value: _ReaderContextOracle | None = None


@dataclass(frozen=True)
class _FormulaOracleCase:
    case_id: str
    fixture_kwargs: dict[str, Any]
    dynamic_attrs: dict[str, float]
    expected_dynamic_fields: dict[str, float]
    expectations: tuple[_FormulaOracleExpectation, ...]
    expected_aggregation_times: int | None = None
    tolerance: _OracleTolerance = field(default_factory=_OracleTolerance)


@dataclass(frozen=True)
class _AnomalyMasteryRetainedOracleCase:
    case_id: str
    fixture_kwargs: dict[str, Any]
    dynamic_attrs: dict[str, float]
    expected_dynamic_fields: dict[str, float]
    expected_value: float
    tolerance: _OracleTolerance = field(default_factory=_OracleTolerance)


@dataclass(frozen=True)
class _AnomalyProficiencyRetainedOracleCase:
    case_id: str
    fixture_kwargs: dict[str, Any]
    dynamic_attrs: dict[str, float]
    expected_dynamic_fields: dict[str, float]
    expected_value: float
    tolerance: _OracleTolerance = field(default_factory=_OracleTolerance)


@dataclass(frozen=True)
class _ImpactRetainedOracleCase:
    case_id: str
    fixture_kwargs: dict[str, Any]
    dynamic_attrs: dict[str, float]
    expected_dynamic_fields: dict[str, float]
    expected_value: float
    tolerance: _OracleTolerance = field(default_factory=_OracleTolerance)


@dataclass(frozen=True)
class _AnomalySnapshotOracleCase:
    case_id: str
    snapshot_values: tuple[float, ...]
    scaling_factor: float = 1.25
    character_name: str = "异常公式角色"


@dataclass(frozen=True)
class _AnomalyMulSnapshotOracleCase:
    case_id: str
    character_name: str
    character_kwargs: dict[str, Any]
    skill_kwargs: dict[str, Any]
    dynamic_attrs: dict[str, float]
    expected_snapshot: tuple[float, ...]


@dataclass(frozen=True)
class _CopiedOutputPayloadCase:
    case_id: str
    snapshot_case: _AnomalySnapshotOracleCase
    copied_kind: str
    runtime_tick: int
    payload_fields: dict[str, Any]
    polarity_ratio: float | None = None


_COPIED_OUTPUT_FORMULA_INPUT_FIELDS = (
    "current_ndarray",
    "element_type",
    "scaling_factor",
)
_COPIED_OUTPUT_EFFECTIVE_ANOMALY_FIELDS = (
    "current_effective_anomaly",
    "current_anomaly",
    "settled",
)
_COPIED_OUTPUT_DURATION_FIELDS = (
    "max_duration",
    "last_active",
    "remaining_tick",
)
_COPIED_OUTPUT_LISTENER_REPORT_PAYLOAD_ONLY_FIELDS = (
    "rename_tag",
    "accompany_dot",
    "anomaly_dmg_ratio",
)
_COPIED_OUTPUT_POLARITY_ONLY_FIELDS = (
    "polarity_disorder_ratio",
    "additional_dmg_ap_ratio",
)


@dataclass(frozen=True)
class _CalAnomalyMultiplierOracleCase:
    case_id: str
    element_type: int
    snapshot_values: tuple[float, ...]
    enemy_max_def: float
    enemy_damage_resistance_attrs: dict[str, float]
    enemy_stunned: bool
    enemy_stun_ratio: float
    dynamic_attrs: dict[str, float]
    expected_dynamic_fields: dict[str, float]
    expected_snapshot_fields: dict[str, float]
    expected_final_multipliers: tuple[float, ...]
    scaling_factor: float = 1.25


@dataclass(frozen=True)
class _CalAnomalyLevelClampOracleCase:
    case_id: str
    input_level: int
    expected_value: float
    expected_log_messages: tuple[str, ...] = ()


@dataclass(frozen=True)
class _CalDisorderOracleCase:
    case_id: str
    element_type: int
    snapshot_values: tuple[float, ...]
    dynamic_attrs: dict[str, float]
    expected_dynamic_fields: dict[str, float]
    runtime_tick: int
    max_duration: int
    last_active: int
    expected_remaining_tick: int
    enemy_stun_resistance: float
    payload_fields: dict[str, Any]
    expected_final_multipliers: tuple[float, ...]
    expected_disorder_stun: float
    scaling_factor: float = 1.0


@dataclass(frozen=True)
class _CalPolarityDisorderOracleCase:
    case_id: str
    base_case: _CalDisorderOracleCase
    dynamic_attrs: dict[str, float]
    expected_dynamic_fields: dict[str, float]
    polarity_disorder_ratio: float
    additional_dmg_ap_ratio: float
    yanagi_static_ap: float
    expected_yanagi_ap: float
    expected_base_disorder_dmg: float
    expected_final_multipliers: tuple[float, ...]


@dataclass(frozen=True)
class _CalAbloomOracleCase:
    case_id: str
    base_case: _CalAnomalyMultiplierOracleCase
    anomaly_dmg_ratio: float
    copied_payload_sentinel_fields: dict[str, Any]
    fixture_blocker_fields: tuple[str, ...]
    expected_deterministic_fields: dict[str, float]
    expected_final_multipliers: tuple[float, ...]


_CAL_ANOMALY_FINAL_MULTIPLIER_ORDER = (
    "base_dmg",
    "dmg_bonus",
    "am_mul",
    "k_level",
    "anomaly_bonus",
    "active_crit",
    "def_mul",
    "res_mul",
    "vulnerability_mul",
    "snapshot_impact",
    "snapshot_stun_bonus",
    "stun_vulnerability",
    "special_mul",
)


_ANOMALY_MUL_SNAPSHOT_FIELDS = (
    "base_damage",
    "dmg_bonus",
    "ap_mul",
    "level",
    "anomaly_bonus",
    "anomaly_crit",
    "pen_ratio",
    "pen_numeric",
    "res_pen",
)


_ANOMALY_CURRENT_NDARRAY_FIELDS = (
    "base_dmg",
    "dmg_bonus",
    "anomaly_mastery",
    "virtual_character_level",
    "anomaly_bonus",
    "snapshot_anomaly_crit",
    "snapshot_pen_ratio",
    "snapshot_pen_numeric",
    "snapshot_res_pen",
    "snapshot_impact",
    "snapshot_stun_bonus",
)

_CAL_RES_PEN_DYNAMIC_FIELD_NAMES = (
    "physical_res_pen_increase",
    "fire_res_pen_increase",
    "ice_res_pen_increase",
    "electric_res_pen_increase",
    "ether_res_pen_increase",
    "all_res_pen_increase",
)

_CAL_RES_PEN_READER_SNAPSHOT_COMPATIBILITY_CASES = (
    (
        "physical",
        0,
        "physical_res_pen_increase",
        {
            "physical_res_pen_increase": 0.11,
            "fire_res_pen_increase": 0.91,
            "ice_res_pen_increase": 0.92,
            "electric_res_pen_increase": 0.93,
            "ether_res_pen_increase": 0.94,
            "all_res_pen_increase": 0.95,
        },
    ),
    (
        "fire",
        1,
        "fire_res_pen_increase",
        {
            "physical_res_pen_increase": 0.91,
            "fire_res_pen_increase": 0.12,
            "ice_res_pen_increase": 0.92,
            "electric_res_pen_increase": 0.93,
            "ether_res_pen_increase": 0.94,
            "all_res_pen_increase": 0.95,
        },
    ),
    (
        "ice",
        2,
        "ice_res_pen_increase",
        {
            "physical_res_pen_increase": 0.91,
            "fire_res_pen_increase": 0.92,
            "ice_res_pen_increase": 0.13,
            "electric_res_pen_increase": 0.93,
            "ether_res_pen_increase": 0.94,
            "all_res_pen_increase": 0.95,
        },
    ),
    (
        "frost",
        5,
        "ice_res_pen_increase",
        {
            "physical_res_pen_increase": 0.91,
            "fire_res_pen_increase": 0.92,
            "ice_res_pen_increase": 0.14,
            "electric_res_pen_increase": 0.93,
            "ether_res_pen_increase": 0.94,
            "all_res_pen_increase": 0.95,
        },
    ),
    (
        "electric",
        3,
        "electric_res_pen_increase",
        {
            "physical_res_pen_increase": 0.91,
            "fire_res_pen_increase": 0.92,
            "ice_res_pen_increase": 0.93,
            "electric_res_pen_increase": 0.15,
            "ether_res_pen_increase": 0.94,
            "all_res_pen_increase": 0.95,
        },
    ),
    (
        "ether",
        4,
        "ether_res_pen_increase",
        {
            "physical_res_pen_increase": 0.91,
            "fire_res_pen_increase": 0.92,
            "ice_res_pen_increase": 0.93,
            "electric_res_pen_increase": 0.94,
            "ether_res_pen_increase": 0.16,
            "all_res_pen_increase": 0.95,
        },
    ),
    (
        "auric-ink",
        6,
        "ether_res_pen_increase",
        {
            "physical_res_pen_increase": 0.91,
            "fire_res_pen_increase": 0.92,
            "ice_res_pen_increase": 0.93,
            "electric_res_pen_increase": 0.94,
            "ether_res_pen_increase": 0.17,
            "all_res_pen_increase": 0.95,
        },
    ),
)


def _reset_formula_oracle_caches() -> None:
    MultiplierData.mul_data_cache.clear()
    MultiplierData.StaticStatement._instance_cache.clear()
    Calculator.AnomalyMul.cal_ap.cache_clear()


@pytest.fixture(autouse=True)
def _reset_formula_fixture_state() -> Iterator[None]:
    _reset_formula_oracle_caches()
    yield
    _reset_formula_oracle_caches()


def _make_character(
    *,
    name: str = "折枝剑歌",
    atk: float = 0.0,
    hp: float = 0.0,
    defense: float = 0.0,
    am: float = 0.0,
    ap: float = 0.0,
    imp: float = 0.0,
    crit_rate: float = 0.0,
    crit_damage: float = 0.0,
    static_statement_attrs: dict[str, float] | None = None,
) -> SimpleNamespace:
    statement_values = {
        "ATK": atk,
        "HP": hp,
        "DEF": defense,
        "AM": am,
        "AP": ap,
        "IMP": imp,
        "CRIT_rate": crit_rate,
        "CRIT_damage": crit_damage,
    }
    if static_statement_attrs is not None:
        statement_values.update(static_statement_attrs)
    statement = SimpleNamespace(statement=statement_values)
    for attr_name, value in statement_values.items():
        setattr(statement, attr_name, value)
    return SimpleNamespace(
        NAME=name,
        CID=1301,
        level=60,
        statement=statement,
        crit_balancing=False,
    )


def _make_enemy(
    enemy_debuffs: Sequence[object] = (),
    enemy_dots: Sequence[object] = (),
    *,
    max_def: float = 0.0,
    damage_resistance_attrs: dict[str, float] | None = None,
    anomaly_resistance_attrs: dict[int, float] | None = None,
    stun_resistance_attrs: dict[int, float] | None = None,
) -> SimpleNamespace:
    resistance_values = {
        "PHY_damage_resistance": 0.0,
        "FIRE_damage_resistance": 0.0,
        "ICE_damage_resistance": 0.0,
        "ELECTRIC_damage_resistance": 0.0,
        "ETHER_damage_resistance": 0.0,
    }
    if damage_resistance_attrs is not None:
        resistance_values.update(damage_resistance_attrs)
    return SimpleNamespace(
        dynamic=SimpleNamespace(
            dynamic_debuff_list=list(enemy_debuffs),
            dynamic_dot_list=list(enemy_dots),
            stun=False,
        ),
        sim_instance=SimpleNamespace(marker="sim"),
        max_DEF=max_def,
        stun_DMG_take_ratio=0.0,
        anomaly_resistance_dict=(
            {} if anomaly_resistance_attrs is None else dict(anomaly_resistance_attrs)
        ),
        stun_resistance_dict=({} if stun_resistance_attrs is None else dict(stun_resistance_attrs)),
        **resistance_values,
    )


def _make_skill_node(
    *,
    char_name: str,
    damage_ratio: float,
    stun_ratio: float = 0.0,
    hit_times: int,
    diff_multiplier: int,
    element_type: int = 0,
    trigger_buff_level: int = 0,
    anomaly_accumulation: float = 0.0,
    element_damage_percent: float = 1.0,
    labels: dict[str, int] | None = None,
) -> SkillNode:
    skill = SimpleNamespace(
        skill_tag=f"{char_name}-formula-oracle",
        char_name=char_name,
        hit_times=hit_times,
        labels=labels,
        ticks=max(hit_times + 1, 2),
        tick_list=[],
        damage_ratio=damage_ratio,
        stun_ratio=stun_ratio,
        diff_multiplier=diff_multiplier,
        element_type=element_type,
        trigger_buff_level=trigger_buff_level,
        anomaly_accumulation=anomaly_accumulation,
        element_damage_percent=element_damage_percent,
    )
    return SkillNode(cast(Any, skill), preload_tick=0)


def _make_attribute_read_fixture(
    *,
    name: str = "折枝剑歌",
    atk: float = 0.0,
    hp: float = 0.0,
    defense: float = 0.0,
    am: float = 0.0,
    ap: float = 0.0,
    imp: float = 0.0,
    crit_rate: float = 0.0,
    crit_damage: float = 0.0,
    static_statement_attrs: dict[str, float] | None = None,
    damage_ratio: float | None = None,
    stun_ratio: float = 0.0,
    hit_times: int = 1,
    diff_multiplier: int = 0,
    element_type: int = 0,
    trigger_buff_level: int = 0,
    skill_labels: dict[str, int] | None = None,
    anomaly_accumulation: float = 0.0,
    element_damage_percent: float = 1.0,
    enemy_max_def: float = 0.0,
    enemy_damage_resistance_attrs: dict[str, float] | None = None,
    enemy_anomaly_resistance_attrs: dict[int, float] | None = None,
    enemy_stun_resistance_attrs: dict[int, float] | None = None,
    char_buff_count: int = 1,
    enemy_debuff_count: int = 1,
    enemy_dot_count: int = 0,
) -> _AttributeReadFixture:
    char_buffs = tuple(object() for _ in range(char_buff_count))
    enemy_debuffs = tuple(object() for _ in range(enemy_debuff_count))
    enemy_dots = tuple(object() for _ in range(enemy_dot_count))
    char = _make_character(
        name=name,
        atk=atk,
        hp=hp,
        defense=defense,
        am=am,
        ap=ap,
        imp=imp,
        crit_rate=crit_rate,
        crit_damage=crit_damage,
        static_statement_attrs=static_statement_attrs,
    )
    enemy = _make_enemy(
        enemy_debuffs,
        enemy_dots,
        max_def=enemy_max_def,
        damage_resistance_attrs=enemy_damage_resistance_attrs,
        anomaly_resistance_attrs=enemy_anomaly_resistance_attrs,
        stun_resistance_attrs=enemy_stun_resistance_attrs,
    )
    active_buff_view = {char.NAME: list(char_buffs)}
    enemy.sim_instance.buff_runtime_state = BuffRuntimeState(
        template_registry={},
        pending_queue={},
        active_store=active_buff_view,
        enemy_mirror=enemy.dynamic.dynamic_debuff_list,
    )
    query_node = (
        _make_skill_node(
            char_name=char.NAME,
            damage_ratio=damage_ratio,
            stun_ratio=stun_ratio,
            hit_times=hit_times,
            diff_multiplier=diff_multiplier,
            element_type=element_type,
            trigger_buff_level=trigger_buff_level,
            anomaly_accumulation=anomaly_accumulation,
            element_damage_percent=element_damage_percent,
            labels=skill_labels,
        )
        if damage_ratio is not None
        else None
    )
    return _AttributeReadFixture(
        context=create_anomaly_attribute_read_context(
            enemy=cast(Any, enemy),
            active_buff_view=active_buff_view,
            character=cast(Any, char),
            query_node=query_node,
        ),
        active_buff_view=active_buff_view,
        enemy=enemy,
        char=char,
        expected_enabled_buff=char_buffs + enemy_debuffs,
        expected_enemy_dot_buff=enemy_dots,
    )


def _make_anomaly_snapshot(values: Sequence[float] | None = None) -> np.ndarray:
    if values is None:
        values = (
            100.0,
            1.10,
            2.0,
            60.0,
            1.30,
            999.0,
            0.05,
            8.0,
            0.10,
            1.20,
            1.40,
        )
    return np.array([list(values)], dtype=np.float64)


def _make_settled_anomaly_formula_fixture(
    *,
    character_name: str = "异常公式角色",
    element_type: int = 0,
    snapshot: np.ndarray | None = None,
    scaling_factor: float = 1.25,
) -> _AnomalyFormulaFixture:
    source_snapshot = _make_anomaly_snapshot() if snapshot is None else snapshot
    sim_instance = SimpleNamespace(tick=321)
    character = _make_character(name=character_name)
    activation = SimpleNamespace(skill=SimpleNamespace(char_obj=character))
    enemy = _make_enemy()
    active_buff_view: dict[str, list[object]] = {character.NAME: []}
    anomaly_bar = AnomalyBar(sim_instance=cast(Any, sim_instance), element_type=element_type)
    anomaly_bar.current_ndarray = np.array(source_snapshot, dtype=np.float64, copy=True)
    anomaly_bar.current_effective_anomaly = np.float64(30.0)
    anomaly_bar.current_anomaly = np.float64(129.0)
    anomaly_bar.settled = True
    anomaly_bar.activated_by = cast(Any, activation)
    anomaly_bar.scaling_factor = scaling_factor
    return _AnomalyFormulaFixture(
        sim_instance=sim_instance,
        character=character,
        activation=activation,
        enemy=enemy,
        active_buff_view=active_buff_view,
        source_snapshot=source_snapshot,
        anomaly_bar=anomaly_bar,
    )


def _reader_snapshot_data(context: BuffAttributeReadContext) -> Any:
    return CalculatorBuffAttributeReader._build_formula_snapshot(context)


def _legacy_multiplier_data(fixture: _AttributeReadFixture) -> MultiplierData:
    return MultiplierData(
        cast(Any, fixture.enemy),
        fixture.active_buff_view,
        cast(Any, fixture.char),
        cast(Any, fixture.context.query_node),
    )


def _legacy_impact_oracle(fixture: _AttributeReadFixture) -> float:
    return Calculator.StunMul.cal_imp(_legacy_multiplier_data(fixture))


def _legacy_full_crit_rate_oracle(fixture: _AttributeReadFixture) -> float:
    return Calculator.RegularMul.cal_crit_rate(_legacy_multiplier_data(fixture))


def _legacy_personal_crit_rate_oracle(fixture: _AttributeReadFixture) -> float:
    return Calculator.RegularMul.cal_personal_crit_rate(_legacy_multiplier_data(fixture))


def _legacy_personal_crit_damage_oracle(fixture: _AttributeReadFixture) -> float:
    return Calculator.RegularMul.cal_personal_crit_dmg(_legacy_multiplier_data(fixture))


def _legacy_pen_ratio_oracle(fixture: _AttributeReadFixture) -> float:
    return Calculator.RegularMul.cal_pen_ratio(_legacy_multiplier_data(fixture))


def _assert_aggregation_calls(
    aggregation_calls: list[_AggregationCall],
    fixture: _AttributeReadFixture,
    *,
    times: int = 2,
) -> None:
    assert (
        aggregation_calls
        == [
            (
                fixture.expected_enabled_buff,
                fixture.context.query_node,
                fixture.enemy.sim_instance,
                fixture.char.NAME,
            )
        ]
        * times
    )


def test_create_anomaly_attribute_read_context_preserves_inputs() -> None:
    char = _make_character(am=115.0, ap=375.0)
    enemy = _make_enemy()
    active_buff_view = {char.NAME: [object()]}
    query_node = SimpleNamespace(marker="node")

    context = create_anomaly_attribute_read_context(
        enemy=cast(Any, enemy),
        active_buff_view=active_buff_view,
        character=cast(Any, char),
        query_node=cast(Any, query_node),
    )

    assert isinstance(context, BuffAttributeReadContext)
    assert context.enemy is enemy
    assert context.active_buff_view is active_buff_view
    assert context.character is char
    assert context.query_node is query_node


def test_calculator_runtime_read_context_uses_explicit_enemy_debuffs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    char = _make_character(name="runtime-reader", am=100.0)
    char_buff = object()
    enemy_debuff = object()
    query_node = SimpleNamespace(marker="runtime-query")
    sim_instance = SimpleNamespace(marker="runtime-sim")
    enemy = SimpleNamespace(
        dynamic=_ForbiddenEnemyDynamic(),
        sim_instance=sim_instance,
    )
    runtime_view = _CalculatorRuntimeView(
        {
            char.NAME: (char_buff,),
            "enemy": (enemy_debuff,),
        }
    )
    aggregation_calls = _patch_buff_aggregation(
        monkeypatch,
        _dynamic_statement_by_attr(field_anomaly_mastery=0.2),
    )

    context = create_calculator_runtime_read_context(
        runtime_view=runtime_view,
        enemy=cast(Any, enemy),
        character=cast(Any, char),
        query_node=cast(Any, query_node),
        sim_instance=sim_instance,
    )
    reader_value = CalculatorBuffAttributeReader().read_anomaly_mastery(context)

    assert isinstance(context, CalculatorRuntimeReadContext)
    assert context.active_buffs_by_beneficiary is runtime_view.active_buff_view
    assert context.enemy_debuffs == (enemy_debuff,)
    assert reader_value == pytest.approx(120.0)
    assert aggregation_calls == [
        (
            (char_buff, enemy_debuff),
            query_node,
            sim_instance,
            char.NAME,
        )
    ]
    assert runtime_view.active_buff_beneficiaries == ["enemy"]
    assert runtime_view.active_view_calls == 1


def test_calculator_runtime_read_context_can_be_built_from_event_context() -> None:
    char = _make_character(name="event-context-reader", ap=300.0)
    enemy_debuff = object()
    sim_instance = SimpleNamespace(marker="event-sim")
    enemy = SimpleNamespace(
        dynamic=_ForbiddenEnemyDynamic(),
        sim_instance=SimpleNamespace(marker="legacy-sim"),
    )
    runtime_view = _CalculatorRuntimeView(
        {
            char.NAME: (),
            "enemy": (enemy_debuff,),
        }
    )
    event_context = EventContext(
        data=SimpleNamespace(),
        tick=10,
        enemy=cast(Any, enemy),
        buff_runtime_view=runtime_view,
        runtime_command_port=SimpleNamespace(),
        action_stack=SimpleNamespace(),
        sim_instance=cast(Any, sim_instance),
    )

    context = create_calculator_runtime_read_context_from_event_context(
        event_context=event_context,
        character=cast(Any, char),
        beneficiary=char.NAME,
    )

    assert context.enemy is enemy
    assert context.active_buff_view is runtime_view.active_buff_view
    assert context.enemy_debuffs == (enemy_debuff,)
    assert context.formula_sim_instance is sim_instance
    assert context.formula_char_name == char.NAME
    assert runtime_view.active_buff_beneficiaries == ["enemy"]
    assert runtime_view.active_view_calls == 1


def test_calculator_runtime_read_context_can_be_built_from_sim_instance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    char = _make_character(name="sim-instance-reader", am=100.0)
    char_buff = object()
    enemy_debuff = object()
    sim_instance = SimpleNamespace(marker="runtime-sim")
    enemy = SimpleNamespace(
        dynamic=_ForbiddenEnemyDynamic(),
        sim_instance=sim_instance,
    )
    sim_instance.buff_runtime_state = BuffRuntimeState(
        template_registry={},
        pending_queue={},
        active_store={char.NAME: [char_buff], "enemy": [enemy_debuff]},
        enemy_mirror=[],
    )
    aggregation_calls = _patch_buff_aggregation(
        monkeypatch,
        _dynamic_statement_by_attr(field_anomaly_mastery=0.2),
    )

    context = create_calculator_runtime_read_context_from_sim_instance(
        sim_instance=sim_instance,
        enemy=cast(Any, enemy),
        character=cast(Any, char),
    )
    reader_value = CalculatorBuffAttributeReader().read_anomaly_mastery(context)

    assert isinstance(context, CalculatorRuntimeReadContext)
    assert context.enemy_debuffs == (enemy_debuff,)
    assert tuple(context.active_buff_view[char.NAME]) == (char_buff,)
    assert reader_value == pytest.approx(120.0)
    assert aggregation_calls == [
        (
            (char_buff, enemy_debuff),
            None,
            sim_instance,
            char.NAME,
        )
    ]


def test_calculator_buff_bonus_context_from_sim_instance_reads_only_beneficiary_buffs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    char_buff = object()
    enemy_debuff = object()
    sim_instance = SimpleNamespace(marker="bonus-sim")
    sim_instance.buff_runtime_state = BuffRuntimeState(
        template_registry={},
        pending_queue={},
        active_store={"panel-reader": [char_buff], "enemy": [enemy_debuff]},
        enemy_mirror=[],
    )
    aggregation_calls: list[_AggregationCall] = []

    def fake_cal_buff_total_bonus(
        *,
        enabled_buff: tuple[object, ...],
        judge_obj: object | None,
        sim_instance: object,
        char_name: str | None,
    ) -> dict[str, float]:
        aggregation_calls.append((enabled_buff, judge_obj, sim_instance, char_name))
        return {"喧响获得效率": 0.25}

    monkeypatch.setattr(
        calculator_module,
        "cal_buff_total_bonus",
        fake_cal_buff_total_bonus,
    )

    context = create_calculator_buff_bonus_context_from_sim_instance(
        sim_instance=sim_instance,
        beneficiary="panel-reader",
    )
    bonus = get_calculator_buff_attribute_reader_service().calculate_buff_total_bonus(context)

    assert isinstance(context, CalculatorBuffBonusReadContext)
    assert bonus == {"喧响获得效率": 0.25}
    assert aggregation_calls == [
        (
            (char_buff,),
            None,
            sim_instance,
            "panel-reader",
        )
    ]


def test_character_update_decibel_uses_runtime_bonus_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    char_buff = object()
    sim_instance = SimpleNamespace()
    sim_instance.buff_runtime_state = BuffRuntimeState(
        template_registry={},
        pending_queue={},
        active_store={"decibel-reader": [char_buff]},
        enemy_mirror=[],
    )
    character = SimpleNamespace(
        NAME="decibel-reader",
        sim_instance=sim_instance,
        decibel=100.0,
    )
    aggregation_calls: list[_AggregationCall] = []

    def fake_cal_buff_total_bonus(
        *,
        enabled_buff: tuple[object, ...],
        judge_obj: object | None,
        sim_instance: object,
        char_name: str | None,
    ) -> dict[str, float]:
        aggregation_calls.append((enabled_buff, judge_obj, sim_instance, char_name))
        return {"喧响获得效率": 0.5}

    monkeypatch.setattr(
        calculator_module,
        "cal_buff_total_bonus",
        fake_cal_buff_total_bonus,
    )

    Character.update_decibel(cast(Any, character), 40.0)

    assert character.decibel == pytest.approx(160.0)
    assert not hasattr(sim_instance, "global_stats")
    assert aggregation_calls == [
        (
            (char_buff,),
            None,
            sim_instance,
            "decibel-reader",
        )
    ]


def test_character_update_decibel_handles_missing_runtime_buff_list(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sim_instance = SimpleNamespace()
    sim_instance.buff_runtime_state = BuffRuntimeState(
        template_registry={},
        pending_queue={},
        active_store={},
        enemy_mirror=[],
    )
    character = SimpleNamespace(
        NAME="missing-buff-reader",
        sim_instance=sim_instance,
        decibel=50.0,
    )
    aggregation_calls: list[_AggregationCall] = []

    def fake_cal_buff_total_bonus(
        *,
        enabled_buff: tuple[object, ...],
        judge_obj: object | None,
        sim_instance: object,
        char_name: str | None,
    ) -> dict[str, float]:
        aggregation_calls.append((enabled_buff, judge_obj, sim_instance, char_name))
        return {}

    monkeypatch.setattr(
        calculator_module,
        "cal_buff_total_bonus",
        fake_cal_buff_total_bonus,
    )

    Character.update_decibel(cast(Any, character), 25.0)

    assert character.decibel == pytest.approx(75.0)
    assert aggregation_calls == [
        (
            (),
            None,
            sim_instance,
            "missing-buff-reader",
        )
    ]


def test_sp_update_data_uses_runtime_bonus_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    char_buff = object()
    sim_instance = SimpleNamespace(marker="sp-sim")
    runtime_state = BuffRuntimeState(
        template_registry={},
        pending_queue={},
        active_store={"sp-reader": [char_buff]},
        enemy_mirror=[],
    )
    character = SimpleNamespace(
        NAME="sp-reader",
        statement=SimpleNamespace(sp_regen=1.0),
    )
    aggregation_calls: list[_AggregationCall] = []

    def fake_cal_buff_total_bonus(
        *,
        enabled_buff: tuple[object, ...],
        judge_obj: object | None,
        sim_instance: object,
        char_name: str | None,
    ) -> dict[str, float]:
        aggregation_calls.append((enabled_buff, judge_obj, sim_instance, char_name))
        return {
            "能量自动恢复": 0.25,
            "局内能量自动恢复": 0.5,
            "局内能量获得效率": 1.0,
        }

    monkeypatch.setattr(
        calculator_module,
        "cal_buff_total_bonus",
        fake_cal_buff_total_bonus,
    )

    sp_update_data = SPUpdateData(
        char_obj=cast(Any, character),
        runtime_view=runtime_state.create_read_port(),
        sim_instance=sim_instance,
    )

    assert sp_update_data.get_sp_regen() == pytest.approx(3.5)
    assert aggregation_calls == [
        (
            (char_buff,),
            None,
            sim_instance,
            "sp-reader",
        )
    ]


def test_calculator_reader_service_public_surface_matches_reader() -> None:
    reader_methods = {
        name
        for name, value in vars(CalculatorBuffAttributeReader).items()
        if name.startswith("read_") and callable(value)
    }
    service_methods = {
        name
        for name, value in vars(CalculatorBuffAttributeReaderService).items()
        if name.startswith("read_") and callable(value)
    }
    service = get_calculator_buff_attribute_reader_service()

    assert (
        service_methods
        == reader_methods
        == {
            "read_anomaly_mastery",
            "read_anomaly_proficiency",
            "read_impact",
            "read_full_crit_rate",
            "read_personal_crit_rate",
            "read_personal_crit_damage",
            "read_pen_ratio",
        }
    )
    assert service is get_calculator_buff_attribute_reader_service()
    assert isinstance(service, CalculatorBuffAttributeReaderService)


def test_calculator_reader_service_is_shared_and_context_scoped(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = get_calculator_buff_attribute_reader_service()
    first_fixture = _make_attribute_read_fixture(name="service-first", am=100.0)
    second_fixture = _make_attribute_read_fixture(name="service-second", am=250.0)
    aggregation_calls = _patch_buff_aggregation(
        monkeypatch,
        _dynamic_statement_by_attr(field_anomaly_mastery=0.0),
    )

    assert service.read_anomaly_mastery(first_fixture.context) == pytest.approx(100.0)
    assert service.read_anomaly_mastery(second_fixture.context) == pytest.approx(250.0)
    assert service.read_anomaly_mastery(first_fixture.context) == pytest.approx(100.0)
    assert aggregation_calls == [
        (
            first_fixture.expected_enabled_buff,
            None,
            first_fixture.enemy.sim_instance,
            first_fixture.char.NAME,
        ),
        (
            second_fixture.expected_enabled_buff,
            None,
            second_fixture.enemy.sim_instance,
            second_fixture.char.NAME,
        ),
        (
            first_fixture.expected_enabled_buff,
            None,
            first_fixture.enemy.sim_instance,
            first_fixture.char.NAME,
        ),
    ]


def _make_cache_contract_buff(effect_value: float) -> Buff:
    buff = cast(Buff, Buff.__new__(Buff))
    buff.dy = SimpleNamespace(active=True, count=1)
    buff.ft = SimpleNamespace(
        label={},
        index="cache-contract-buff",
        beneficiary="cache-reader",
    )
    buff.effect_dct = {"局内攻击力": effect_value}
    buff.sim_instance = object()
    return buff


def test_shared_buff_total_bonus_cache_key_keeps_runtime_identity_fields() -> None:
    data_analyzer_module.cal_buff_total_bonus.cache_clear()
    sim_instance = object()
    buff = _make_cache_contract_buff(1.0)

    try:
        first_result = data_analyzer_module.cal_buff_total_bonus(
            (buff,),
            sim_instance=sim_instance,
            char_name="cache-reader",
        )
        buff.effect_dct["局内攻击力"] = 9.0
        second_result = data_analyzer_module.cal_buff_total_bonus(
            (buff,),
            sim_instance=sim_instance,
            char_name="cache-reader",
        )
        third_result = data_analyzer_module.cal_buff_total_bonus(
            (buff,),
            sim_instance=sim_instance,
            char_name="other-reader",
        )
        cache_info = data_analyzer_module.cal_buff_total_bonus.cache_info()
    finally:
        data_analyzer_module.cal_buff_total_bonus.cache_clear()

    assert first_result == {"局内攻击力": 1.0}
    assert second_result is first_result
    assert third_result == {"局内攻击力": 9.0}
    assert third_result is not first_result
    assert cache_info.hits == 1
    assert cache_info.misses == 2


def _patch_buff_aggregation(
    monkeypatch: pytest.MonkeyPatch,
    dynamic_statement: dict[str, float],
) -> list[_AggregationCall]:
    aggregation_calls: list[_AggregationCall] = []

    def fake_cal_buff_total_bonus(
        *,
        enabled_buff: tuple[object, ...],
        judge_obj: object | None,
        sim_instance: object,
        char_name: str | None,
    ) -> dict[str, float]:
        aggregation_calls.append((enabled_buff, judge_obj, sim_instance, char_name))
        return dict(dynamic_statement)

    monkeypatch.setattr(
        calculator_module,
        "cal_buff_total_bonus",
        fake_cal_buff_total_bonus,
    )
    return aggregation_calls


def _dynamic_statement_by_attr(**attrs: float) -> dict[str, float]:
    effect_by_attr = {
        cast(str, attr): cast(str, effect)
        for effect, attr in calculator_module.buff_effect_trans.items()
    }
    return {effect_by_attr[attr]: value for attr, value in attrs.items()}


def _make_anomaly_formula_fixture_from_case(
    case: _AnomalySnapshotOracleCase,
) -> _AnomalyFormulaFixture:
    return _make_settled_anomaly_formula_fixture(
        character_name=case.character_name,
        snapshot=_make_anomaly_snapshot(case.snapshot_values),
        scaling_factor=case.scaling_factor,
    )


def _run_formula_oracle_case(
    monkeypatch: pytest.MonkeyPatch,
    case: _FormulaOracleCase,
) -> _AttributeReadFixture:
    _reset_formula_oracle_caches()
    fixture = _make_attribute_read_fixture(**case.fixture_kwargs)
    aggregation_calls = _patch_buff_aggregation(
        monkeypatch,
        _dynamic_statement_by_attr(**case.dynamic_attrs),
    )

    retained_data = _legacy_multiplier_data(fixture)
    reader_snapshot_data = _reader_snapshot_data(fixture.context)
    for attr_name, expected_value in case.expected_dynamic_fields.items():
        for source_label, data in (
            ("retained", retained_data),
            ("reader-snapshot", reader_snapshot_data),
        ):
            assert getattr(data.dynamic, attr_name) == case.tolerance.approx(expected_value), (
                f"{case.case_id}:{source_label}:{attr_name}"
            )

    reader = CalculatorBuffAttributeReader()
    reader_expectation_count = 0
    for expectation in case.expectations:
        expected = case.tolerance.approx(expectation.expected_value)
        assert expectation.retained_value(retained_data) == expected, (
            f"{case.case_id}:{expectation.label}:retained"
        )
        assert expectation.retained_value(reader_snapshot_data) == expected, (
            f"{case.case_id}:{expectation.label}:reader-snapshot"
        )
        if expectation.reader_value is not None:
            reader_expectation_count += 1
            assert expectation.reader_value(reader, fixture.context) == expected, (
                f"{case.case_id}:{expectation.label}:reader"
            )

    expected_aggregation_times = case.expected_aggregation_times
    if expected_aggregation_times is None:
        expected_aggregation_times = 2 + reader_expectation_count
    _assert_aggregation_calls(
        aggregation_calls,
        fixture,
        times=expected_aggregation_times,
    )
    for enabled_buff, *_ in aggregation_calls:
        assert all(dot not in enabled_buff for dot in fixture.expected_enemy_dot_buff), (
            f"{case.case_id}:enemy-dot-exclusion"
        )
    return fixture


def _apply_copied_output_payload(
    anomaly_bar: Any,
    payload_fields: dict[str, Any],
) -> None:
    for field_name, value in payload_fields.items():
        setattr(anomaly_bar, field_name, value)


def _copy_output_from_payload_case(
    case: _CopiedOutputPayloadCase,
    fixture: _AnomalyFormulaFixture,
) -> tuple[Any, SimpleNamespace]:
    runtime_sim = SimpleNamespace(tick=case.runtime_tick)
    if case.copied_kind == "new_anomaly":
        return (
            NewAnomaly(
                cast(Any, fixture.anomaly_bar),
                active_by=cast(Any, fixture.activation),
                sim_instance=cast(Any, runtime_sim),
            ),
            runtime_sim,
        )
    if case.copied_kind == "polarity_disorder":
        assert case.polarity_ratio is not None
        return (
            PolarityDisorder(
                cast(Any, fixture.anomaly_bar),
                case.polarity_ratio,
                active_by=cast(Any, fixture.activation),
                sim_instance=cast(Any, runtime_sim),
            ),
            runtime_sim,
        )
    if case.copied_kind == "disorder":
        return (
            Disorder(
                cast(Any, fixture.anomaly_bar),
                active_by=cast(Any, fixture.activation),
                sim_instance=cast(Any, runtime_sim),
            ),
            runtime_sim,
        )
    raise AssertionError(f"Unknown copied-output oracle case: {case.copied_kind}")


_MIGRATED_READER_SEAM_SAMPLES = (
    _MigratedReaderSeamSample(
        case_id="p2a-alice-am",
        phase="P2-A",
        migrated_file="zsim/sim_progress/Buff/BuffXLogic/AliceAdditionalAbilityApBonus.py",
        formula_key="cal_am",
        fixture_kwargs={
            "name": "Alice",
            "am": 100.0,
            "char_buff_count": 1,
            "enemy_debuff_count": 1,
        },
        dynamic_attrs={
            "field_anomaly_mastery": 0.2,
            "anomaly_mastery": 15.0,
        },
        expected_value=135.0,
    ),
    _MigratedReaderSeamSample(
        case_id="p2a-jane-ap",
        phase="P2-A",
        migrated_file="zsim/sim_progress/Buff/BuffXLogic/JaneCinema1APTransToDmgBonus.py",
        formula_key="cal_ap",
        fixture_kwargs={
            "name": "Jane",
            "ap": 300.0,
            "char_buff_count": 1,
            "enemy_debuff_count": 1,
        },
        dynamic_attrs={
            "field_anomaly_proficiency": 0.25,
            "anomaly_proficiency": 40.0,
        },
        expected_value=415.0,
    ),
    _MigratedReaderSeamSample(
        case_id="p2b-qingyi-impact",
        phase="P2-B",
        migrated_file=(
            "zsim/sim_progress/Buff/BuffXLogic/QingYiAdditionalAbilityStunConvertToATK.py"
        ),
        formula_key="cal_imp",
        fixture_kwargs={
            "name": "Qingyi",
            "imp": 80.0,
            "char_buff_count": 1,
            "enemy_debuff_count": 1,
        },
        dynamic_attrs={
            "field_imp_percentage": 0.1,
            "imp": 9.0,
        },
        expected_value=97.0,
    ),
    _MigratedReaderSeamSample(
        case_id="p2b-cannon-rotor-full-crit",
        phase="P2-B",
        migrated_file="zsim/sim_progress/Buff/BuffXLogic/CannonRotor.py",
        formula_key="cal_crit_rate",
        fixture_kwargs={
            "name": "CannonRotor",
            "crit_rate": 0.2,
            "char_buff_count": 1,
            "enemy_debuff_count": 1,
        },
        dynamic_attrs={
            "field_crit_rate": 0.05,
            "crit_rate": 0.1,
            "crit_rate_received_increase": 0.25,
        },
        expected_value=0.6,
    ),
    _MigratedReaderSeamSample(
        case_id="p2b-anby-personal-crit-dmg",
        phase="P2-B",
        migrated_file=("zsim/sim_progress/Buff/BuffXLogic/Soldier0AnbyCoreSkillCritDMGBonus.py"),
        formula_key="cal_personal_crit_dmg",
        fixture_kwargs={
            "name": "Soldier0Anby",
            "crit_damage": 0.5,
            "char_buff_count": 1,
            "enemy_debuff_count": 1,
        },
        dynamic_attrs={
            "field_crit_dmg": 0.2,
            "crit_dmg": 0.3,
            "received_crit_dmg_bonus": 0.4,
        },
        expected_value=1.0,
    ),
)


def _retained_formula_value(formula_key: str, data: Any) -> Any:
    if formula_key == "cal_am":
        return Calculator.AnomalyMul.cal_am(data)
    if formula_key == "cal_ap":
        return Calculator.AnomalyMul.cal_ap(data)
    if formula_key == "cal_imp":
        return Calculator.StunMul.cal_imp(data)
    if formula_key == "cal_crit_rate":
        return Calculator.RegularMul.cal_crit_rate(data)
    if formula_key == "cal_personal_crit_rate":
        return Calculator.RegularMul.cal_personal_crit_rate(data)
    if formula_key == "cal_personal_crit_dmg":
        return Calculator.RegularMul.cal_personal_crit_dmg(data)
    raise AssertionError(f"Unknown migrated reader formula sample: {formula_key}")


def _reader_formula_value(
    formula_key: str,
    reader: CalculatorBuffAttributeReader,
    context: BuffAttributeReadContext,
) -> Any:
    if formula_key == "cal_am":
        return reader.read_anomaly_mastery(context)
    if formula_key == "cal_ap":
        return reader.read_anomaly_proficiency(context)
    if formula_key == "cal_imp":
        return reader.read_impact(context)
    if formula_key == "cal_crit_rate":
        return reader.read_full_crit_rate(context)
    if formula_key == "cal_personal_crit_rate":
        return reader.read_personal_crit_rate(context)
    if formula_key == "cal_personal_crit_dmg":
        return reader.read_personal_crit_damage(context)
    raise AssertionError(f"Unknown migrated reader formula sample: {formula_key}")


def _regular_mul_oracle() -> Any:
    return Calculator.RegularMul.__new__(Calculator.RegularMul)


def _anomaly_mul_oracle() -> Any:
    return Calculator.AnomalyMul.__new__(Calculator.AnomalyMul)


def _regular_mul_base_attr(data: MultiplierData, base_attr: int) -> float:
    return cast(float, _regular_mul_oracle().cal_base_attr(base_attr, data))


def _regular_mul_base_dmg(data: MultiplierData) -> float:
    return cast(float, _regular_mul_oracle().cal_base_dmg(data))


def _regular_mul_defense_mul(data: MultiplierData) -> float:
    return cast(float, _regular_mul_oracle().cal_defense_mul(data))


def _regular_mul_crit_expect(data: MultiplierData) -> float:
    oracle = _regular_mul_oracle()
    oracle.crit_rate = Calculator.RegularMul.cal_crit_rate(data)
    oracle.crit_dmg = Calculator.RegularMul.cal_crit_dmg(data)
    return cast(float, oracle.cal_crit_expect(data))


def _regular_mul_branch_matrix_values(data: MultiplierData) -> dict[str, float]:
    oracle = _regular_mul_oracle()
    return {
        "cal_base_dmg": cast(float, oracle.cal_base_dmg(data)),
        "cal_dmg_bonus": Calculator.RegularMul.cal_dmg_bonus(data),
        "cal_crit_rate": Calculator.RegularMul.cal_crit_rate(data),
        "cal_crit_dmg": Calculator.RegularMul.cal_crit_dmg(data),
        "cal_crit_expect": _regular_mul_crit_expect(data),
        "cal_personal_crit_dmg": Calculator.RegularMul.cal_personal_crit_dmg(data),
        "cal_defense_mul": cast(float, oracle.cal_defense_mul(data)),
        "cal_res_mul": Calculator.RegularMul.cal_res_mul(data),
        "cal_dmg_vulnerability": Calculator.RegularMul.cal_dmg_vulnerability(data),
        "cal_stun_vulnerability": Calculator.RegularMul.cal_stun_vulnerability(data),
        "cal_special_mul": Calculator.RegularMul.cal_special_mul(data),
        "cal_sheer_dmg_bonus": Calculator.RegularMul.cal_sheer_dmg_bonus(data),
    }


def _anomaly_mul_ap_mul(data: MultiplierData) -> float:
    return cast(float, _anomaly_mul_oracle().cal_ap_mul(data))


def _anomaly_mul_crit(data: MultiplierData) -> float:
    return cast(float, _anomaly_mul_oracle().cal_anomaly_crit(data))


def _anomaly_mul_res_pen(data: MultiplierData) -> float:
    return cast(float, _anomaly_mul_oracle().cal_res_pen(data))


_FORMULA_ORACLE_TABLE_CASES = (
    _FormulaOracleCase(
        case_id="regular-base-dmg-neutral-atk",
        fixture_kwargs={
            "name": "直伤基础-攻击中性",
            "atk": 100.0,
            "damage_ratio": 2.0,
            "hit_times": 1,
            "diff_multiplier": 0,
            "char_buff_count": 0,
            "enemy_debuff_count": 0,
            "enemy_dot_count": 0,
        },
        dynamic_attrs={},
        expected_dynamic_fields={
            "field_atk_percentage": 0.0,
            "atk": 0.0,
            "extra_damage_ratio": 0.0,
            "base_dmg_increase_percentage": 0.0,
            "base_dmg_increase": 0.0,
        },
        expectations=(
            _FormulaOracleExpectation(
                label="cal_base_attr_atk",
                expected_value=100.0,
                retained_value=lambda data: _regular_mul_base_attr(data, 0),
            ),
            _FormulaOracleExpectation(
                label="cal_base_dmg",
                expected_value=200.0,
                retained_value=_regular_mul_base_dmg,
            ),
        ),
    ),
    _FormulaOracleCase(
        case_id="regular-base-attr-static-hp",
        fixture_kwargs={
            "name": "直伤基础-生命静态",
            "hp": 1250.0,
            "damage_ratio": 3.0,
            "hit_times": 2,
            "diff_multiplier": 1,
            "char_buff_count": 0,
            "enemy_debuff_count": 0,
            "enemy_dot_count": 0,
        },
        dynamic_attrs={},
        expected_dynamic_fields={
            "field_hp_percentage": 0.0,
            "hp": 0.0,
            "extra_damage_ratio": 0.0,
            "base_dmg_increase_percentage": 0.0,
            "base_dmg_increase": 0.0,
        },
        expectations=(
            _FormulaOracleExpectation(
                label="cal_base_attr_hp",
                expected_value=1250.0,
                retained_value=lambda data: _regular_mul_base_attr(data, 1),
            ),
            _FormulaOracleExpectation(
                label="cal_base_dmg",
                expected_value=1875.0,
                retained_value=_regular_mul_base_dmg,
            ),
        ),
    ),
    _FormulaOracleCase(
        case_id="regular-base-attr-dynamic-defense",
        fixture_kwargs={
            "name": "regular base attr defense dynamic",
            "defense": 240.0,
            "damage_ratio": 2.5,
            "hit_times": 1,
            "diff_multiplier": 2,
            "char_buff_count": 1,
            "enemy_debuff_count": 1,
            "enemy_dot_count": 0,
        },
        dynamic_attrs={
            "field_def_percentage": 0.5,
            "defense": 30.0,
            "extra_damage_ratio": 0.2,
            "base_dmg_increase_percentage": 0.1,
            "base_dmg_increase": 7.0,
        },
        expected_dynamic_fields={
            "field_def_percentage": 0.5,
            "defense": 30.0,
            "extra_damage_ratio": 0.2,
            "base_dmg_increase_percentage": 0.1,
            "base_dmg_increase": 7.0,
        },
        expectations=(
            _FormulaOracleExpectation(
                label="cal_base_attr_defense",
                expected_value=390.0,
                retained_value=lambda data: _regular_mul_base_attr(data, 2),
            ),
            _FormulaOracleExpectation(
                label="cal_base_dmg",
                expected_value=1165.3,
                retained_value=_regular_mul_base_dmg,
            ),
        ),
    ),
    _FormulaOracleCase(
        case_id="regular-base-attr-dynamic-anomaly-proficiency",
        fixture_kwargs={
            "name": "regular base attr anomaly proficiency dynamic",
            "ap": 400.0,
            "damage_ratio": 3.6,
            "hit_times": 3,
            "diff_multiplier": 3,
            "char_buff_count": 1,
            "enemy_debuff_count": 1,
            "enemy_dot_count": 0,
        },
        dynamic_attrs={
            "field_anomaly_proficiency": 0.25,
            "anomaly_proficiency": 50.0,
            "extra_damage_ratio": 0.3,
            "base_dmg_increase_percentage": 0.2,
            "base_dmg_increase": 12.0,
        },
        expected_dynamic_fields={
            "field_anomaly_proficiency": 0.25,
            "anomaly_proficiency": 50.0,
            "extra_damage_ratio": 0.3,
            "base_dmg_increase_percentage": 0.2,
            "base_dmg_increase": 12.0,
        },
        expectations=(
            _FormulaOracleExpectation(
                label="cal_base_attr_anomaly_proficiency",
                expected_value=550.0,
                retained_value=lambda data: _regular_mul_base_attr(data, 3),
            ),
            _FormulaOracleExpectation(
                label="cal_base_dmg",
                expected_value=1002.0,
                retained_value=_regular_mul_base_dmg,
            ),
        ),
    ),
    _FormulaOracleCase(
        case_id="regular-base-dmg-dynamic-atk",
        fixture_kwargs={
            "name": "直伤基础-动态攻击",
            "atk": 120.0,
            "damage_ratio": 1.8,
            "hit_times": 2,
            "diff_multiplier": 0,
            "char_buff_count": 1,
            "enemy_debuff_count": 1,
            "enemy_dot_count": 0,
        },
        dynamic_attrs={
            "field_atk_percentage": 0.25,
            "atk": 40.0,
            "extra_damage_ratio": 0.2,
            "base_dmg_increase_percentage": 0.5,
            "base_dmg_increase": 10.0,
        },
        expected_dynamic_fields={
            "field_atk_percentage": 0.25,
            "atk": 40.0,
            "extra_damage_ratio": 0.2,
            "base_dmg_increase_percentage": 0.5,
            "base_dmg_increase": 10.0,
        },
        expectations=(
            _FormulaOracleExpectation(
                label="cal_base_attr_atk",
                expected_value=190.0,
                retained_value=lambda data: _regular_mul_base_attr(data, 0),
            ),
            _FormulaOracleExpectation(
                label="cal_base_dmg",
                expected_value=323.5,
                retained_value=_regular_mul_base_dmg,
            ),
        ),
    ),
    _FormulaOracleCase(
        case_id="regular-multipliers-neutral-zero-boundary",
        fixture_kwargs={
            "name": "直伤乘区-中性边界",
            "damage_ratio": 1.0,
            "hit_times": 1,
            "diff_multiplier": 0,
            "element_type": 1,
            "enemy_max_def": 0.0,
            "enemy_damage_resistance_attrs": {"FIRE_damage_resistance": 0.0},
            "char_buff_count": 0,
            "enemy_debuff_count": 0,
            "enemy_dot_count": 0,
        },
        dynamic_attrs={},
        expected_dynamic_fields={
            "fire_dmg_bonus": 0.0,
            "normal_attack_dmg_bonus": 0.0,
            "aftershock_attack_dmg_bonus": 0.0,
            "all_dmg_bonus": 0.0,
            "percentage_def_reduction": 0.0,
            "def_reduction": 0.0,
            "pen_ratio": 0.0,
            "pen_numeric": 0.0,
            "fire_dmg_res_decrease": 0.0,
            "fire_res_pen_increase": 0.0,
            "all_dmg_res_decrease": 0.0,
            "all_res_pen_increase": 0.0,
            "fire_vulnerability": 0.0,
            "all_vulnerability": 0.0,
        },
        expectations=(
            _FormulaOracleExpectation(
                label="cal_dmg_bonus",
                expected_value=1.0,
                retained_value=lambda data: Calculator.RegularMul.cal_dmg_bonus(data),
            ),
            _FormulaOracleExpectation(
                label="cal_defense_mul",
                expected_value=1.0,
                retained_value=_regular_mul_defense_mul,
            ),
            _FormulaOracleExpectation(
                label="cal_res_mul",
                expected_value=1.0,
                retained_value=lambda data: Calculator.RegularMul.cal_res_mul(data),
            ),
            _FormulaOracleExpectation(
                label="cal_dmg_vulnerability",
                expected_value=1.0,
                retained_value=lambda data: Calculator.RegularMul.cal_dmg_vulnerability(data),
            ),
        ),
    ),
    _FormulaOracleCase(
        case_id="regular-dmg-bonus-character-field-stack",
        fixture_kwargs={
            "name": "直伤乘区-角色增伤堆叠",
            "static_statement_attrs": {"FIRE_DMG_bonus": 0.15},
            "damage_ratio": 1.0,
            "hit_times": 1,
            "diff_multiplier": 0,
            "element_type": 1,
            "trigger_buff_level": 0,
            "skill_labels": {"aftershock_attack": 1},
            "enemy_max_def": 0.0,
            "enemy_damage_resistance_attrs": {"FIRE_damage_resistance": 0.0},
            "char_buff_count": 1,
            "enemy_debuff_count": 0,
            "enemy_dot_count": 0,
        },
        dynamic_attrs={
            "fire_dmg_bonus": 0.25,
            "normal_attack_dmg_bonus": 0.30,
            "aftershock_attack_dmg_bonus": 0.10,
            "all_dmg_bonus": 0.20,
        },
        expected_dynamic_fields={
            "fire_dmg_bonus": 0.25,
            "normal_attack_dmg_bonus": 0.30,
            "aftershock_attack_dmg_bonus": 0.10,
            "all_dmg_bonus": 0.20,
        },
        expectations=(
            _FormulaOracleExpectation(
                label="cal_dmg_bonus",
                expected_value=2.0,
                retained_value=lambda data: Calculator.RegularMul.cal_dmg_bonus(data),
            ),
            _FormulaOracleExpectation(
                label="cal_defense_mul",
                expected_value=1.0,
                retained_value=_regular_mul_defense_mul,
            ),
            _FormulaOracleExpectation(
                label="cal_res_mul",
                expected_value=1.0,
                retained_value=lambda data: Calculator.RegularMul.cal_res_mul(data),
            ),
            _FormulaOracleExpectation(
                label="cal_dmg_vulnerability",
                expected_value=1.0,
                retained_value=lambda data: Calculator.RegularMul.cal_dmg_vulnerability(data),
            ),
        ),
    ),
    _FormulaOracleCase(
        case_id="regular-sheer-dmg-bonus-retained-snapshot",
        fixture_kwargs={
            "name": "直伤乘区-贯穿伤害增幅",
            "damage_ratio": 1.0,
            "hit_times": 1,
            "diff_multiplier": 4,
            "element_type": 4,
            "char_buff_count": 1,
            "enemy_debuff_count": 0,
            "enemy_dot_count": 0,
        },
        dynamic_attrs={
            "sheer_atk": 5.0,
            "sheer_dmg_bonus": 0.45,
        },
        expected_dynamic_fields={
            "sheer_atk": 5.0,
            "sheer_dmg_bonus": 0.45,
        },
        expectations=(
            _FormulaOracleExpectation(
                label="cal_sheer_dmg_bonus",
                expected_value=1.45,
                retained_value=lambda data: Calculator.RegularMul.cal_sheer_dmg_bonus(data),
            ),
        ),
    ),
    _FormulaOracleCase(
        case_id="regular-defense-res-vulnerability-received-stack",
        fixture_kwargs={
            "name": "直伤乘区-敌方与受击字段堆叠",
            "static_statement_attrs": {"PEN_ratio": 0.10, "PEN_numeric": 20.0},
            "damage_ratio": 1.0,
            "hit_times": 1,
            "diff_multiplier": 0,
            "element_type": 1,
            "enemy_max_def": 500.0,
            "enemy_damage_resistance_attrs": {"FIRE_damage_resistance": 0.20},
            "char_buff_count": 0,
            "enemy_debuff_count": 1,
            "enemy_dot_count": 0,
        },
        dynamic_attrs={
            "percentage_def_reduction": 0.25,
            "def_reduction": 50.0,
            "pen_ratio": 0.15,
            "pen_numeric": 30.0,
            "fire_dmg_res_decrease": 0.10,
            "fire_res_pen_increase": 0.05,
            "all_dmg_res_decrease": 0.08,
            "all_res_pen_increase": 0.04,
            "fire_vulnerability": 0.18,
            "all_vulnerability": 0.12,
        },
        expected_dynamic_fields={
            "percentage_def_reduction": 0.25,
            "def_reduction": 50.0,
            "pen_ratio": 0.15,
            "pen_numeric": 30.0,
            "fire_dmg_res_decrease": 0.10,
            "fire_res_pen_increase": 0.05,
            "all_dmg_res_decrease": 0.08,
            "all_res_pen_increase": 0.04,
            "fire_vulnerability": 0.18,
            "all_vulnerability": 0.12,
        },
        expectations=(
            _FormulaOracleExpectation(
                label="cal_dmg_bonus",
                expected_value=1.0,
                retained_value=lambda data: Calculator.RegularMul.cal_dmg_bonus(data),
            ),
            _FormulaOracleExpectation(
                label="cal_defense_mul",
                expected_value=794.0 / (794.0 + 193.75),
                retained_value=_regular_mul_defense_mul,
            ),
            _FormulaOracleExpectation(
                label="cal_res_mul",
                expected_value=1.07,
                retained_value=lambda data: Calculator.RegularMul.cal_res_mul(data),
            ),
            _FormulaOracleExpectation(
                label="cal_dmg_vulnerability",
                expected_value=1.30,
                retained_value=lambda data: Calculator.RegularMul.cal_dmg_vulnerability(data),
            ),
        ),
    ),
    _FormulaOracleCase(
        case_id="regular-crit-received-boundary",
        fixture_kwargs={
            "name": "直伤双暴-受击字段边界",
            "crit_rate": 0.20,
            "crit_damage": 0.50,
            "damage_ratio": 1.0,
            "hit_times": 1,
            "diff_multiplier": 0,
            "char_buff_count": 1,
            "enemy_debuff_count": 1,
            "enemy_dot_count": 0,
        },
        dynamic_attrs={
            "crit_rate": 0.10,
            "field_crit_rate": 0.05,
            "crit_rate_received_increase": 0.25,
            "crit_dmg": 0.30,
            "field_crit_dmg": 0.20,
            "received_crit_dmg_bonus": 0.40,
        },
        expected_dynamic_fields={
            "crit_rate": 0.10,
            "field_crit_rate": 0.05,
            "crit_rate_received_increase": 0.25,
            "crit_dmg": 0.30,
            "field_crit_dmg": 0.20,
            "received_crit_dmg_bonus": 0.40,
        },
        expectations=(
            _FormulaOracleExpectation(
                label="cal_crit_rate",
                expected_value=0.60,
                retained_value=lambda data: Calculator.RegularMul.cal_crit_rate(data),
                reader_value=lambda reader, context: reader.read_full_crit_rate(context),
            ),
            _FormulaOracleExpectation(
                label="cal_personal_crit_rate",
                expected_value=0.35,
                retained_value=lambda data: Calculator.RegularMul.cal_personal_crit_rate(data),
                reader_value=lambda reader, context: reader.read_personal_crit_rate(context),
            ),
            _FormulaOracleExpectation(
                label="cal_crit_dmg",
                expected_value=1.40,
                retained_value=lambda data: Calculator.RegularMul.cal_crit_dmg(data),
            ),
            _FormulaOracleExpectation(
                label="cal_personal_crit_dmg",
                expected_value=1.00,
                retained_value=lambda data: Calculator.RegularMul.cal_personal_crit_dmg(data),
                reader_value=lambda reader, context: reader.read_personal_crit_damage(context),
            ),
        ),
    ),
    _FormulaOracleCase(
        case_id="regular-crit_dmg-aftershock-label-and-received-exact",
        fixture_kwargs={
            "name": "直伤暴伤-aftershock标签精确行",
            "crit_damage": 0.50,
            "damage_ratio": 1.0,
            "hit_times": 1,
            "diff_multiplier": 0,
            "skill_labels": {"aftershock_attack": 1},
            "char_buff_count": 1,
            "enemy_debuff_count": 1,
            "enemy_dot_count": 0,
        },
        dynamic_attrs={
            "crit_dmg": 0.30,
            "field_crit_dmg": 0.10,
            "aftershock_attack_crit_dmg_bonus": 0.20,
            "received_crit_dmg_bonus": 0.40,
        },
        expected_dynamic_fields={
            "crit_dmg": 0.30,
            "field_crit_dmg": 0.10,
            "aftershock_attack_crit_dmg_bonus": 0.20,
            "received_crit_dmg_bonus": 0.40,
        },
        expectations=(
            _FormulaOracleExpectation(
                label="cal_crit_dmg",
                expected_value=1.50,
                retained_value=lambda data: Calculator.RegularMul.cal_crit_dmg(data),
            ),
            _FormulaOracleExpectation(
                label="cal_personal_crit_dmg",
                expected_value=0.90,
                retained_value=lambda data: Calculator.RegularMul.cal_personal_crit_dmg(data),
                reader_value=lambda reader, context: reader.read_personal_crit_damage(context),
            ),
        ),
    ),
    _FormulaOracleCase(
        case_id="regular-crit_dmg-aftershock-label-and-received-cap",
        fixture_kwargs={
            "name": "直伤暴伤-aftershock标签上限行",
            "crit_damage": 0.50,
            "damage_ratio": 1.0,
            "hit_times": 1,
            "diff_multiplier": 0,
            "skill_labels": {"aftershock_attack": 1},
            "char_buff_count": 1,
            "enemy_debuff_count": 1,
            "enemy_dot_count": 0,
        },
        dynamic_attrs={
            "crit_dmg": 0.30,
            "field_crit_dmg": 0.10,
            "aftershock_attack_crit_dmg_bonus": 3.80,
            "received_crit_dmg_bonus": 0.90,
        },
        expected_dynamic_fields={
            "crit_dmg": 0.30,
            "field_crit_dmg": 0.10,
            "aftershock_attack_crit_dmg_bonus": 3.80,
            "received_crit_dmg_bonus": 0.90,
        },
        expectations=(
            _FormulaOracleExpectation(
                label="cal_crit_dmg",
                expected_value=5.00,
                retained_value=lambda data: Calculator.RegularMul.cal_crit_dmg(data),
            ),
            _FormulaOracleExpectation(
                label="cal_personal_crit_dmg",
                expected_value=0.90,
                retained_value=lambda data: Calculator.RegularMul.cal_personal_crit_dmg(data),
                reader_value=lambda reader, context: reader.read_personal_crit_damage(context),
            ),
        ),
    ),
    _FormulaOracleCase(
        case_id="anomaly-mastery-proficiency-buildup-base-damage",
        fixture_kwargs={
            "name": "异常乘区-火积蓄基础伤害",
            "atk": 200.0,
            "am": 120.0,
            "ap": 350.0,
            "damage_ratio": 1.0,
            "hit_times": 2,
            "diff_multiplier": 0,
            "element_type": 1,
            "trigger_buff_level": 2,
            "anomaly_accumulation": 80.0,
            "element_damage_percent": 0.75,
            "enemy_anomaly_resistance_attrs": {1: 0.10},
            "char_buff_count": 1,
            "enemy_debuff_count": 1,
            "enemy_dot_count": 0,
        },
        dynamic_attrs={
            "field_anomaly_mastery": 0.25,
            "anomaly_mastery": 20.0,
            "field_anomaly_proficiency": 0.10,
            "anomaly_proficiency": 30.0,
            "field_atk_percentage": 0.50,
            "atk": 20.0,
            "fire_anomaly_buildup_bonus": 0.20,
            "all_anomaly_buildup_bonus": 0.10,
            "ex_special_skill_anomaly_buildup_bonus": 0.15,
            "fire_anomaly_res_decrease": 0.05,
        },
        expected_dynamic_fields={
            "field_anomaly_mastery": 0.25,
            "anomaly_mastery": 20.0,
            "field_anomaly_proficiency": 0.10,
            "anomaly_proficiency": 30.0,
            "field_atk_percentage": 0.50,
            "atk": 20.0,
            "fire_anomaly_buildup_bonus": 0.20,
            "all_anomaly_buildup_bonus": 0.10,
            "ex_special_skill_anomaly_buildup_bonus": 0.15,
            "fire_anomaly_res_decrease": 0.05,
        },
        expectations=(
            _FormulaOracleExpectation(
                label="cal_am",
                expected_value=170.0,
                retained_value=lambda data: Calculator.AnomalyMul.cal_am(data),
                reader_value=lambda reader, context: reader.read_anomaly_mastery(context),
            ),
            _FormulaOracleExpectation(
                label="cal_ap",
                expected_value=415.0,
                retained_value=lambda data: Calculator.AnomalyMul.cal_ap(data),
                reader_value=lambda reader, context: reader.read_anomaly_proficiency(context),
            ),
            _FormulaOracleExpectation(
                label="cal_anomaly_buildup",
                expected_value=62.8575,
                retained_value=lambda data: Calculator.AnomalyMul.cal_anomaly_buildup(data),
            ),
            _FormulaOracleExpectation(
                label="cal_base_damage",
                expected_value=160.0,
                retained_value=lambda data: Calculator.AnomalyMul.cal_base_damage(data),
            ),
        ),
    ),
    _FormulaOracleCase(
        case_id="anomaly-dmg-bonus-ratio-fields",
        fixture_kwargs={
            "name": "异常乘区-增伤字段",
            "static_statement_attrs": {"FIRE_DMG_bonus": 0.12},
            "damage_ratio": 1.0,
            "hit_times": 1,
            "diff_multiplier": 0,
            "element_type": 1,
            "char_buff_count": 1,
            "enemy_debuff_count": 0,
            "enemy_dot_count": 0,
        },
        dynamic_attrs={
            "fire_dmg_bonus": 0.23,
            "all_dmg_bonus": 0.17,
            "anomaly_dmg_bonus": 0.08,
        },
        expected_dynamic_fields={
            "fire_dmg_bonus": 0.23,
            "all_dmg_bonus": 0.17,
            "anomaly_dmg_bonus": 0.08,
        },
        expectations=(
            _FormulaOracleExpectation(
                label="cal_dmg_bonus",
                expected_value=1.60,
                retained_value=lambda data: Calculator.AnomalyMul.cal_dmg_bonus(data),
            ),
        ),
    ),
    _FormulaOracleCase(
        case_id="anomaly-ap-multiplier-conversion",
        fixture_kwargs={
            "name": "异常乘区-AP转换",
            "ap": 320.0,
            "damage_ratio": 1.0,
            "hit_times": 1,
            "diff_multiplier": 0,
            "element_type": 1,
            "char_buff_count": 1,
            "enemy_debuff_count": 0,
            "enemy_dot_count": 0,
        },
        dynamic_attrs={
            "field_anomaly_proficiency": 0.25,
            "anomaly_proficiency": 60.0,
        },
        expected_dynamic_fields={
            "field_anomaly_proficiency": 0.25,
            "anomaly_proficiency": 60.0,
        },
        expectations=(
            _FormulaOracleExpectation(
                label="cal_ap",
                expected_value=460.0,
                retained_value=lambda data: Calculator.AnomalyMul.cal_ap(data),
                reader_value=lambda reader, context: reader.read_anomaly_proficiency(context),
            ),
            _FormulaOracleExpectation(
                label="cal_ap_mul",
                expected_value=4.60,
                retained_value=_anomaly_mul_ap_mul,
            ),
        ),
    ),
    _FormulaOracleCase(
        case_id="anomaly-extra-multiplier-fields",
        fixture_kwargs={
            "name": "异常乘区-额外倍率",
            "damage_ratio": 1.0,
            "hit_times": 1,
            "diff_multiplier": 0,
            "element_type": 3,
            "char_buff_count": 1,
            "enemy_debuff_count": 0,
            "enemy_dot_count": 0,
        },
        dynamic_attrs={
            "shock_dmg_mul": 0.35,
            "all_anomaly_dmg_mul": 0.15,
        },
        expected_dynamic_fields={
            "shock_dmg_mul": 0.35,
            "all_anomaly_dmg_mul": 0.15,
        },
        expectations=(
            _FormulaOracleExpectation(
                label="cal_ano_extra_mul",
                expected_value=1.50,
                retained_value=lambda data: Calculator.AnomalyMul.cal_ano_extra_mul(data),
            ),
        ),
    ),
    _FormulaOracleCase(
        case_id="anomaly-crit-retained-fields",
        fixture_kwargs={
            "name": "异常乘区-暴击保留边界",
            "crit_rate": 0.20,
            "crit_damage": 0.80,
            "damage_ratio": 1.0,
            "hit_times": 1,
            "diff_multiplier": 0,
            "element_type": 0,
            "char_buff_count": 1,
            "enemy_debuff_count": 0,
            "enemy_dot_count": 0,
        },
        dynamic_attrs={
            "strike_crit_rate_increase": 0.25,
            "strike_crit_dmg_increase": 0.40,
        },
        expected_dynamic_fields={
            "strike_crit_rate_increase": 0.25,
            "strike_crit_dmg_increase": 0.40,
        },
        expectations=(
            _FormulaOracleExpectation(
                label="cal_anomaly_crit",
                expected_value=1.0,
                retained_value=_anomaly_mul_crit,
            ),
        ),
    ),
    _FormulaOracleCase(
        case_id="anomaly-res-pen-physical-positive",
        fixture_kwargs={
            "name": "异常乘区-物理抗性穿透正值",
            "damage_ratio": 1.0,
            "hit_times": 1,
            "diff_multiplier": 0,
            "element_type": 0,
            "char_buff_count": 1,
            "enemy_debuff_count": 0,
            "enemy_dot_count": 0,
        },
        dynamic_attrs={
            "physical_res_pen_increase": 0.21,
            "fire_res_pen_increase": 0.99,
        },
        expected_dynamic_fields={
            "physical_res_pen_increase": 0.21,
            "fire_res_pen_increase": 0.99,
        },
        expectations=(
            _FormulaOracleExpectation(
                label="cal_res_pen",
                expected_value=0.21,
                retained_value=_anomaly_mul_res_pen,
            ),
        ),
    ),
    _FormulaOracleCase(
        case_id="anomaly-res-pen-fire-positive",
        fixture_kwargs={
            "name": "异常乘区-火抗性穿透正值",
            "damage_ratio": 1.0,
            "hit_times": 1,
            "diff_multiplier": 0,
            "element_type": 1,
            "char_buff_count": 1,
            "enemy_debuff_count": 0,
            "enemy_dot_count": 0,
        },
        dynamic_attrs={
            "fire_res_pen_increase": 0.18,
        },
        expected_dynamic_fields={
            "fire_res_pen_increase": 0.18,
        },
        expectations=(
            _FormulaOracleExpectation(
                label="cal_res_pen",
                expected_value=0.18,
                retained_value=_anomaly_mul_res_pen,
            ),
        ),
    ),
    _FormulaOracleCase(
        case_id="anomaly-res-pen-ice-positive",
        fixture_kwargs={
            "name": "异常乘区-冰抗性穿透正值",
            "damage_ratio": 1.0,
            "hit_times": 1,
            "diff_multiplier": 0,
            "element_type": 2,
            "char_buff_count": 1,
            "enemy_debuff_count": 0,
            "enemy_dot_count": 0,
        },
        dynamic_attrs={
            "physical_res_pen_increase": 0.77,
            "ice_res_pen_increase": 0.22,
        },
        expected_dynamic_fields={
            "physical_res_pen_increase": 0.77,
            "ice_res_pen_increase": 0.22,
        },
        expectations=(
            _FormulaOracleExpectation(
                label="cal_res_pen",
                expected_value=0.22,
                retained_value=_anomaly_mul_res_pen,
            ),
        ),
    ),
    _FormulaOracleCase(
        case_id="anomaly-res-pen-electric-positive",
        fixture_kwargs={
            "name": "异常乘区-电抗性穿透正值",
            "damage_ratio": 1.0,
            "hit_times": 1,
            "diff_multiplier": 0,
            "element_type": 3,
            "char_buff_count": 1,
            "enemy_debuff_count": 0,
            "enemy_dot_count": 0,
        },
        dynamic_attrs={
            "electric_res_pen_increase": 0.24,
            "ether_res_pen_increase": 0.88,
        },
        expected_dynamic_fields={
            "electric_res_pen_increase": 0.24,
            "ether_res_pen_increase": 0.88,
        },
        expectations=(
            _FormulaOracleExpectation(
                label="cal_res_pen",
                expected_value=0.24,
                retained_value=_anomaly_mul_res_pen,
            ),
        ),
    ),
    _FormulaOracleCase(
        case_id="anomaly-res-pen-ether-positive",
        fixture_kwargs={
            "name": "异常乘区-以太抗性穿透正值",
            "damage_ratio": 1.0,
            "hit_times": 1,
            "diff_multiplier": 0,
            "element_type": 4,
            "char_buff_count": 1,
            "enemy_debuff_count": 0,
            "enemy_dot_count": 0,
        },
        dynamic_attrs={
            "ice_res_pen_increase": 0.11,
            "ether_res_pen_increase": 0.25,
        },
        expected_dynamic_fields={
            "ice_res_pen_increase": 0.11,
            "ether_res_pen_increase": 0.25,
        },
        expectations=(
            _FormulaOracleExpectation(
                label="cal_res_pen",
                expected_value=0.25,
                retained_value=_anomaly_mul_res_pen,
            ),
        ),
    ),
    _FormulaOracleCase(
        case_id="anomaly-res-pen-auric-ink-uses-ether-field",
        fixture_kwargs={
            "name": "异常乘区-玄墨属性读取以太抗穿",
            "damage_ratio": 1.0,
            "hit_times": 1,
            "diff_multiplier": 0,
            "element_type": 6,
            "char_buff_count": 1,
            "enemy_debuff_count": 0,
            "enemy_dot_count": 0,
        },
        dynamic_attrs={
            "fire_res_pen_increase": 0.12,
            "ether_res_pen_increase": 0.26,
            "all_res_pen_increase": 0.61,
        },
        expected_dynamic_fields={
            "fire_res_pen_increase": 0.12,
            "ether_res_pen_increase": 0.26,
            "all_res_pen_increase": 0.61,
        },
        expectations=(
            _FormulaOracleExpectation(
                label="cal_res_pen",
                expected_value=0.26,
                retained_value=_anomaly_mul_res_pen,
            ),
        ),
    ),
    _FormulaOracleCase(
        case_id="anomaly-res-pen-default-zero",
        fixture_kwargs={
            "name": "异常乘区-抗性穿透默认零值",
            "damage_ratio": 1.0,
            "hit_times": 1,
            "diff_multiplier": 0,
            "element_type": 3,
            "char_buff_count": 0,
            "enemy_debuff_count": 0,
            "enemy_dot_count": 0,
        },
        dynamic_attrs={},
        expected_dynamic_fields={
            "electric_res_pen_increase": 0.0,
        },
        expectations=(
            _FormulaOracleExpectation(
                label="cal_res_pen",
                expected_value=0.0,
                retained_value=_anomaly_mul_res_pen,
            ),
        ),
    ),
    _FormulaOracleCase(
        case_id="anomaly-res-pen-frost-uses-ice-field",
        fixture_kwargs={
            "name": "异常乘区-霜属性读取冰抗穿",
            "damage_ratio": 1.0,
            "hit_times": 1,
            "diff_multiplier": 0,
            "element_type": 5,
            "char_buff_count": 1,
            "enemy_debuff_count": 1,
            "enemy_dot_count": 0,
        },
        dynamic_attrs={
            "fire_res_pen_increase": 0.44,
            "ice_res_pen_increase": 0.33,
            "ether_res_pen_increase": 0.55,
            "all_res_pen_increase": 0.66,
        },
        expected_dynamic_fields={
            "fire_res_pen_increase": 0.44,
            "ice_res_pen_increase": 0.33,
            "ether_res_pen_increase": 0.55,
            "all_res_pen_increase": 0.66,
        },
        expectations=(
            _FormulaOracleExpectation(
                label="cal_res_pen",
                expected_value=0.33,
                retained_value=_anomaly_mul_res_pen,
            ),
            _FormulaOracleExpectation(
                label="cal_res_mul",
                expected_value=1.99,
                retained_value=lambda data: Calculator.RegularMul.cal_res_mul(data),
            ),
        ),
    ),
    _FormulaOracleCase(
        case_id="stun-impact-reader-parity",
        fixture_kwargs={
            "name": "失衡乘区-冲击 reader",
            "imp": 80.0,
            "damage_ratio": 1.0,
            "hit_times": 1,
            "diff_multiplier": 0,
            "char_buff_count": 1,
            "enemy_debuff_count": 1,
            "enemy_dot_count": 0,
        },
        dynamic_attrs={
            "field_imp_percentage": 0.25,
            "imp": 5.0,
        },
        expected_dynamic_fields={
            "field_imp_percentage": 0.25,
            "imp": 5.0,
        },
        expectations=(
            _FormulaOracleExpectation(
                label="cal_imp",
                expected_value=105.0,
                retained_value=lambda data: Calculator.StunMul.cal_imp(data),
                reader_value=lambda reader, context: reader.read_impact(context),
            ),
        ),
    ),
    _FormulaOracleCase(
        case_id="stun-ratio-res-bonus-received-retained",
        fixture_kwargs={
            "name": "失衡乘区-倍率抗性增幅受击",
            "damage_ratio": 1.0,
            "stun_ratio": 240.0,
            "hit_times": 4,
            "diff_multiplier": 0,
            "element_type": 3,
            "trigger_buff_level": 2,
            "skill_labels": {"aftershock_attack": 1},
            "enemy_stun_resistance_attrs": {3: 0.20},
            "char_buff_count": 1,
            "enemy_debuff_count": 1,
            "enemy_dot_count": 0,
        },
        dynamic_attrs={
            "stun_res": 0.15,
            "ex_special_skill_stun_bonus": 0.25,
            "stun_bonus": 0.10,
            "aftershock_attack_stun_bonus": 0.05,
            "received_stun_increase": 0.30,
        },
        expected_dynamic_fields={
            "stun_res": 0.15,
            "ex_special_skill_stun_bonus": 0.25,
            "stun_bonus": 0.10,
            "aftershock_attack_stun_bonus": 0.05,
            "received_stun_increase": 0.30,
        },
        expectations=(
            _FormulaOracleExpectation(
                label="cal_stun_ratio",
                expected_value=60.0,
                retained_value=lambda data: Calculator.StunMul.cal_stun_ratio(data),
            ),
            _FormulaOracleExpectation(
                label="cal_stun_res",
                expected_value=0.65,
                retained_value=lambda data: Calculator.StunMul.cal_stun_res(
                    data,
                    cast(SkillNode, data.judge_node).element_type,
                ),
            ),
            _FormulaOracleExpectation(
                label="cal_stun_bonus",
                expected_value=1.40,
                retained_value=lambda data: Calculator.StunMul.cal_stun_bonus(data),
            ),
            _FormulaOracleExpectation(
                label="cal_stun_received",
                expected_value=1.30,
                retained_value=lambda data: Calculator.StunMul.cal_stun_received(data),
            ),
        ),
    ),
    _FormulaOracleCase(
        case_id="active-debuff-dot-reader-parity",
        fixture_kwargs={
            "name": "公式表用例-动态列表",
            "am": 100.0,
            "ap": 300.0,
            "imp": 80.0,
            "crit_rate": 0.2,
            "crit_damage": 0.8,
            "char_buff_count": 2,
            "enemy_debuff_count": 2,
            "enemy_dot_count": 1,
        },
        dynamic_attrs={
            "field_anomaly_mastery": 0.2,
            "anomaly_mastery": 10.0,
            "field_anomaly_proficiency": 0.1,
            "anomaly_proficiency": 15.0,
            "field_imp_percentage": 0.25,
            "imp": 5.0,
            "field_crit_rate": 0.05,
            "crit_rate": 0.1,
            "crit_rate_received_increase": 0.25,
            "field_crit_dmg": 0.25,
            "crit_dmg": 0.2,
        },
        expected_dynamic_fields={
            "field_anomaly_mastery": 0.2,
            "anomaly_mastery": 10.0,
            "field_anomaly_proficiency": 0.1,
            "anomaly_proficiency": 15.0,
            "field_imp_percentage": 0.25,
            "imp": 5.0,
            "field_crit_rate": 0.05,
            "crit_rate": 0.1,
            "crit_rate_received_increase": 0.25,
            "field_crit_dmg": 0.25,
            "crit_dmg": 0.2,
        },
        expectations=(
            _FormulaOracleExpectation(
                label="cal_am",
                expected_value=130.0,
                retained_value=lambda data: Calculator.AnomalyMul.cal_am(data),
                reader_value=lambda reader, context: reader.read_anomaly_mastery(context),
            ),
            _FormulaOracleExpectation(
                label="cal_ap",
                expected_value=345.0,
                retained_value=lambda data: Calculator.AnomalyMul.cal_ap(data),
                reader_value=lambda reader, context: reader.read_anomaly_proficiency(context),
            ),
            _FormulaOracleExpectation(
                label="cal_imp",
                expected_value=105.0,
                retained_value=lambda data: Calculator.StunMul.cal_imp(data),
                reader_value=lambda reader, context: reader.read_impact(context),
            ),
            _FormulaOracleExpectation(
                label="cal_crit_rate",
                expected_value=0.6,
                retained_value=lambda data: Calculator.RegularMul.cal_crit_rate(data),
                reader_value=lambda reader, context: reader.read_full_crit_rate(context),
            ),
            _FormulaOracleExpectation(
                label="cal_personal_crit_dmg",
                expected_value=1.25,
                retained_value=lambda data: Calculator.RegularMul.cal_personal_crit_dmg(data),
                reader_value=lambda reader, context: reader.read_personal_crit_damage(context),
            ),
        ),
    ),
    _FormulaOracleCase(
        case_id="empty-dynamic-defaults",
        fixture_kwargs={
            "name": "公式表用例-默认值",
            "am": 90.0,
            "ap": 310.0,
            "imp": 70.0,
            "crit_rate": 0.15,
            "crit_damage": 0.6,
            "char_buff_count": 0,
            "enemy_debuff_count": 0,
            "enemy_dot_count": 0,
        },
        dynamic_attrs={},
        expected_dynamic_fields={
            "field_anomaly_mastery": 0.0,
            "anomaly_mastery": 0.0,
            "field_anomaly_proficiency": 0.0,
            "anomaly_proficiency": 0.0,
            "field_imp_percentage": 0.0,
            "imp": 0.0,
        },
        expectations=(
            _FormulaOracleExpectation(
                label="cal_am",
                expected_value=90.0,
                retained_value=lambda data: Calculator.AnomalyMul.cal_am(data),
                reader_value=lambda reader, context: reader.read_anomaly_mastery(context),
            ),
            _FormulaOracleExpectation(
                label="cal_ap",
                expected_value=310.0,
                retained_value=lambda data: Calculator.AnomalyMul.cal_ap(data),
                reader_value=lambda reader, context: reader.read_anomaly_proficiency(context),
            ),
            _FormulaOracleExpectation(
                label="cal_imp",
                expected_value=70.0,
                retained_value=lambda data: Calculator.StunMul.cal_imp(data),
                reader_value=lambda reader, context: reader.read_impact(context),
            ),
        ),
    ),
)


_AM_RETAINED_MULTIPLIER_ORACLE_CASES = (
    _AnomalyMasteryRetainedOracleCase(
        case_id="am-default-zero",
        fixture_kwargs={
            "name": "异常掌控-默认零值",
            "char_buff_count": 0,
            "enemy_debuff_count": 0,
            "enemy_dot_count": 0,
        },
        dynamic_attrs={},
        expected_dynamic_fields={
            "field_anomaly_mastery": 0.0,
            "anomaly_mastery": 0.0,
        },
        expected_value=0.0,
    ),
    _AnomalyMasteryRetainedOracleCase(
        case_id="am-base-only",
        fixture_kwargs={
            "name": "异常掌控-基础值",
            "am": 95.0,
            "char_buff_count": 0,
            "enemy_debuff_count": 0,
            "enemy_dot_count": 0,
        },
        dynamic_attrs={},
        expected_dynamic_fields={
            "field_anomaly_mastery": 0.0,
            "anomaly_mastery": 0.0,
        },
        expected_value=95.0,
    ),
    _AnomalyMasteryRetainedOracleCase(
        case_id="am-static-fixed-increase",
        fixture_kwargs={
            "name": "异常掌控-静态固定值",
            "am": 95.0,
            "static_statement_attrs": {"AM": 118.0},
            "char_buff_count": 0,
            "enemy_debuff_count": 0,
            "enemy_dot_count": 0,
        },
        dynamic_attrs={},
        expected_dynamic_fields={
            "field_anomaly_mastery": 0.0,
            "anomaly_mastery": 0.0,
        },
        expected_value=118.0,
    ),
    _AnomalyMasteryRetainedOracleCase(
        case_id="am-dynamic-flat-increase",
        fixture_kwargs={
            "name": "异常掌控-局内固定值",
            "am": 80.0,
            "char_buff_count": 1,
            "enemy_debuff_count": 1,
            "enemy_dot_count": 0,
        },
        dynamic_attrs={
            "anomaly_mastery": 22.0,
        },
        expected_dynamic_fields={
            "field_anomaly_mastery": 0.0,
            "anomaly_mastery": 22.0,
        },
        expected_value=102.0,
    ),
    _AnomalyMasteryRetainedOracleCase(
        case_id="am-mixed-flat-percentage",
        fixture_kwargs={
            "name": "异常掌控-固定百分比混合",
            "am": 80.0,
            "char_buff_count": 2,
            "enemy_debuff_count": 1,
            "enemy_dot_count": 0,
        },
        dynamic_attrs={
            "field_anomaly_mastery": 0.25,
            "anomaly_mastery": 15.0,
        },
        expected_dynamic_fields={
            "field_anomaly_mastery": 0.25,
            "anomaly_mastery": 15.0,
        },
        expected_value=115.0,
    ),
)


_AP_RETAINED_MULTIPLIER_ORACLE_CASES = (
    _AnomalyProficiencyRetainedOracleCase(
        case_id="ap-default-zero",
        fixture_kwargs={
            "name": "异常精通-默认零值",
            "char_buff_count": 0,
            "enemy_debuff_count": 0,
            "enemy_dot_count": 0,
        },
        dynamic_attrs={},
        expected_dynamic_fields={
            "field_anomaly_proficiency": 0.0,
            "anomaly_proficiency": 0.0,
        },
        expected_value=0.0,
    ),
    _AnomalyProficiencyRetainedOracleCase(
        case_id="ap-base-only",
        fixture_kwargs={
            "name": "异常精通-基础值",
            "ap": 300.0,
            "char_buff_count": 0,
            "enemy_debuff_count": 0,
            "enemy_dot_count": 0,
        },
        dynamic_attrs={},
        expected_dynamic_fields={
            "field_anomaly_proficiency": 0.0,
            "anomaly_proficiency": 0.0,
        },
        expected_value=300.0,
    ),
    _AnomalyProficiencyRetainedOracleCase(
        case_id="ap-static-fixed-increase",
        fixture_kwargs={
            "name": "异常精通-静态固定值",
            "ap": 300.0,
            "static_statement_attrs": {"AP": 360.0},
            "char_buff_count": 0,
            "enemy_debuff_count": 0,
            "enemy_dot_count": 0,
        },
        dynamic_attrs={},
        expected_dynamic_fields={
            "field_anomaly_proficiency": 0.0,
            "anomaly_proficiency": 0.0,
        },
        expected_value=360.0,
    ),
    _AnomalyProficiencyRetainedOracleCase(
        case_id="ap-dynamic-flat-increase",
        fixture_kwargs={
            "name": "异常精通-局内固定值",
            "ap": 300.0,
            "char_buff_count": 1,
            "enemy_debuff_count": 1,
            "enemy_dot_count": 0,
        },
        dynamic_attrs={
            "anomaly_proficiency": 45.0,
        },
        expected_dynamic_fields={
            "field_anomaly_proficiency": 0.0,
            "anomaly_proficiency": 45.0,
        },
        expected_value=345.0,
    ),
    _AnomalyProficiencyRetainedOracleCase(
        case_id="ap-mixed-flat-percentage",
        fixture_kwargs={
            "name": "异常精通-固定百分比混合",
            "ap": 300.0,
            "char_buff_count": 2,
            "enemy_debuff_count": 1,
            "enemy_dot_count": 0,
        },
        dynamic_attrs={
            "field_anomaly_proficiency": 0.25,
            "anomaly_proficiency": 60.0,
        },
        expected_dynamic_fields={
            "field_anomaly_proficiency": 0.25,
            "anomaly_proficiency": 60.0,
        },
        expected_value=435.0,
    ),
)


_IMP_RETAINED_MULTIPLIER_ORACLE_CASES = (
    _ImpactRetainedOracleCase(
        case_id="imp-default-zero",
        fixture_kwargs={
            "name": "冲击力-默认零值",
            "char_buff_count": 0,
            "enemy_debuff_count": 0,
            "enemy_dot_count": 0,
        },
        dynamic_attrs={},
        expected_dynamic_fields={
            "field_imp_percentage": 0.0,
            "imp": 0.0,
        },
        expected_value=0.0,
    ),
    _ImpactRetainedOracleCase(
        case_id="imp-base-only",
        fixture_kwargs={
            "name": "冲击力-基础值",
            "imp": 100.0,
            "char_buff_count": 0,
            "enemy_debuff_count": 0,
            "enemy_dot_count": 0,
        },
        dynamic_attrs={},
        expected_dynamic_fields={
            "field_imp_percentage": 0.0,
            "imp": 0.0,
        },
        expected_value=100.0,
    ),
    _ImpactRetainedOracleCase(
        case_id="imp-static-fixed-increase",
        fixture_kwargs={
            "name": "冲击力-静态固定值",
            "imp": 100.0,
            "static_statement_attrs": {"IMP": 118.0},
            "char_buff_count": 0,
            "enemy_debuff_count": 0,
            "enemy_dot_count": 0,
        },
        dynamic_attrs={},
        expected_dynamic_fields={
            "field_imp_percentage": 0.0,
            "imp": 0.0,
        },
        expected_value=118.0,
    ),
    _ImpactRetainedOracleCase(
        case_id="imp-dynamic-percentage-increase",
        fixture_kwargs={
            "name": "冲击力-局内百分比",
            "imp": 90.0,
            "char_buff_count": 1,
            "enemy_debuff_count": 1,
            "enemy_dot_count": 0,
        },
        dynamic_attrs={
            "field_imp_percentage": 0.20,
        },
        expected_dynamic_fields={
            "field_imp_percentage": 0.20,
            "imp": 0.0,
        },
        expected_value=108.0,
    ),
    _ImpactRetainedOracleCase(
        case_id="imp-mixed-flat-percentage",
        fixture_kwargs={
            "name": "冲击力-固定百分比混合",
            "imp": 80.0,
            "char_buff_count": 2,
            "enemy_debuff_count": 1,
            "enemy_dot_count": 0,
        },
        dynamic_attrs={
            "field_imp_percentage": 0.25,
            "imp": 5.0,
        },
        expected_dynamic_fields={
            "field_imp_percentage": 0.25,
            "imp": 5.0,
        },
        expected_value=105.0,
    ),
)


_ANOMALY_SNAPSHOT_ORACLE_CASES = (
    _AnomalySnapshotOracleCase(
        case_id="new-anomaly-copy-source-snapshot",
        snapshot_values=(
            210.0,
            1.20,
            3.0,
            60.0,
            1.50,
            999.0,
            0.15,
            5.0,
            0.20,
            1.30,
            1.70,
        ),
    ),
)


_ANOMALY_MUL_SNAPSHOT_ORACLE_CASES = (
    _AnomalyMulSnapshotOracleCase(
        case_id="physical-default-no-bonus-vector",
        character_name="异常快照默认角色",
        character_kwargs={
            "atk": 100.0,
            "ap": 200.0,
        },
        skill_kwargs={
            "damage_ratio": 1.0,
            "hit_times": 1,
            "diff_multiplier": 0,
            "element_type": 0,
            "anomaly_accumulation": 0.0,
        },
        dynamic_attrs={},
        expected_snapshot=(
            713.0,
            1.0,
            2.0,
            60.0,
            1.0,
            1.0,
            0.0,
            0.0,
            0.0,
        ),
    ),
    _AnomalyMulSnapshotOracleCase(
        case_id="electric-dynamic-field-vector",
        character_name="异常快照动态角色",
        character_kwargs={
            "atk": 120.0,
            "ap": 250.0,
            "static_statement_attrs": {
                "PEN_ratio": 0.05,
                "PEN_numeric": 8.0,
                "ELECTRIC_DMG_bonus": 0.12,
            },
        },
        skill_kwargs={
            "damage_ratio": 1.0,
            "hit_times": 1,
            "diff_multiplier": 0,
            "element_type": 3,
            "anomaly_accumulation": 0.0,
        },
        dynamic_attrs={
            "field_atk_percentage": 0.10,
            "atk": 30.0,
            "electric_dmg_bonus": 0.08,
            "all_dmg_bonus": 0.05,
            "anomaly_dmg_bonus": 0.04,
            "field_anomaly_proficiency": 0.20,
            "anomaly_proficiency": 25.0,
            "shock_dmg_mul": 0.16,
            "all_anomaly_dmg_mul": 0.07,
            "pen_ratio": 0.04,
            "pen_numeric": 6.0,
            "electric_res_pen_increase": 0.11,
        },
        expected_snapshot=(
            202.5,
            1.29,
            3.25,
            60.0,
            1.23,
            1.0,
            0.09,
            14.0,
            0.11,
        ),
    ),
)


_CAL_ANOMALY_LEVEL_CLAMP_ORACLE_CASES = (
    _CalAnomalyLevelClampOracleCase(
        case_id="below-boundary-clamps-to-zero",
        input_level=-1,
        expected_value=0.0,
        expected_log_messages=("角色等级-1过低，将被设置为0",),
    ),
    _CalAnomalyLevelClampOracleCase(
        case_id="normal-level-uses-retained-table",
        input_level=40,
        expected_value=1.6610,
    ),
    _CalAnomalyLevelClampOracleCase(
        case_id="above-boundary-clamps-to-sixty",
        input_level=61,
        expected_value=2.0,
        expected_log_messages=("角色等级61过高，将被设置为60",),
    ),
)


_COPIED_OUTPUT_PAYLOAD_CASES = (
    _CopiedOutputPayloadCase(
        case_id="new-anomaly-payload-fields",
        snapshot_case=_AnomalySnapshotOracleCase(
            case_id="new-anomaly-source-snapshot",
            snapshot_values=(
                266.0,
                1.45,
                5.0,
                80.0,
                1.90,
                0.25,
                0.18,
                12.0,
                0.27,
                1.52,
                1.86,
            ),
            scaling_factor=1.40,
        ),
        copied_kind="new_anomaly",
        runtime_tick=410,
        payload_fields={
            "element_type": 4,
            "accompany_dot": "Corruption",
            "anomaly_dmg_ratio": 2.15,
            "max_duration": 540,
            "last_active": 250,
            "rename_tag": "new-anomaly-payload",
        },
    ),
    _CopiedOutputPayloadCase(
        case_id="disorder-payload-fields",
        snapshot_case=_AnomalySnapshotOracleCase(
            case_id="disorder-source-snapshot",
            snapshot_values=(
                188.0,
                1.35,
                4.0,
                72.0,
                1.80,
                777.0,
                0.22,
                9.0,
                0.33,
                1.44,
                1.66,
            ),
            scaling_factor=1.75,
        ),
        copied_kind="disorder",
        runtime_tick=300,
        payload_fields={
            "element_type": 3,
            "accompany_dot": "Shock",
            "anomaly_dmg_ratio": 2.4,
            "max_duration": 480,
            "last_active": 120,
            "rename_tag": "copied-disorder-source",
        },
    ),
    _CopiedOutputPayloadCase(
        case_id="polarity-disorder-payload-fields",
        snapshot_case=_AnomalySnapshotOracleCase(
            case_id="polarity-disorder-source-snapshot",
            snapshot_values=(
                188.0,
                1.35,
                4.0,
                72.0,
                1.80,
                777.0,
                0.22,
                9.0,
                0.33,
                1.44,
                1.66,
            ),
            scaling_factor=1.75,
        ),
        copied_kind="polarity_disorder",
        runtime_tick=300,
        payload_fields={
            "element_type": 3,
            "accompany_dot": "Shock",
            "anomaly_dmg_ratio": 2.4,
            "max_duration": 480,
            "last_active": 120,
            "rename_tag": "copied-disorder-source",
        },
        polarity_ratio=0.65,
    ),
)


_CAL_ANOMALY_MULTIPLIER_ORACLE_CASES = (
    _CalAnomalyMultiplierOracleCase(
        case_id="physical-active-crit-defense-res-vulnerability-stack",
        element_type=0,
        snapshot_values=(
            120.0,
            1.15,
            2.25,
            60.0,
            1.35,
            999.0,
            0.07,
            12.0,
            0.09,
            1.20,
            1.40,
        ),
        enemy_max_def=600.0,
        enemy_damage_resistance_attrs={"PHY_damage_resistance": 0.22},
        enemy_stunned=True,
        enemy_stun_ratio=0.45,
        dynamic_attrs={
            "strike_crit_rate_increase": 0.30,
            "strike_crit_dmg_increase": 0.50,
            "strike_ignore_defense": 0.04,
            "percentage_def_reduction": 0.20,
            "def_reduction": 40.0,
            "pen_ratio": 0.10,
            "pen_numeric": 25.0,
            "physical_dmg_res_decrease": 0.08,
            "physical_res_pen_increase": 0.03,
            "all_dmg_res_decrease": 0.06,
            "all_res_pen_increase": 0.02,
            "physical_vulnerability": 0.14,
            "all_vulnerability": 0.11,
            "stun_vulnerability_increase": 0.20,
            "stun_vulnerability_increase_all_time": 0.05,
            "special_multiplier_zone": 0.07,
        },
        expected_dynamic_fields={
            "strike_crit_rate_increase": 0.30,
            "strike_crit_dmg_increase": 0.50,
            "strike_ignore_defense": 0.04,
            "percentage_def_reduction": 0.20,
            "def_reduction": 40.0,
            "pen_ratio": 0.10,
            "pen_numeric": 25.0,
            "physical_dmg_res_decrease": 0.08,
            "physical_res_pen_increase": 0.03,
            "all_dmg_res_decrease": 0.06,
            "all_res_pen_increase": 0.02,
            "physical_vulnerability": 0.14,
            "all_vulnerability": 0.11,
            "stun_vulnerability_increase": 0.20,
            "stun_vulnerability_increase_all_time": 0.05,
            "special_multiplier_zone": 0.07,
        },
        expected_snapshot_fields={
            "virtual_character_level": 60.0,
            "snapshot_pen_ratio": 0.07,
            "snapshot_pen_numeric": 12.0,
            "snapshot_res_pen": 0.09,
            "snapshot_impact": 1.20,
            "snapshot_stun_bonus": 1.40,
        },
        expected_final_multipliers=(
            120.0,
            1.15,
            2.25,
            2.0,
            1.35,
            1.15,
            0.7188122397247874,
            1.06,
            1.25,
            1.20,
            1.40,
            1.70,
            1.07,
        ),
        scaling_factor=1.75,
    ),
    _CalAnomalyMultiplierOracleCase(
        case_id="fire-res-vulnerability-keeps-active-crit-neutral",
        element_type=1,
        snapshot_values=(
            90.0,
            1.05,
            1.75,
            40.0,
            1.20,
            999.0,
            0.03,
            5.0,
            0.04,
            1.10,
            1.30,
        ),
        enemy_max_def=500.0,
        enemy_damage_resistance_attrs={"FIRE_damage_resistance": 0.18},
        enemy_stunned=False,
        enemy_stun_ratio=0.0,
        dynamic_attrs={
            "strike_crit_rate_increase": 0.80,
            "strike_crit_dmg_increase": 2.00,
            "strike_ignore_defense": 0.50,
            "percentage_def_reduction": 0.10,
            "def_reduction": 25.0,
            "pen_ratio": 0.05,
            "pen_numeric": 15.0,
            "fire_dmg_res_decrease": 0.07,
            "fire_res_pen_increase": 0.02,
            "all_dmg_res_decrease": 0.03,
            "all_res_pen_increase": 0.01,
            "fire_vulnerability": 0.09,
            "all_vulnerability": 0.06,
            "stun_vulnerability_increase": 0.90,
            "stun_vulnerability_increase_all_time": 0.04,
        },
        expected_dynamic_fields={
            "strike_crit_rate_increase": 0.80,
            "strike_crit_dmg_increase": 2.00,
            "strike_ignore_defense": 0.50,
            "percentage_def_reduction": 0.10,
            "def_reduction": 25.0,
            "pen_ratio": 0.05,
            "pen_numeric": 15.0,
            "fire_dmg_res_decrease": 0.07,
            "fire_res_pen_increase": 0.02,
            "all_dmg_res_decrease": 0.03,
            "all_res_pen_increase": 0.01,
            "fire_vulnerability": 0.09,
            "all_vulnerability": 0.06,
            "stun_vulnerability_increase": 0.90,
            "stun_vulnerability_increase_all_time": 0.04,
            "special_multiplier_zone": 0.0,
        },
        expected_snapshot_fields={
            "virtual_character_level": 40.0,
            "snapshot_pen_ratio": 0.03,
            "snapshot_pen_numeric": 5.0,
            "snapshot_res_pen": 0.04,
            "snapshot_impact": 1.10,
            "snapshot_stun_bonus": 1.30,
        },
        expected_final_multipliers=(
            90.0,
            1.05,
            1.75,
            1.661,
            1.20,
            1.0,
            0.5315656565656566,
            0.99,
            1.15,
            1.10,
            1.30,
            1.04,
            1.0,
        ),
        scaling_factor=0.60,
    ),
)


_ABLOOM_FIXTURE_BLOCKER_FIELDS = (
    "schedule_priority",
    "rename_tag",
    "accompany_dot",
)


def _make_cal_abloom_oracle_case(
    *,
    case_id: str,
    base_case: _CalAnomalyMultiplierOracleCase,
    anomaly_dmg_ratio: float,
) -> _CalAbloomOracleCase:
    expected_final_multipliers = (
        base_case.expected_final_multipliers[0] * anomaly_dmg_ratio,
        *base_case.expected_final_multipliers[1:],
    )
    expected_damage = (
        float(np.prod(expected_final_multipliers))
        / (expected_final_multipliers[9] * expected_final_multipliers[10])
        * base_case.scaling_factor
    )
    return _CalAbloomOracleCase(
        case_id=case_id,
        base_case=base_case,
        anomaly_dmg_ratio=anomaly_dmg_ratio,
        copied_payload_sentinel_fields={
            "schedule_priority": 321,
            "rename_tag": f"{case_id}-copied-output-only",
            "accompany_dot": "abloom-fixture-blocker",
        },
        fixture_blocker_fields=_ABLOOM_FIXTURE_BLOCKER_FIELDS,
        expected_deterministic_fields={
            "source_base_snapshot": base_case.snapshot_values[0],
            "anomaly_dmg_ratio": anomaly_dmg_ratio,
            "abloom_base_multiplier": expected_final_multipliers[0],
            "scaling_factor": base_case.scaling_factor,
            "snapshot_impact": base_case.snapshot_values[9],
            "snapshot_stun_bonus": base_case.snapshot_values[10],
            "cal_anomaly_dmg": expected_damage,
        },
        expected_final_multipliers=expected_final_multipliers,
    )


_CAL_ABLOOM_ORACLE_CASES = (
    _make_cal_abloom_oracle_case(
        case_id="physical-abloom-ratio-keeps-inherited-active-crit-inputs",
        base_case=_CAL_ANOMALY_MULTIPLIER_ORACLE_CASES[0],
        anomaly_dmg_ratio=1.30,
    ),
    _make_cal_abloom_oracle_case(
        case_id="fire-abloom-ratio-keeps-non-physical-active-crit-neutral",
        base_case=_CAL_ANOMALY_MULTIPLIER_ORACLE_CASES[1],
        anomaly_dmg_ratio=0.75,
    ),
)


_CAL_DISORDER_COMMON_DYNAMIC_ATTRS = {
    "all_disorder_basic_mul": 0.10,
    "disorder_dmg_mul": 0.45,
    "stun_res": 0.12,
    "received_stun_increase": 0.16,
}

_CAL_DISORDER_COMMON_PAYLOAD_FIELDS: dict[str, Any] = {
    "schedule_priority": 123,
    "rename_tag": "listener-payload-sentinel",
    "accompany_dot": "copied-output-only",
    "anomaly_dmg_ratio": 99.0,
}


def _cal_disorder_snapshot(base_mul: float) -> tuple[float, ...]:
    return (
        base_mul,
        1.11,
        2.20,
        60.0,
        9.99,
        777.0,
        0.0,
        0.0,
        0.0,
        1.25,
        1.35,
    )


def _make_cal_disorder_oracle_case(
    *,
    case_id: str,
    element_type: int,
    base_mul: float,
    element_disorder_basic_attr: str,
    expected_base_dmg: float,
) -> _CalDisorderOracleCase:
    dynamic_attrs = {
        **_CAL_DISORDER_COMMON_DYNAMIC_ATTRS,
        element_disorder_basic_attr: 0.20,
    }
    return _CalDisorderOracleCase(
        case_id=case_id,
        element_type=element_type,
        snapshot_values=_cal_disorder_snapshot(base_mul),
        dynamic_attrs=dynamic_attrs,
        expected_dynamic_fields=dynamic_attrs,
        runtime_tick=300,
        max_duration=500,
        last_active=115,
        expected_remaining_tick=315,
        enemy_stun_resistance=0.18,
        payload_fields=dict(_CAL_DISORDER_COMMON_PAYLOAD_FIELDS),
        expected_final_multipliers=(
            expected_base_dmg,
            1.11,
            2.20,
            2.0,
            1.45,
            1.0,
            1.0,
            1.0,
            1.0,
            1.25,
            1.35,
            1.0,
            1.0,
        ),
        expected_disorder_stun=3.973725,
    )


_CAL_DISORDER_ORACLE_CASES = (
    _make_cal_disorder_oracle_case(
        case_id="physical-strike-floor-seconds",
        element_type=0,
        base_mul=713.0,
        element_disorder_basic_attr="strike_disorder_basic_mul",
        expected_base_dmg=517.5,
    ),
    _make_cal_disorder_oracle_case(
        case_id="fire-burn-half-second-floor",
        element_type=1,
        base_mul=50.0,
        element_disorder_basic_attr="burn_disorder_basic_mul",
        expected_base_dmg=980.0,
    ),
    _make_cal_disorder_oracle_case(
        case_id="ice-frostbite-floor-seconds",
        element_type=2,
        base_mul=500.0,
        element_disorder_basic_attr="frostbite_disorder_basic_mul",
        expected_base_dmg=517.5,
    ),
    _make_cal_disorder_oracle_case(
        case_id="electric-shock-floor-seconds",
        element_type=3,
        base_mul=125.0,
        element_disorder_basic_attr="shock_disorder_basic_mul",
        expected_base_dmg=1105.0,
    ),
    _make_cal_disorder_oracle_case(
        case_id="ether-chaos-half-second-floor",
        element_type=4,
        base_mul=62.5,
        element_disorder_basic_attr="chaos_disorder_basic_mul",
        expected_base_dmg=1105.0,
    ),
    _make_cal_disorder_oracle_case(
        case_id="auric-ink-frostbite-floor-seconds",
        element_type=5,
        base_mul=500.0,
        element_disorder_basic_attr="frostbite_disorder_basic_mul",
        expected_base_dmg=1005.0,
    ),
    _make_cal_disorder_oracle_case(
        case_id="auric-ether-chaos-half-second-floor",
        element_type=6,
        base_mul=62.5,
        element_disorder_basic_attr="chaos_disorder_basic_mul",
        expected_base_dmg=1105.0,
    ),
)


def _make_cal_polarity_disorder_oracle_case(
    *,
    case_id: str,
    element_type: int,
    base_mul: float,
    element_disorder_basic_attr: str,
    expected_base_dmg: float,
    polarity_disorder_ratio: float,
    additional_dmg_ap_ratio: float,
    yanagi_static_ap: float,
    yanagi_field_ap: float,
    yanagi_flat_ap: float,
) -> _CalPolarityDisorderOracleCase:
    base_case = _make_cal_disorder_oracle_case(
        case_id=case_id,
        element_type=element_type,
        base_mul=base_mul,
        element_disorder_basic_attr=element_disorder_basic_attr,
        expected_base_dmg=expected_base_dmg,
    )
    yanagi_ap_attrs = {
        "field_anomaly_proficiency": yanagi_field_ap,
        "anomaly_proficiency": yanagi_flat_ap,
    }
    dynamic_attrs = {
        **base_case.dynamic_attrs,
        **yanagi_ap_attrs,
    }
    expected_yanagi_ap = yanagi_static_ap * (1 + yanagi_field_ap) + yanagi_flat_ap
    expected_polarity_base_dmg = (
        base_case.expected_final_multipliers[0] * polarity_disorder_ratio
    ) + (expected_yanagi_ap * additional_dmg_ap_ratio)
    expected_final_multipliers = (
        expected_polarity_base_dmg,
        *base_case.expected_final_multipliers[1:],
    )
    return _CalPolarityDisorderOracleCase(
        case_id=case_id,
        base_case=base_case,
        dynamic_attrs=dynamic_attrs,
        expected_dynamic_fields=dynamic_attrs,
        polarity_disorder_ratio=polarity_disorder_ratio,
        additional_dmg_ap_ratio=additional_dmg_ap_ratio,
        yanagi_static_ap=yanagi_static_ap,
        expected_yanagi_ap=expected_yanagi_ap,
        expected_base_disorder_dmg=base_case.expected_final_multipliers[0],
        expected_final_multipliers=expected_final_multipliers,
    )


_CAL_POLARITY_DISORDER_ORACLE_CASES = (
    _make_cal_polarity_disorder_oracle_case(
        case_id="electric-polarity-disorder-ratio-plus-yanagi-ap",
        element_type=3,
        base_mul=125.0,
        element_disorder_basic_attr="shock_disorder_basic_mul",
        expected_base_dmg=1105.0,
        polarity_disorder_ratio=0.13,
        additional_dmg_ap_ratio=17.5,
        yanagi_static_ap=400.0,
        yanagi_field_ap=0.25,
        yanagi_flat_ap=60.0,
    ),
)


def test_migrated_reader_seam_regression_sample_scope_is_representative() -> None:
    selected = {
        (sample.phase, sample.migrated_file, sample.formula_key)
        for sample in _MIGRATED_READER_SEAM_SAMPLES
    }

    assert selected == {
        (
            "P2-A",
            "zsim/sim_progress/Buff/BuffXLogic/AliceAdditionalAbilityApBonus.py",
            "cal_am",
        ),
        (
            "P2-A",
            "zsim/sim_progress/Buff/BuffXLogic/JaneCinema1APTransToDmgBonus.py",
            "cal_ap",
        ),
        (
            "P2-B",
            "zsim/sim_progress/Buff/BuffXLogic/QingYiAdditionalAbilityStunConvertToATK.py",
            "cal_imp",
        ),
        (
            "P2-B",
            "zsim/sim_progress/Buff/BuffXLogic/CannonRotor.py",
            "cal_crit_rate",
        ),
        (
            "P2-B",
            "zsim/sim_progress/Buff/BuffXLogic/Soldier0AnbyCoreSkillCritDMGBonus.py",
            "cal_personal_crit_dmg",
        ),
    }
    assert {sample.phase for sample in _MIGRATED_READER_SEAM_SAMPLES} == {
        "P2-A",
        "P2-B",
    }
    for sample in _MIGRATED_READER_SEAM_SAMPLES:
        migrated_path = PROJECT_ROOT / sample.migrated_file
        assert migrated_path.is_file()
        assert ".codex_worktrees" not in migrated_path.parts


@pytest.mark.parametrize(
    "sample",
    _MIGRATED_READER_SEAM_SAMPLES,
    ids=lambda sample: sample.case_id,
)
def test_migrated_reader_seam_regression_samples_match_retained_helpers(
    monkeypatch: pytest.MonkeyPatch,
    sample: _MigratedReaderSeamSample,
) -> None:
    fixture = _make_attribute_read_fixture(**sample.fixture_kwargs)
    aggregation_calls = _patch_buff_aggregation(
        monkeypatch,
        _dynamic_statement_by_attr(**sample.dynamic_attrs),
    )

    retained_value = _retained_formula_value(
        sample.formula_key,
        _legacy_multiplier_data(fixture),
    )
    reader_snapshot_value = _retained_formula_value(
        sample.formula_key,
        _reader_snapshot_data(fixture.context),
    )
    reader_value = _reader_formula_value(
        sample.formula_key,
        CalculatorBuffAttributeReader(),
        fixture.context,
    )

    assert retained_value == pytest.approx(sample.expected_value)
    assert reader_snapshot_value == pytest.approx(retained_value)
    assert reader_value == pytest.approx(retained_value)
    _assert_aggregation_calls(aggregation_calls, fixture, times=3)


@pytest.mark.parametrize(
    "case",
    _FORMULA_ORACLE_TABLE_CASES,
    ids=lambda case: case.case_id,
)
def test_formula_oracle_table_cases_drive_expected_fields_and_reader_parity(
    monkeypatch: pytest.MonkeyPatch,
    case: _FormulaOracleCase,
) -> None:
    fixture = _run_formula_oracle_case(monkeypatch, case)

    char_buff_count = cast(int, case.fixture_kwargs["char_buff_count"])
    enemy_debuff_count = cast(int, case.fixture_kwargs["enemy_debuff_count"])
    enemy_dot_count = cast(int, case.fixture_kwargs["enemy_dot_count"])
    assert len(fixture.active_buff_view[fixture.char.NAME]) == char_buff_count
    assert len(fixture.enemy.dynamic.dynamic_debuff_list) == enemy_debuff_count
    assert len(fixture.enemy.dynamic.dynamic_dot_list) == enemy_dot_count


@pytest.mark.parametrize(
    "case",
    _AM_RETAINED_MULTIPLIER_ORACLE_CASES,
    ids=lambda case: case.case_id,
)
def test_cal_am_retained_multiplier_data_oracle_rows(
    monkeypatch: pytest.MonkeyPatch,
    case: _AnomalyMasteryRetainedOracleCase,
) -> None:
    _reset_formula_oracle_caches()
    fixture = _make_attribute_read_fixture(**case.fixture_kwargs)
    aggregation_calls = _patch_buff_aggregation(
        monkeypatch,
        _dynamic_statement_by_attr(**case.dynamic_attrs),
    )

    retained_data = _legacy_multiplier_data(fixture)
    reader_snapshot_data = _reader_snapshot_data(fixture.context)

    for attr_name, expected_value in case.expected_dynamic_fields.items():
        for source_label, data in (
            ("retained", retained_data),
            ("reader-snapshot", reader_snapshot_data),
        ):
            assert getattr(data.dynamic, attr_name) == case.tolerance.approx(expected_value), (
                f"{case.case_id}:{source_label}:{attr_name}"
            )

    expected = case.tolerance.approx(case.expected_value)
    retained_value = Calculator.AnomalyMul.cal_am(retained_data)
    reader_snapshot_value = Calculator.AnomalyMul.cal_am(reader_snapshot_data)
    reader_value = CalculatorBuffAttributeReader().read_anomaly_mastery(fixture.context)

    assert retained_value == expected, f"{case.case_id}:retained"
    assert reader_snapshot_value == expected, f"{case.case_id}:reader-snapshot"
    assert reader_value == expected, f"{case.case_id}:reader"
    _assert_aggregation_calls(aggregation_calls, fixture, times=3)


@pytest.mark.parametrize(
    "case",
    _AP_RETAINED_MULTIPLIER_ORACLE_CASES,
    ids=lambda case: case.case_id,
)
def test_cal_ap_retained_multiplier_data_oracle_rows(
    monkeypatch: pytest.MonkeyPatch,
    case: _AnomalyProficiencyRetainedOracleCase,
) -> None:
    _reset_formula_oracle_caches()
    fixture = _make_attribute_read_fixture(**case.fixture_kwargs)
    aggregation_calls = _patch_buff_aggregation(
        monkeypatch,
        _dynamic_statement_by_attr(**case.dynamic_attrs),
    )

    retained_data = _legacy_multiplier_data(fixture)
    reader_snapshot_data = _reader_snapshot_data(fixture.context)

    for attr_name, expected_value in case.expected_dynamic_fields.items():
        for source_label, data in (
            ("retained", retained_data),
            ("reader-snapshot", reader_snapshot_data),
        ):
            assert getattr(data.dynamic, attr_name) == case.tolerance.approx(expected_value), (
                f"{case.case_id}:{source_label}:{attr_name}"
            )

    expected = case.tolerance.approx(case.expected_value)
    retained_value = Calculator.AnomalyMul.cal_ap(retained_data)
    reader_snapshot_value = Calculator.AnomalyMul.cal_ap(reader_snapshot_data)
    reader_value = CalculatorBuffAttributeReader().read_anomaly_proficiency(fixture.context)

    assert retained_value == expected, f"{case.case_id}:retained"
    assert reader_snapshot_value == expected, f"{case.case_id}:reader-snapshot"
    assert reader_value == expected, f"{case.case_id}:reader"
    _assert_aggregation_calls(aggregation_calls, fixture, times=3)


def test_cal_ap_delegates_to_scalar_proficiency_helper_and_keeps_cache(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _make_attribute_read_fixture(ap=300.0)
    aggregation_calls = _patch_buff_aggregation(monkeypatch, {})
    retained_data = _legacy_multiplier_data(fixture)
    helper_calls: list[tuple[Any, Any]] = []

    def fake_calculate_anomaly_proficiency(
        static_statement: Any, dynamic_statement: Any
    ) -> np.float64:
        helper_calls.append((static_statement, dynamic_statement))
        return np.float64(432.0)

    monkeypatch.setattr(
        calculator_module,
        "_calculate_anomaly_proficiency",
        fake_calculate_anomaly_proficiency,
    )

    first_value = Calculator.AnomalyMul.cal_ap(retained_data)
    second_value = Calculator.AnomalyMul.cal_ap(retained_data)
    cache_info = Calculator.AnomalyMul.cal_ap.cache_info()

    assert first_value == pytest.approx(432.0)
    assert second_value == pytest.approx(432.0)
    assert len(helper_calls) == 1
    assert helper_calls[0][0] is retained_data.static
    assert helper_calls[0][1] is retained_data.dynamic
    assert cache_info.hits == 1
    assert cache_info.misses == 1
    assert cache_info.maxsize == 16
    _assert_aggregation_calls(aggregation_calls, fixture, times=1)


def test_cal_imp_delegates_to_scalar_impact_helper_and_remains_uncached(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _make_attribute_read_fixture(imp=80.0)
    aggregation_calls = _patch_buff_aggregation(monkeypatch, {})
    retained_data = _legacy_multiplier_data(fixture)
    helper_calls: list[tuple[Any, Any]] = []

    def fake_calculate_impact(static_statement: Any, dynamic_statement: Any) -> float:
        helper_calls.append((static_statement, dynamic_statement))
        return 321.0

    monkeypatch.setattr(
        calculator_module,
        "_calculate_impact",
        fake_calculate_impact,
    )

    first_value = Calculator.StunMul.cal_imp(retained_data)
    second_value = Calculator.StunMul.cal_imp(retained_data)

    assert first_value == pytest.approx(321.0)
    assert second_value == pytest.approx(321.0)
    assert helper_calls == [
        (retained_data.static, retained_data.dynamic),
        (retained_data.static, retained_data.dynamic),
    ]
    _assert_aggregation_calls(aggregation_calls, fixture, times=1)


@pytest.mark.parametrize(
    "case",
    _IMP_RETAINED_MULTIPLIER_ORACLE_CASES,
    ids=lambda case: case.case_id,
)
def test_cal_imp_retained_multiplier_data_oracle_rows(
    monkeypatch: pytest.MonkeyPatch,
    case: _ImpactRetainedOracleCase,
) -> None:
    _reset_formula_oracle_caches()
    fixture = _make_attribute_read_fixture(**case.fixture_kwargs)
    aggregation_calls = _patch_buff_aggregation(
        monkeypatch,
        _dynamic_statement_by_attr(**case.dynamic_attrs),
    )

    retained_data = _legacy_multiplier_data(fixture)
    reader_snapshot_data = _reader_snapshot_data(fixture.context)

    for attr_name, expected_value in case.expected_dynamic_fields.items():
        for source_label, data in (
            ("retained", retained_data),
            ("reader-snapshot", reader_snapshot_data),
        ):
            assert getattr(data.dynamic, attr_name) == case.tolerance.approx(expected_value), (
                f"{case.case_id}:{source_label}:{attr_name}"
            )

    expected = case.tolerance.approx(case.expected_value)
    retained_value = Calculator.StunMul.cal_imp(retained_data)
    reader_snapshot_value = Calculator.StunMul.cal_imp(reader_snapshot_data)
    reader_value = CalculatorBuffAttributeReader().read_impact(fixture.context)

    assert retained_value == expected, f"{case.case_id}:retained"
    assert reader_snapshot_value == expected, f"{case.case_id}:reader-snapshot"
    assert reader_value == expected, f"{case.case_id}:reader"
    _assert_aggregation_calls(aggregation_calls, fixture, times=3)


def test_stun_array_output_contract_preserves_field_order_dtype_and_product(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _make_attribute_read_fixture(
        name="失衡数组契约",
        imp=80.0,
        damage_ratio=1.0,
        stun_ratio=240.0,
        hit_times=4,
        diff_multiplier=0,
        element_type=3,
        trigger_buff_level=2,
        skill_labels={"aftershock_attack": 1},
        enemy_stun_resistance_attrs={3: 0.20},
        char_buff_count=1,
        enemy_debuff_count=1,
        enemy_dot_count=0,
    )
    aggregation_calls = _patch_buff_aggregation(
        monkeypatch,
        _dynamic_statement_by_attr(
            field_imp_percentage=0.25,
            imp=5.0,
            stun_res=0.15,
            ex_special_skill_stun_bonus=0.25,
            stun_bonus=0.10,
            aftershock_attack_stun_bonus=0.05,
            received_stun_increase=0.30,
        ),
    )

    retained_data = _legacy_multiplier_data(fixture)
    stun_multipliers = Calculator.StunMul(retained_data)
    expected_fields = (
        ("imp", 105.0),
        ("stun_ratio", 60.0),
        ("stun_res", 0.65),
        ("stun_bonus", 1.40),
        ("stun_received", 1.30),
    )
    expected_array = np.array(
        [expected_value for _, expected_value in expected_fields],
        dtype=np.float64,
    )

    stun_array = stun_multipliers.get_stun_array()

    assert tuple(field_name for field_name, _ in expected_fields) == (
        "imp",
        "stun_ratio",
        "stun_res",
        "stun_bonus",
        "stun_received",
    )
    assert stun_array.shape == (5,)
    assert stun_array.dtype == np.float64
    np.testing.assert_allclose(stun_array, expected_array)

    calculator = cast(Calculator, Calculator.__new__(Calculator))
    calculator.stun_multipliers = stun_multipliers
    get_stun_array_calls: list[str] = []
    original_get_stun_array = stun_multipliers.get_stun_array

    def tracking_get_stun_array() -> np.ndarray:
        get_stun_array_calls.append("get_stun_array")
        return original_get_stun_array()

    monkeypatch.setattr(stun_multipliers, "get_stun_array", tracking_get_stun_array)

    stun_value = calculator.cal_stun()

    assert get_stun_array_calls == ["get_stun_array"]
    assert isinstance(stun_value, np.float64)
    assert stun_value == pytest.approx(np.float64(np.prod(expected_array)))
    _assert_aggregation_calls(aggregation_calls, fixture, times=1)


def test_stun_array_delegates_to_module_helper(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stun_multipliers = Calculator.StunMul.__new__(Calculator.StunMul)
    stun_multipliers.imp = 101.0
    stun_multipliers.stun_ratio = 2.0
    stun_multipliers.stun_res = 0.75
    stun_multipliers.stun_bonus = 1.25
    stun_multipliers.stun_received = 1.5
    helper_calls: list[tuple[float, float, float, float, float]] = []
    expected_array = np.array([9.0, 8.0, 7.0, 6.0, 5.0], dtype=np.float64)

    def fake_build_stun_multiplier_array(
        imp: float,
        stun_ratio: float,
        stun_res: float,
        stun_bonus: float,
        stun_received: float,
    ) -> np.ndarray:
        helper_calls.append((imp, stun_ratio, stun_res, stun_bonus, stun_received))
        return expected_array

    monkeypatch.setattr(
        calculator_module,
        "_build_stun_multiplier_array",
        fake_build_stun_multiplier_array,
    )

    stun_array = stun_multipliers.get_stun_array()

    assert helper_calls == [(101.0, 2.0, 0.75, 1.25, 1.5)]
    assert stun_array is expected_array


def test_regular_mul_array_outputs_preserve_field_order_dtype_and_crit_split(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _make_attribute_read_fixture(
        name="常规直伤数组契约",
        atk=100.0,
        crit_rate=0.20,
        crit_damage=0.50,
        static_statement_attrs={"FIRE_DMG_bonus": 0.15},
        damage_ratio=2.0,
        hit_times=2,
        diff_multiplier=0,
        element_type=1,
        trigger_buff_level=0,
        skill_labels={"aftershock_attack": 1},
        enemy_max_def=0.0,
        enemy_damage_resistance_attrs={"FIRE_damage_resistance": 0.0},
        char_buff_count=1,
        enemy_debuff_count=1,
        enemy_dot_count=0,
    )
    aggregation_calls = _patch_buff_aggregation(
        monkeypatch,
        _dynamic_statement_by_attr(
            field_atk_percentage=0.25,
            atk=10.0,
            extra_damage_ratio=0.50,
            base_dmg_increase_percentage=0.20,
            base_dmg_increase=3.0,
            fire_dmg_bonus=0.25,
            normal_attack_dmg_bonus=0.30,
            aftershock_attack_dmg_bonus=0.10,
            all_dmg_bonus=0.20,
            crit_rate=0.10,
            field_crit_rate=0.05,
            crit_rate_received_increase=0.25,
            crit_dmg=0.30,
            field_crit_dmg=0.20,
            aftershock_attack_crit_dmg_bonus=0.10,
            received_crit_dmg_bonus=0.40,
            fire_vulnerability=0.18,
            all_vulnerability=0.12,
            stun_vulnerability_increase=0.20,
            stun_vulnerability_increase_all_time=0.05,
            special_multiplier_zone=0.07,
        ),
    )

    retained_data = _legacy_multiplier_data(fixture)
    regular_multipliers = Calculator.RegularMul(retained_data)
    common_prefix = (
        ("base_dmg", 246.0),
        ("dmg_bonus", 2.0),
    )
    common_suffix = (
        ("defense_mul", 1.0),
        ("res_mul", 1.0),
        ("dmg_vulnerability", 1.30),
        ("stun_vulnerability", 1.05),
        ("special_multiplier_zone", 1.07),
        ("sheer_dmg_bonus", 1.0),
    )
    expected_expect_fields = common_prefix + (("crit_expect", 1.90),) + common_suffix
    expected_crit_fields = common_prefix + (("when_crit_mul", 2.50),) + common_suffix
    expected_not_crit_fields = common_prefix + (("not_crit_mul", 1.0),) + common_suffix

    array_expect = regular_multipliers.get_array_expect()
    array_crit = regular_multipliers.get_array_crit()
    array_not_crit = regular_multipliers.get_array_not_crit()

    assert tuple(name for name, _ in expected_expect_fields) == (
        "base_dmg",
        "dmg_bonus",
        "crit_expect",
        "defense_mul",
        "res_mul",
        "dmg_vulnerability",
        "stun_vulnerability",
        "special_multiplier_zone",
        "sheer_dmg_bonus",
    )
    assert tuple(name for name, _ in expected_crit_fields) == (
        "base_dmg",
        "dmg_bonus",
        "when_crit_mul",
        "defense_mul",
        "res_mul",
        "dmg_vulnerability",
        "stun_vulnerability",
        "special_multiplier_zone",
        "sheer_dmg_bonus",
    )
    assert tuple(name for name, _ in expected_not_crit_fields) == (
        "base_dmg",
        "dmg_bonus",
        "not_crit_mul",
        "defense_mul",
        "res_mul",
        "dmg_vulnerability",
        "stun_vulnerability",
        "special_multiplier_zone",
        "sheer_dmg_bonus",
    )

    for actual_array, expected_fields in (
        (array_expect, expected_expect_fields),
        (array_crit, expected_crit_fields),
        (array_not_crit, expected_not_crit_fields),
    ):
        assert actual_array.shape == (9,)
        assert actual_array.dtype == np.float64
        np.testing.assert_allclose(
            actual_array,
            np.array(
                [expected_value for _, expected_value in expected_fields],
                dtype=np.float64,
            ),
        )

    shared_indexes = np.array([0, 1, 3, 4, 5, 6, 7, 8])
    assert array_expect[2] != pytest.approx(array_crit[2])
    assert array_expect[2] != pytest.approx(array_not_crit[2])
    assert array_crit[2] != pytest.approx(array_not_crit[2])
    np.testing.assert_allclose(array_expect[shared_indexes], array_crit[shared_indexes])
    np.testing.assert_allclose(array_expect[shared_indexes], array_not_crit[shared_indexes])
    _assert_aggregation_calls(aggregation_calls, fixture, times=1)


@pytest.mark.parametrize(
    "case_id,element_type,selected_field,dynamic_attrs",
    _CAL_RES_PEN_READER_SNAPSHOT_COMPATIBILITY_CASES,
    ids=[case[0] for case in _CAL_RES_PEN_READER_SNAPSHOT_COMPATIBILITY_CASES],
)
def test_cal_res_pen_retained_and_reader_snapshot_select_same_dynamic_field(
    monkeypatch: pytest.MonkeyPatch,
    case_id: str,
    element_type: int,
    selected_field: str,
    dynamic_attrs: dict[str, float],
) -> None:
    _reset_formula_oracle_caches()
    fixture = _make_attribute_read_fixture(
        name=f"异常乘区-{case_id}-reader-snapshot-compat",
        damage_ratio=1.0,
        hit_times=1,
        diff_multiplier=0,
        element_type=element_type,
        char_buff_count=1,
        enemy_debuff_count=1,
        enemy_dot_count=1,
    )
    aggregation_calls = _patch_buff_aggregation(
        monkeypatch,
        _dynamic_statement_by_attr(**dynamic_attrs),
    )

    retained_data = _legacy_multiplier_data(fixture)
    reader_snapshot_data = _reader_snapshot_data(fixture.context)
    expected_value = dynamic_attrs[selected_field]

    for source_label, data in (
        ("retained", retained_data),
        ("reader-snapshot", reader_snapshot_data),
    ):
        for field_name in _CAL_RES_PEN_DYNAMIC_FIELD_NAMES:
            assert getattr(data.dynamic, field_name) == pytest.approx(dynamic_attrs[field_name]), (
                f"{case_id}:{source_label}:{field_name}"
            )
        assert _anomaly_mul_res_pen(data) == pytest.approx(expected_value), (
            f"{case_id}:{source_label}:cal_res_pen"
        )

    _assert_aggregation_calls(aggregation_calls, fixture, times=2)


def test_anomaly_res_pen_rejects_invalid_element_for_retained_and_reader_snapshot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _reset_formula_oracle_caches()
    fixture = _make_attribute_read_fixture(
        name="异常乘区-非法属性抗性穿透",
        damage_ratio=1.0,
        hit_times=1,
        diff_multiplier=0,
        element_type=7,
        char_buff_count=1,
        enemy_debuff_count=1,
        enemy_dot_count=0,
    )
    aggregation_calls = _patch_buff_aggregation(
        monkeypatch,
        _dynamic_statement_by_attr(
            physical_res_pen_increase=0.17,
            fire_res_pen_increase=0.18,
            ice_res_pen_increase=0.19,
            electric_res_pen_increase=0.20,
            ether_res_pen_increase=0.21,
            all_res_pen_increase=0.22,
        ),
    )

    retained_data = _legacy_multiplier_data(fixture)
    reader_snapshot_data = _reader_snapshot_data(fixture.context)

    for source_label, data in (
        ("retained", retained_data),
        ("reader-snapshot", reader_snapshot_data),
    ):
        with pytest.raises(
            AssertionError,
            match=calculator_module.INVALID_ELEMENT_ERROR,
        ):
            _anomaly_mul_res_pen(data)
        assert data.dynamic.all_res_pen_increase == pytest.approx(0.22), source_label

    _assert_aggregation_calls(aggregation_calls, fixture, times=2)


def test_formula_parity_fixture_builds_independent_calculator_inputs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _make_attribute_read_fixture(
        name="公式夹具角色",
        am=100.0,
        ap=300.0,
        imp=80.0,
        crit_rate=0.2,
        crit_damage=0.5,
        char_buff_count=2,
        enemy_debuff_count=1,
        enemy_dot_count=2,
    )
    aggregation_calls = _patch_buff_aggregation(
        monkeypatch,
        {
            "局内异常掌控": 0.2,
            "固定异常精通": 30.0,
            "局内冲击力%": 0.1,
        },
    )

    data = _legacy_multiplier_data(fixture)
    reader_data = _reader_snapshot_data(fixture.context)

    assert fixture.char.statement.AM == pytest.approx(100.0)
    assert fixture.char.statement.AP == pytest.approx(300.0)
    assert len(fixture.active_buff_view[fixture.char.NAME]) == 2
    assert tuple(fixture.enemy.dynamic.dynamic_debuff_list) == (fixture.expected_enabled_buff[2:])
    assert tuple(fixture.enemy.dynamic.dynamic_dot_list) == fixture.expected_enemy_dot_buff
    assert data.dynamic.field_anomaly_mastery == pytest.approx(0.2)
    assert data.dynamic.anomaly_proficiency == pytest.approx(30.0)
    assert reader_data.dynamic.field_imp_percentage == pytest.approx(0.1)
    _assert_aggregation_calls(aggregation_calls, fixture, times=2)

    data.dynamic.anomaly_proficiency = -999.0
    fixture.active_buff_view[fixture.char.NAME].append(object())
    fixture.enemy.dynamic.dynamic_debuff_list.append(object())
    fixture.enemy.dynamic.dynamic_dot_list.append(object())

    next_fixture = _make_attribute_read_fixture(
        name="公式夹具角色",
        am=100.0,
        ap=300.0,
        imp=80.0,
        crit_rate=0.2,
        crit_damage=0.5,
        char_buff_count=2,
        enemy_debuff_count=1,
        enemy_dot_count=2,
    )
    next_data = _legacy_multiplier_data(next_fixture)

    assert next_data is not data
    assert len(next_fixture.active_buff_view[next_fixture.char.NAME]) == 2
    assert len(next_fixture.enemy.dynamic.dynamic_debuff_list) == 1
    assert len(next_fixture.enemy.dynamic.dynamic_dot_list) == 2
    assert next_data.dynamic.anomaly_proficiency == pytest.approx(30.0)


@pytest.mark.parametrize(
    (
        "char_buff_count",
        "enemy_debuff_count",
        "enemy_dot_count",
        "case_id",
    ),
    [
        pytest.param(0, 0, 0, "empty-enemy-state", id="empty-enemy-state"),
        pytest.param(0, 1, 0, "one-enemy-debuff", id="one-enemy-debuff"),
        pytest.param(1, 3, 2, "stacked-enemy-debuffs", id="stacked-enemy-debuffs"),
        pytest.param(
            1,
            0,
            2,
            "enemy-dot-cache-participation",
            id="enemy-dot-cache-participation",
        ),
    ],
)
def test_enemy_dynamic_debuff_reads_feed_old_and_reader_formula_snapshots(
    monkeypatch: pytest.MonkeyPatch,
    char_buff_count: int,
    enemy_debuff_count: int,
    enemy_dot_count: int,
    case_id: str,
) -> None:
    fixture = _make_attribute_read_fixture(
        name=f"敌方动态读测试-{case_id}",
        am=100.0,
        ap=300.0,
        char_buff_count=char_buff_count,
        enemy_debuff_count=enemy_debuff_count,
        enemy_dot_count=enemy_dot_count,
    )
    dynamic_statement = _dynamic_statement_by_attr(
        field_anomaly_mastery=0.2,
        anomaly_mastery=5.0,
        field_anomaly_proficiency=0.1,
        anomaly_proficiency=15.0,
        all_vulnerability=0.25,
    )
    aggregation_calls = _patch_buff_aggregation(
        monkeypatch,
        dynamic_statement,
    )

    direct_statement = calculator_module._calculate_dynamic_statement(
        cast(Any, fixture.enemy),
        fixture.active_buff_view,
        cast(Any, fixture.char),
        cast(Any, fixture.context.query_node),
    )

    retained_data = _legacy_multiplier_data(fixture)
    reader_snapshot_data = _reader_snapshot_data(fixture.context)
    reader = CalculatorBuffAttributeReader()

    retained_values = {
        "cal_am": Calculator.AnomalyMul.cal_am(retained_data),
        "cal_ap": Calculator.AnomalyMul.cal_ap(retained_data),
        "cal_dmg_vulnerability": Calculator.RegularMul.cal_dmg_vulnerability(
            retained_data,
            element_type=0,
        ),
    }
    reader_snapshot_values = {
        "cal_am": Calculator.AnomalyMul.cal_am(reader_snapshot_data),
        "cal_ap": Calculator.AnomalyMul.cal_ap(reader_snapshot_data),
        "cal_dmg_vulnerability": Calculator.RegularMul.cal_dmg_vulnerability(
            reader_snapshot_data,
            element_type=0,
        ),
    }
    reader_values = {
        "cal_am": reader.read_anomaly_mastery(fixture.context),
        "cal_ap": reader.read_anomaly_proficiency(fixture.context),
    }

    assert retained_values == pytest.approx(
        {
            "cal_am": 125.0,
            "cal_ap": 345.0,
            "cal_dmg_vulnerability": 1.25,
        }
    )
    assert direct_statement == dynamic_statement
    assert reader_snapshot_values == pytest.approx(retained_values)
    assert reader_values == pytest.approx(
        {
            "cal_am": retained_values["cal_am"],
            "cal_ap": retained_values["cal_ap"],
        }
    )
    assert tuple(fixture.enemy.dynamic.dynamic_debuff_list) == tuple(
        fixture.expected_enabled_buff[char_buff_count:]
    )
    assert tuple(fixture.enemy.dynamic.dynamic_dot_list) == fixture.expected_enemy_dot_buff
    _assert_aggregation_calls(aggregation_calls, fixture, times=5)
    for enabled_buff, *_ in aggregation_calls:
        assert all(dot not in enabled_buff for dot in fixture.expected_enemy_dot_buff)


def test_multiplier_data_cache_key_distinguishes_enemy_dot_participation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _make_attribute_read_fixture(
        name="敌方dot缓存测试",
        am=100.0,
        char_buff_count=1,
        enemy_debuff_count=1,
        enemy_dot_count=0,
    )
    dynamic_statement = _dynamic_statement_by_attr(anomaly_mastery=5.0)
    aggregation_calls = _patch_buff_aggregation(monkeypatch, dynamic_statement)

    first = _legacy_multiplier_data(fixture)

    dynamic_statement.clear()
    dynamic_statement.update(_dynamic_statement_by_attr(anomaly_mastery=9.0))
    enemy_dot = object()
    fixture.enemy.dynamic.dynamic_dot_list.append(enemy_dot)
    second = _legacy_multiplier_data(fixture)

    assert second is not first
    assert first.dynamic.anomaly_mastery == pytest.approx(5.0)
    assert second.dynamic.anomaly_mastery == pytest.approx(9.0)
    assert len(MultiplierData.mul_data_cache) == 2
    _assert_aggregation_calls(aggregation_calls, fixture, times=2)
    for enabled_buff, *_ in aggregation_calls:
        assert enemy_dot not in enabled_buff

    dynamic_statement.clear()
    dynamic_statement.update(_dynamic_statement_by_attr(anomaly_mastery=13.0))
    still_cached = _legacy_multiplier_data(fixture)

    assert still_cached is second
    assert still_cached.dynamic.anomaly_mastery == pytest.approx(9.0)
    _assert_aggregation_calls(aggregation_calls, fixture, times=2)


@pytest.mark.parametrize(
    "case",
    _ANOMALY_SNAPSHOT_ORACLE_CASES,
    ids=lambda case: case.case_id,
)
def test_anomaly_formula_fixture_copies_snapshot_inputs_for_copied_output(
    case: _AnomalySnapshotOracleCase,
) -> None:
    fixture = _make_anomaly_formula_fixture_from_case(case)
    source_snapshot = fixture.source_snapshot
    original_snapshot = source_snapshot.copy()

    assert fixture.anomaly_bar.current_ndarray is not source_snapshot
    np.testing.assert_allclose(fixture.anomaly_bar.current_ndarray, original_snapshot)

    copied = NewAnomaly(
        fixture.anomaly_bar,
        active_by=cast(Any, fixture.activation),
        sim_instance=cast(Any, SimpleNamespace(tick=322)),
    )

    source_snapshot[0, 0] = -111.0
    assert fixture.anomaly_bar.current_ndarray[0, 0] == pytest.approx(original_snapshot[0, 0])
    fixture.anomaly_bar.current_ndarray[0, 0] = -222.0
    assert copied.current_ndarray[0, 0] == pytest.approx(original_snapshot[0, 0])

    next_fixture = _make_settled_anomaly_formula_fixture()
    assert next_fixture.anomaly_bar.current_ndarray[0, 0] == pytest.approx(100.0)


def test_disorder_copied_output_preserves_formula_owner_and_trigger_identity() -> None:
    fixture = _make_settled_anomaly_formula_fixture()
    trigger = SimpleNamespace(
        skill_tag="trigger-disorder",
        skill=SimpleNamespace(char_obj=_make_character(name="当前触发角色")),
    )

    disorder = Disorder(
        fixture.anomaly_bar,
        active_by=cast(Any, trigger),
        sim_instance=cast(Any, fixture.sim_instance),
    )
    polarity = PolarityDisorder(
        fixture.anomaly_bar,
        1.6,
        active_by=cast(Any, trigger),
        sim_instance=cast(Any, fixture.sim_instance),
    )

    for copied in (disorder, polarity):
        assert copied.activated_by is not trigger
        assert copied.activated_by.skill is fixture.activation.skill
        assert copied.activate_by is trigger
        assert copied.source_uuid == fixture.anomaly_bar.UUID
        assert copied.UUID != fixture.anomaly_bar.UUID


@pytest.mark.parametrize(
    "case",
    _COPIED_OUTPUT_PAYLOAD_CASES,
    ids=lambda case: case.case_id,
)
def test_copied_payload_constructors_preserve_formula_inputs_and_payload_fields(
    case: _CopiedOutputPayloadCase,
) -> None:
    fixture = _make_anomaly_formula_fixture_from_case(case.snapshot_case)
    source_snapshot = fixture.source_snapshot
    source_bar = cast(Any, fixture.anomaly_bar)
    _apply_copied_output_payload(source_bar, case.payload_fields)
    copied, runtime_sim = _copy_output_from_payload_case(case, fixture)

    assert copied is not source_bar
    if case.copied_kind == "new_anomaly":
        assert type(copied) is NewAnomaly
        assert copied.is_disorder is False
    elif case.copied_kind == "polarity_disorder":
        assert type(copied) is PolarityDisorder
        assert copied.is_disorder is True
    else:
        assert type(copied) is Disorder
        assert copied.is_disorder is True
    assert copied.sim_instance is runtime_sim
    assert copied.source_uuid == source_bar.UUID
    assert copied.UUID != source_bar.UUID
    if case.copied_kind == "new_anomaly":
        assert copied.activated_by is fixture.activation
        assert copied.activate_by is fixture.activation
    else:
        assert copied.activated_by is not fixture.activation
        assert copied.activated_by.skill is fixture.activation.skill
        assert copied.activate_by is fixture.activation
    assert copied.settled is True

    formula_inputs = {
        "element_type": copied.element_type,
        "scaling_factor": copied.scaling_factor,
    }
    assert set(_COPIED_OUTPUT_FORMULA_INPUT_FIELDS) == {
        "current_ndarray",
        *formula_inputs,
    }
    assert formula_inputs == pytest.approx(
        {
            "element_type": case.payload_fields["element_type"],
            "scaling_factor": case.snapshot_case.scaling_factor,
        }
    )
    assert copied.current_ndarray is not source_bar.current_ndarray
    np.testing.assert_allclose(copied.current_ndarray, source_snapshot)

    effective_anomaly_fields = {
        "current_effective_anomaly": copied.current_effective_anomaly,
        "current_anomaly": copied.current_anomaly,
        "settled": copied.settled,
    }
    assert tuple(effective_anomaly_fields) == _COPIED_OUTPUT_EFFECTIVE_ANOMALY_FIELDS
    assert effective_anomaly_fields == {
        "current_effective_anomaly": pytest.approx(fixture.anomaly_bar.current_effective_anomaly),
        "current_anomaly": pytest.approx(fixture.anomaly_bar.current_anomaly),
        "settled": True,
    }

    expected_remaining_tick = case.payload_fields["max_duration"] - (
        case.runtime_tick - case.payload_fields["last_active"]
    )
    duration_fields = {
        "max_duration": copied.max_duration,
        "last_active": copied.last_active,
        "remaining_tick": copied.remaining_tick(),
    }
    assert tuple(duration_fields) == _COPIED_OUTPUT_DURATION_FIELDS
    assert duration_fields == pytest.approx(
        {
            "max_duration": case.payload_fields["max_duration"],
            "last_active": case.payload_fields["last_active"],
            "remaining_tick": expected_remaining_tick,
        }
    )
    source_bar.max_duration = 999
    source_bar.last_active = 1
    assert copied.remaining_tick() == pytest.approx(expected_remaining_tick)

    listener_report_payload_only_fields = {
        field_name: getattr(copied, field_name)
        for field_name in _COPIED_OUTPUT_LISTENER_REPORT_PAYLOAD_ONLY_FIELDS
    }
    assert set(listener_report_payload_only_fields).isdisjoint(formula_inputs)
    assert set(listener_report_payload_only_fields).isdisjoint(duration_fields)
    assert listener_report_payload_only_fields == {
        "rename_tag": case.payload_fields["rename_tag"],
        "accompany_dot": case.payload_fields["accompany_dot"],
        "anomaly_dmg_ratio": pytest.approx(case.payload_fields["anomaly_dmg_ratio"]),
    }

    assert copied.schedule_priority == 999
    assert not hasattr(copied, "execute_tick")
    source_bar.current_ndarray[0, 0] = -10.0
    assert copied.current_ndarray[0, 0] == pytest.approx(source_snapshot[0, 0])
    copied.current_ndarray[0, 1] = -20.0
    assert source_bar.current_ndarray[0, 1] == pytest.approx(source_snapshot[0, 1])

    if case.copied_kind == "polarity_disorder":
        polarity_only_fields = {
            "polarity_disorder_ratio": copied.polarity_disorder_ratio,
            "additional_dmg_ap_ratio": copied.additional_dmg_ap_ratio,
        }
        assert tuple(polarity_only_fields) == _COPIED_OUTPUT_POLARITY_ONLY_FIELDS
        assert polarity_only_fields == pytest.approx(
            {
                "polarity_disorder_ratio": cast(float, case.polarity_ratio),
                "additional_dmg_ap_ratio": 32,
            }
        )
    else:
        for field_name in _COPIED_OUTPUT_POLARITY_ONLY_FIELDS:
            assert not hasattr(copied, field_name)


def test_new_anomaly_spawn_output_copies_active_payload_without_publish() -> None:
    from zsim.sim_progress.Update import spawn_output

    broadcast_events: list[tuple[object, object]] = []

    def record_broadcast(*, event: object, signal: object) -> None:
        broadcast_events.append((event, signal))

    runtime_sim = SimpleNamespace(
        tick=410,
        listener_manager=SimpleNamespace(broadcast_event=record_broadcast),
    )
    active_bar = AnomalyBar(sim_instance=cast(Any, runtime_sim), element_type=4)
    source_snapshot = _make_anomaly_snapshot(
        (
            266.0,
            1.45,
            5.0,
            80.0,
            1.90,
            0.25,
            0.18,
            12.0,
            0.27,
            1.52,
            1.86,
        )
    )
    active_bar.update_snap_shot(
        (4, np.float64(25.0), source_snapshot),
        cast(Any, SimpleNamespace(effective_anomlay_buildup=lambda: True)),
    )
    _apply_copied_output_payload(
        cast(Any, active_bar),
        {
            "anomaly_dmg_ratio": 2.15,
            "scaling_factor": 1.40,
            "max_duration": 540,
            "last_active": 250,
            "active": True,
            "accompany_dot": "Corruption",
            "rename_tag": "new-anomaly-payload",
        },
    )
    activation = SimpleNamespace(
        skill_tag="payload-skill",
        skill=SimpleNamespace(char_obj=_make_character(name="异常输出角色")),
    )

    copied = cast(
        Any,
        spawn_output(
            active_bar,
            0,
            sim_instance=cast(Any, runtime_sim),
            skill_node=cast(Any, activation),
        ),
    )

    assert isinstance(copied, NewAnomaly)
    copied_payload = cast(Any, copied)
    assert copied is not active_bar
    assert copied.sim_instance is runtime_sim
    assert copied.is_disorder is False
    assert copied.active is True
    assert copied.element_type == 4
    assert copied.accompany_dot == "Corruption"
    assert copied.rename_tag == "new-anomaly-payload"
    assert copied_payload.anomaly_dmg_ratio == pytest.approx(2.15)
    assert copied.scaling_factor == pytest.approx(1.40)
    assert copied.max_duration == 540
    assert copied.last_active == 250
    assert copied.remaining_tick() == pytest.approx(380)
    assert copied.current_effective_anomaly == pytest.approx(25.0)
    assert copied.activated_by is activation
    assert copied.activate_by is activation
    assert active_bar.settled is True
    assert copied.current_ndarray is not active_bar.current_ndarray
    np.testing.assert_allclose(copied.current_ndarray, source_snapshot)
    active_bar.current_ndarray[0, 0] = -30.0
    assert copied.current_ndarray[0, 0] == pytest.approx(source_snapshot[0, 0])
    copied.current_ndarray[0, 1] = -40.0
    assert active_bar.current_ndarray[0, 1] == pytest.approx(source_snapshot[0, 1])
    assert not hasattr(copied, "execute_tick")
    assert broadcast_events == []


@pytest.mark.parametrize(
    (
        "char_buff_count",
        "enemy_debuff_count",
        "dynamic_statement",
        "expected_fields",
        "expected_personal_crit_rate",
        "expected_full_crit_rate",
        "expected_personal_crit_damage",
    ),
    [
        pytest.param(
            0,
            0,
            {},
            {
                "atk": 0.0,
                "field_atk_percentage": 0.0,
                "field_anomaly_mastery": 0.0,
                "anomaly_mastery": 0.0,
                "field_anomaly_proficiency": 0.0,
                "anomaly_proficiency": 0.0,
                "crit_rate": 0.0,
                "field_crit_rate": 0.0,
                "crit_rate_received_increase": 0.0,
                "crit_dmg": 0.0,
                "field_crit_dmg": 0.0,
                "received_crit_dmg_bonus": 0.0,
                "fire_dmg_res_decrease": 0.0,
                "all_vulnerability": 0.0,
            },
            0.2,
            0.2,
            0.8,
            id="empty-input",
        ),
        pytest.param(
            1,
            0,
            {
                "局内异常掌控": 0.25,
                "固定异常精通": 35.0,
                "局内暴击率": 0.05,
                "固定暴击伤害": 0.15,
            },
            {
                "field_anomaly_mastery": 0.25,
                "anomaly_proficiency": 35.0,
                "field_crit_rate": 0.05,
                "crit_dmg": 0.15,
                "crit_rate_received_increase": 0.0,
                "received_crit_dmg_bonus": 0.0,
            },
            0.25,
            0.25,
            0.95,
            id="single-character-buff",
        ),
        pytest.param(
            3,
            0,
            {
                "固定异常掌控": 12.0,
                "局内异常精通": 0.15,
                "局内攻击力%": 0.30,
                "固定攻击力": 120.0,
                "固定暴击率": 0.07,
                "局内暴击伤害": 0.20,
            },
            {
                "atk": 120.0,
                "field_atk_percentage": 0.30,
                "anomaly_mastery": 12.0,
                "field_anomaly_proficiency": 0.15,
                "crit_rate": 0.07,
                "field_crit_dmg": 0.20,
                "crit_rate_received_increase": 0.0,
                "received_crit_dmg_bonus": 0.0,
            },
            0.27,
            0.27,
            1.0,
            id="stacked-character-buffs",
        ),
        pytest.param(
            0,
            2,
            {
                "被暴击几率增加": 0.12,
                "受暴击伤害增加": 0.22,
                "火伤害抗性降低": 0.15,
                "全易伤": 0.10,
                "百分比减防": 0.08,
            },
            {
                "crit_rate": 0.0,
                "field_crit_rate": 0.0,
                "crit_rate_received_increase": 0.12,
                "received_crit_dmg_bonus": 0.22,
                "fire_dmg_res_decrease": 0.15,
                "all_vulnerability": 0.10,
                "percentage_def_reduction": 0.08,
            },
            0.2,
            0.32,
            0.8,
            id="enemy-debuffs-only",
        ),
    ],
)
def test_multiplier_data_get_buff_bonus_builds_dynamic_statement_snapshot(
    monkeypatch: pytest.MonkeyPatch,
    char_buff_count: int,
    enemy_debuff_count: int,
    dynamic_statement: dict[str, float],
    expected_fields: dict[str, float],
    expected_personal_crit_rate: float,
    expected_full_crit_rate: float,
    expected_personal_crit_damage: float,
) -> None:
    MultiplierData.mul_data_cache.clear()
    fixture = _make_attribute_read_fixture(
        am=100.0,
        ap=300.0,
        imp=80.0,
        crit_rate=0.2,
        crit_damage=0.8,
        char_buff_count=char_buff_count,
        enemy_debuff_count=enemy_debuff_count,
    )
    aggregation_calls = _patch_buff_aggregation(monkeypatch, dynamic_statement)

    data = _legacy_multiplier_data(fixture)
    raw_statement = data.get_buff_bonus(
        fixture.active_buff_view,
        fixture.context.query_node,
    )

    assert raw_statement == dynamic_statement
    assert data.static.am == pytest.approx(100.0)
    assert data.static.ap == pytest.approx(300.0)
    assert data.static.imp == pytest.approx(80.0)
    assert data.static.crit_rate == pytest.approx(0.2)
    assert data.static.crit_damage == pytest.approx(0.8)
    for attr_name, expected_value in expected_fields.items():
        assert getattr(data.dynamic, attr_name) == pytest.approx(expected_value)
    personal_crit_rate = Calculator.RegularMul.cal_personal_crit_rate(data)
    full_crit_rate = Calculator.RegularMul.cal_crit_rate(data)
    personal_crit_damage = Calculator.RegularMul.cal_personal_crit_dmg(data)
    assert personal_crit_rate == pytest.approx(expected_personal_crit_rate)
    assert full_crit_rate == pytest.approx(expected_full_crit_rate)
    assert personal_crit_damage == pytest.approx(expected_personal_crit_damage)
    assert full_crit_rate - personal_crit_rate == pytest.approx(
        data.dynamic.crit_rate_received_increase
    )
    assert data.dynamic.ano_extra_bonus["all"] == pytest.approx(0.0)
    _assert_aggregation_calls(aggregation_calls, fixture, times=2)


def test_multiplier_data_dynamic_statement_translates_python_attr_names() -> None:
    attr_values = {
        "anomaly_mastery": 12.0,
        "field_anomaly_mastery": 0.25,
        "crit_rate_received_increase": 0.4,
        "all_anomaly_dmg_mul": 0.5,
    }

    translated_statement = _dynamic_statement_by_attr(**attr_values)

    assert set(translated_statement).issubset(calculator_module.buff_effect_trans)
    assert {
        calculator_module.buff_effect_trans[effect_key]: value
        for effect_key, value in translated_statement.items()
    } == attr_values

    dynamic = MultiplierData.DynamicStatement(translated_statement)
    for attr_name, expected_value in attr_values.items():
        assert getattr(dynamic, attr_name) == pytest.approx(expected_value)
    assert dynamic.ano_extra_bonus["all"] == pytest.approx(attr_values["all_anomaly_dmg_mul"])


def test_multiplier_data_dynamic_statement_rejects_invalid_effect_key() -> None:
    invalid_key = "not-a-real-effect-key"

    with pytest.raises(KeyError, match=f"无效的 Buff 乘区键：{invalid_key}"):
        MultiplierData.DynamicStatement({invalid_key: 1.0})


def test_multiplier_data_cache_key_stability_and_reset_isolation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _make_attribute_read_fixture(
        am=100.0,
        char_buff_count=1,
        enemy_debuff_count=1,
        enemy_dot_count=1,
    )
    dynamic_statement = _dynamic_statement_by_attr(anomaly_mastery=5.0)
    aggregation_calls = _patch_buff_aggregation(monkeypatch, dynamic_statement)

    first = _legacy_multiplier_data(fixture)
    second = _legacy_multiplier_data(fixture)

    assert second is first
    assert second.static is first.static
    assert second.dynamic.anomaly_mastery == pytest.approx(5.0)
    assert len(MultiplierData.mul_data_cache) == 1
    assert len(MultiplierData.StaticStatement._instance_cache) == 1
    _assert_aggregation_calls(aggregation_calls, fixture, times=1)

    dynamic_statement.clear()
    dynamic_statement.update(_dynamic_statement_by_attr(anomaly_mastery=8.0))

    still_cached = _legacy_multiplier_data(fixture)

    assert still_cached is first
    assert still_cached.dynamic.anomaly_mastery == pytest.approx(5.0)
    _assert_aggregation_calls(aggregation_calls, fixture, times=1)

    _reset_formula_oracle_caches()
    refreshed = _legacy_multiplier_data(fixture)

    assert refreshed is not first
    assert refreshed.static is not first.static
    assert refreshed.dynamic.anomaly_mastery == pytest.approx(8.0)
    assert len(MultiplierData.mul_data_cache) == 1
    assert len(MultiplierData.StaticStatement._instance_cache) == 1
    _assert_aggregation_calls(aggregation_calls, fixture, times=2)


@pytest.mark.parametrize(
    (
        "static_am",
        "field_am",
        "flat_am",
        "char_buff_count",
        "enemy_debuff_count",
        "expected",
    ),
    [
        pytest.param(115.0, 0.0, 0.0, 1, 1, 115.0, id="baseline"),
        pytest.param(100.0, 0.15, 0.0, 1, 1, 115.0, id="percentage-buff"),
        pytest.param(100.0, 0.0, 15.0, 1, 1, 115.0, id="flat-buff"),
        pytest.param(115.0, 0.0, 0.0, 0, 0, 115.0, id="no-buff"),
    ],
)
def test_attribute_reader_matches_old_anomaly_mastery_helper(
    monkeypatch: pytest.MonkeyPatch,
    static_am: float,
    field_am: float,
    flat_am: float,
    char_buff_count: int,
    enemy_debuff_count: int,
    expected: float,
) -> None:
    MultiplierData.mul_data_cache.clear()
    fixture = _make_attribute_read_fixture(
        am=static_am,
        char_buff_count=char_buff_count,
        enemy_debuff_count=enemy_debuff_count,
    )
    aggregation_calls = _patch_buff_aggregation(
        monkeypatch,
        {
            "局内异常掌控": field_am,
            "固定异常掌控": flat_am,
        },
    )

    reader_value = CalculatorBuffAttributeReader().read_anomaly_mastery(fixture.context)

    old_data = MultiplierData(
        cast(Any, fixture.enemy),
        fixture.active_buff_view,
        cast(Any, fixture.char),
    )
    old_value = Calculator.AnomalyMul.cal_am(old_data)

    assert reader_value == pytest.approx(old_value)
    assert reader_value == pytest.approx(expected)
    assert aggregation_calls == [
        (
            fixture.expected_enabled_buff,
            None,
            fixture.enemy.sim_instance,
            fixture.char.NAME,
        ),
        (
            fixture.expected_enabled_buff,
            None,
            fixture.enemy.sim_instance,
            fixture.char.NAME,
        ),
    ]


def test_attribute_reader_keeps_query_node_optional(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _make_attribute_read_fixture(am=90.0, enemy_debuff_count=0)

    def fake_cal_buff_total_bonus(**kwargs: object) -> dict[str, float]:
        assert kwargs["judge_obj"] is None
        return {}

    monkeypatch.setattr(
        calculator_module,
        "cal_buff_total_bonus",
        fake_cal_buff_total_bonus,
    )

    assert CalculatorBuffAttributeReader().read_anomaly_mastery(fixture.context) == pytest.approx(
        90.0
    )


@pytest.mark.parametrize(
    (
        "static_ap",
        "field_ap",
        "flat_ap",
        "char_buff_count",
        "enemy_debuff_count",
        "expected",
    ),
    [
        pytest.param(375.0, 0.0, 0.0, 1, 1, 375.0, id="baseline"),
        pytest.param(300.0, 0.25, 0.0, 1, 1, 375.0, id="percentage-buff"),
        pytest.param(300.0, 0.0, 75.0, 1, 1, 375.0, id="flat-buff"),
        pytest.param(375.0, 0.0, 0.0, 0, 0, 375.0, id="no-buff"),
    ],
)
def test_attribute_reader_matches_old_anomaly_proficiency_helper(
    monkeypatch: pytest.MonkeyPatch,
    static_ap: float,
    field_ap: float,
    flat_ap: float,
    char_buff_count: int,
    enemy_debuff_count: int,
    expected: float,
) -> None:
    MultiplierData.mul_data_cache.clear()
    fixture = _make_attribute_read_fixture(
        name="时流贤者",
        ap=static_ap,
        char_buff_count=char_buff_count,
        enemy_debuff_count=enemy_debuff_count,
    )
    aggregation_calls = _patch_buff_aggregation(
        monkeypatch,
        {
            "局内异常精通": field_ap,
            "固定异常精通": flat_ap,
        },
    )

    reader_value = CalculatorBuffAttributeReader().read_anomaly_proficiency(fixture.context)

    old_data = MultiplierData(
        cast(Any, fixture.enemy),
        fixture.active_buff_view,
        cast(Any, fixture.char),
    )
    old_value = Calculator.AnomalyMul.cal_ap(old_data)

    assert reader_value == pytest.approx(old_value)
    assert reader_value == pytest.approx(expected)
    assert aggregation_calls == [
        (
            fixture.expected_enabled_buff,
            None,
            fixture.enemy.sim_instance,
            fixture.char.NAME,
        ),
        (
            fixture.expected_enabled_buff,
            None,
            fixture.enemy.sim_instance,
            fixture.char.NAME,
        ),
    ]


def test_calculator_reader_service_pen_ratio_matches_retained_formula(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    MultiplierData.mul_data_cache.clear()
    fixture = _make_attribute_read_fixture(
        name="丽娜",
        static_statement_attrs={"PEN_ratio": 0.10},
    )
    aggregation_calls = _patch_buff_aggregation(
        monkeypatch,
        _dynamic_statement_by_attr(pen_ratio=0.15),
    )
    service = get_calculator_buff_attribute_reader_service()

    reader_value = service.read_pen_ratio(fixture.context)
    retained_value = _legacy_pen_ratio_oracle(fixture)

    assert reader_value == pytest.approx(0.25)
    assert reader_value == pytest.approx(retained_value)
    assert aggregation_calls == [
        (
            fixture.expected_enabled_buff,
            None,
            fixture.enemy.sim_instance,
            fixture.char.NAME,
        ),
        (
            fixture.expected_enabled_buff,
            None,
            fixture.enemy.sim_instance,
            fixture.char.NAME,
        ),
    ]


@pytest.mark.parametrize(
    (
        "static_imp",
        "field_imp",
        "flat_imp",
        "char_buff_count",
        "enemy_debuff_count",
        "expected",
    ),
    [
        pytest.param(100.0, 0.0, 0.0, 1, 1, 100.0, id="baseline"),
        pytest.param(100.0, 0.2, 0.0, 1, 1, 120.0, id="percentage-buff"),
        pytest.param(100.0, 0.0, 12.0, 1, 1, 112.0, id="flat-buff"),
        pytest.param(90.0, 0.1, 9.0, 0, 1, 108.0, id="enemy-debuff"),
        pytest.param(123.0, 0.0, 0.0, 0, 0, 123.0, id="no-buff"),
    ],
)
def test_p2b_parity_fixture_matches_old_impact_helper(
    monkeypatch: pytest.MonkeyPatch,
    static_imp: float,
    field_imp: float,
    flat_imp: float,
    char_buff_count: int,
    enemy_debuff_count: int,
    expected: float,
) -> None:
    MultiplierData.mul_data_cache.clear()
    fixture = _make_attribute_read_fixture(
        name="冲击测试",
        imp=static_imp,
        char_buff_count=char_buff_count,
        enemy_debuff_count=enemy_debuff_count,
    )
    aggregation_calls = _patch_buff_aggregation(
        monkeypatch,
        {
            "局内冲击力%": field_imp,
            "固定冲击力": flat_imp,
        },
    )

    reader_value = CalculatorBuffAttributeReader().read_impact(fixture.context)
    old_value = _legacy_impact_oracle(fixture)

    assert reader_value == pytest.approx(old_value)
    assert reader_value == pytest.approx(expected)
    _assert_aggregation_calls(aggregation_calls, fixture)


@pytest.mark.parametrize(
    (
        "name",
        "static_am",
        "static_ap",
        "static_imp",
        "dynamic_attrs",
        "char_buff_count",
        "enemy_debuff_count",
        "expected_values",
    ),
    [
        pytest.param(
            "static-only",
            115.0,
            375.0,
            100.0,
            {},
            0,
            0,
            {"cal_am": 115.0, "cal_ap": 375.0, "cal_imp": 100.0},
            id="static-only",
        ),
        pytest.param(
            "dynamic-flat",
            100.0,
            300.0,
            80.0,
            {
                "anomaly_mastery": 15.0,
                "anomaly_proficiency": 75.0,
                "imp": 12.0,
            },
            1,
            1,
            {"cal_am": 115.0, "cal_ap": 375.0, "cal_imp": 92.0},
            id="dynamic-flat",
        ),
        pytest.param(
            "field-buff",
            100.0,
            300.0,
            80.0,
            {
                "field_anomaly_mastery": 0.15,
                "field_anomaly_proficiency": 0.25,
                "field_imp_percentage": 0.10,
            },
            1,
            1,
            {"cal_am": 115.0, "cal_ap": 375.0, "cal_imp": 88.0},
            id="field-buff",
        ),
    ],
)
def test_calculator_am_ap_impact_formula_family_matches_reader_snapshot_parity(
    monkeypatch: pytest.MonkeyPatch,
    name: str,
    static_am: float,
    static_ap: float,
    static_imp: float,
    dynamic_attrs: dict[str, float],
    char_buff_count: int,
    enemy_debuff_count: int,
    expected_values: dict[str, float],
) -> None:
    fixture = _make_attribute_read_fixture(
        name=name,
        am=static_am,
        ap=static_ap,
        imp=static_imp,
        char_buff_count=char_buff_count,
        enemy_debuff_count=enemy_debuff_count,
    )
    aggregation_calls = _patch_buff_aggregation(
        monkeypatch,
        _dynamic_statement_by_attr(**dynamic_attrs),
    )

    retained_data = _legacy_multiplier_data(fixture)
    reader_snapshot_data = _reader_snapshot_data(fixture.context)
    retained_formula_values = {
        "cal_am": Calculator.AnomalyMul.cal_am(retained_data),
        "cal_ap": Calculator.AnomalyMul.cal_ap(retained_data),
        "cal_imp": Calculator.StunMul.cal_imp(retained_data),
    }
    reader_snapshot_formula_values = {
        "cal_am": Calculator.AnomalyMul.cal_am(reader_snapshot_data),
        "cal_ap": Calculator.AnomalyMul.cal_ap(reader_snapshot_data),
        "cal_imp": Calculator.StunMul.cal_imp(reader_snapshot_data),
    }
    reader = CalculatorBuffAttributeReader()
    reader_values = {
        "cal_am": reader.read_anomaly_mastery(fixture.context),
        "cal_ap": reader.read_anomaly_proficiency(fixture.context),
        "cal_imp": reader.read_impact(fixture.context),
    }

    assert retained_formula_values == pytest.approx(expected_values)
    assert reader_snapshot_formula_values == pytest.approx(retained_formula_values)
    assert reader_values == pytest.approx(retained_formula_values)
    _assert_aggregation_calls(aggregation_calls, fixture, times=5)


@pytest.mark.parametrize(
    (
        "dynamic_attrs",
        "expected_values",
        "expected_received_crit_rate",
        "expected_received_crit_damage",
    ),
    [
        pytest.param(
            {},
            {
                "cal_crit_rate": 0.2,
                "cal_personal_crit_rate": 0.2,
                "cal_crit_dmg": 0.5,
                "cal_crit_expect": 1.1,
                "cal_personal_crit_dmg": 0.5,
            },
            0.0,
            0.0,
            id="static-only",
        ),
        pytest.param(
            {
                "crit_rate": 0.1,
                "field_crit_rate": 0.05,
                "crit_dmg": 0.3,
                "field_crit_dmg": 0.2,
            },
            {
                "cal_crit_rate": 0.35,
                "cal_personal_crit_rate": 0.35,
                "cal_crit_dmg": 1.0,
                "cal_crit_expect": 1.35,
                "cal_personal_crit_dmg": 1.0,
            },
            0.0,
            0.0,
            id="personal-fields",
        ),
        pytest.param(
            {
                "crit_rate": 0.1,
                "field_crit_rate": 0.05,
                "crit_rate_received_increase": 0.25,
                "crit_dmg": 0.3,
                "field_crit_dmg": 0.2,
                "received_crit_dmg_bonus": 0.4,
            },
            {
                "cal_crit_rate": 0.6,
                "cal_personal_crit_rate": 0.35,
                "cal_crit_dmg": 1.4,
                "cal_crit_expect": 1.84,
                "cal_personal_crit_dmg": 1.0,
            },
            0.25,
            0.4,
            id="received-fields-excluded-from-personal-values",
        ),
    ],
)
def test_calculator_regular_mul_crit_formula_families_preserve_received_boundaries(
    monkeypatch: pytest.MonkeyPatch,
    dynamic_attrs: dict[str, float],
    expected_values: dict[str, float],
    expected_received_crit_rate: float,
    expected_received_crit_damage: float,
) -> None:
    fixture = _make_attribute_read_fixture(
        name="双暴公式角色",
        crit_rate=0.2,
        crit_damage=0.5,
        damage_ratio=1.0,
        hit_times=1,
        diff_multiplier=0,
        char_buff_count=1,
        enemy_debuff_count=1,
    )
    aggregation_calls = _patch_buff_aggregation(
        monkeypatch,
        _dynamic_statement_by_attr(**dynamic_attrs),
    )

    retained_data = _legacy_multiplier_data(fixture)
    retained_dynamic = cast(Any, retained_data).dynamic
    values = {
        "cal_crit_rate": Calculator.RegularMul.cal_crit_rate(retained_data),
        "cal_personal_crit_rate": Calculator.RegularMul.cal_personal_crit_rate(retained_data),
        "cal_crit_dmg": Calculator.RegularMul.cal_crit_dmg(retained_data),
        "cal_crit_expect": _regular_mul_crit_expect(retained_data),
        "cal_personal_crit_dmg": Calculator.RegularMul.cal_personal_crit_dmg(retained_data),
    }

    assert values == pytest.approx(expected_values)
    assert retained_dynamic.crit_rate_received_increase == pytest.approx(
        expected_received_crit_rate
    )
    assert retained_dynamic.received_crit_dmg_bonus == pytest.approx(expected_received_crit_damage)
    assert values["cal_crit_rate"] - values["cal_personal_crit_rate"] == pytest.approx(
        retained_dynamic.crit_rate_received_increase
    )
    assert values["cal_crit_dmg"] - values["cal_personal_crit_dmg"] == pytest.approx(
        retained_dynamic.received_crit_dmg_bonus
    )
    assert values["cal_crit_expect"] == pytest.approx(
        1 + min(1, values["cal_crit_rate"]) * values["cal_crit_dmg"]
    )
    assert values["cal_personal_crit_dmg"] == pytest.approx(
        cast(Any, retained_data).static.crit_damage
        + retained_dynamic.crit_dmg
        + retained_dynamic.field_crit_dmg
    )
    _assert_aggregation_calls(aggregation_calls, fixture, times=1)


def test_regular_mul_damage_bonus_delegates_to_module_helper(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _make_attribute_read_fixture(
        name="增伤委托",
        static_statement_attrs={"FIRE_DMG_bonus": 0.15},
        damage_ratio=1.0,
        hit_times=1,
        diff_multiplier=0,
        element_type=1,
        trigger_buff_level=0,
        skill_labels={"aftershock_attack": 1},
        char_buff_count=1,
        enemy_debuff_count=0,
    )
    aggregation_calls = _patch_buff_aggregation(
        monkeypatch,
        _dynamic_statement_by_attr(
            fire_dmg_bonus=0.25,
            normal_attack_dmg_bonus=0.30,
            aftershock_attack_dmg_bonus=0.10,
            all_dmg_bonus=0.20,
        ),
    )
    retained_data = _legacy_multiplier_data(fixture)
    helper_calls: list[tuple[Any, Any, Any]] = []

    def fake_calculate_damage_bonus(
        static_statement: Any,
        dynamic_statement: Any,
        judge_node: SkillNode,
    ) -> float:
        helper_calls.append((static_statement, dynamic_statement, judge_node))
        return 6.54

    monkeypatch.setattr(
        calculator_module,
        "_calculate_damage_bonus",
        fake_calculate_damage_bonus,
    )

    first_value = Calculator.RegularMul.cal_dmg_bonus(retained_data)
    second_value = Calculator.RegularMul.cal_dmg_bonus(retained_data)

    assert first_value == pytest.approx(6.54)
    assert second_value == pytest.approx(6.54)
    assert helper_calls == [
        (retained_data.static, retained_data.dynamic, retained_data.judge_node),
        (retained_data.static, retained_data.dynamic, retained_data.judge_node),
    ]
    _assert_aggregation_calls(aggregation_calls, fixture, times=1)


@pytest.mark.parametrize(
    ("damage_ratio", "attr", "dynamic_attrs", "expected_value"),
    [
        pytest.param(2.0, 100.0, {}, 200.0, id="neutral"),
        pytest.param(
            1.2,
            550.0,
            {
                "extra_damage_ratio": 0.3,
                "base_dmg_increase_percentage": 0.2,
                "base_dmg_increase": 12.0,
            },
            1002.0,
            id="dynamic-ap",
        ),
    ],
)
def test_regular_mul_base_damage_scalar_helper_preserves_current_formula(
    damage_ratio: float,
    attr: float,
    dynamic_attrs: dict[str, float],
    expected_value: float,
) -> None:
    dynamic_statement_attrs = {
        "extra_damage_ratio": 0.0,
        "base_dmg_increase_percentage": 0.0,
        "base_dmg_increase": 0.0,
    }
    dynamic_statement_attrs.update(dynamic_attrs)
    dynamic_statement = SimpleNamespace(**dynamic_statement_attrs)

    assert calculator_module._calculate_base_damage(
        damage_ratio,
        attr,
        dynamic_statement,
    ) == pytest.approx(expected_value)


def test_regular_mul_base_damage_delegates_to_module_helper_and_base_attr_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _make_attribute_read_fixture(
        name="base damage delegate",
        damage_ratio=3.6,
        hit_times=3,
        diff_multiplier=3,
        char_buff_count=1,
        enemy_debuff_count=1,
    )
    aggregation_calls = _patch_buff_aggregation(
        monkeypatch,
        _dynamic_statement_by_attr(
            extra_damage_ratio=0.3,
            base_dmg_increase_percentage=0.2,
            base_dmg_increase=12.0,
        ),
    )
    retained_data = _legacy_multiplier_data(fixture)
    regular_mul = _regular_mul_oracle()
    base_attr_calls: list[tuple[Any, int, MultiplierData]] = []
    helper_calls: list[tuple[float, float, Any]] = []

    def fake_cal_base_attr(self: Any, base_attr: int, data: MultiplierData) -> float:
        base_attr_calls.append((self, base_attr, data))
        return 444.0

    def fake_calculate_base_damage(
        damage_ratio: float, attr: float, dynamic_statement: Any
    ) -> float:
        helper_calls.append((damage_ratio, attr, dynamic_statement))
        return 8.88

    monkeypatch.setattr(
        Calculator.RegularMul,
        "cal_base_attr",
        fake_cal_base_attr,
    )
    monkeypatch.setattr(
        calculator_module,
        "_calculate_base_damage",
        fake_calculate_base_damage,
    )

    assert regular_mul.cal_base_dmg(retained_data) == pytest.approx(8.88)
    assert len(base_attr_calls) == 1
    called_self, called_base_attr, called_data = base_attr_calls[0]
    assert called_self is regular_mul
    assert called_base_attr == 3
    assert called_data is retained_data
    assert len(helper_calls) == 1
    called_damage_ratio, called_attr, called_dynamic = helper_calls[0]
    assert called_damage_ratio == pytest.approx(1.2)
    assert called_attr == pytest.approx(444.0)
    assert called_dynamic is retained_data.dynamic
    _assert_aggregation_calls(aggregation_calls, fixture, times=1)


def test_regular_mul_branch_matrix_defense_group_delegates_to_module_helpers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _make_attribute_read_fixture(
        name="防御乘区委托",
        static_statement_attrs={"PEN_ratio": 0.10, "PEN_numeric": 20.0},
        damage_ratio=1.0,
        hit_times=1,
        diff_multiplier=0,
        element_type=1,
        enemy_max_def=500.0,
        char_buff_count=0,
        enemy_debuff_count=1,
    )
    aggregation_calls = _patch_buff_aggregation(
        monkeypatch,
        _dynamic_statement_by_attr(
            percentage_def_reduction=0.25,
            def_reduction=50.0,
            pen_ratio=0.15,
            pen_numeric=30.0,
        ),
    )
    retained_data = _legacy_multiplier_data(fixture)
    regular_mul = _regular_mul_oracle()
    helper_calls: list[tuple[Any, ...]] = []

    def fake_calculate_attacker_level_coefficient(attacker_level: int) -> int:
        helper_calls.append(("k-attacker", attacker_level))
        return 777

    def fake_calculate_pen_ratio(
        static_statement: Any,
        dynamic_statement: Any,
        *,
        addon_pen_ratio: float = 0.0,
    ) -> float:
        helper_calls.append(("pen-ratio", static_statement, dynamic_statement, addon_pen_ratio))
        return 0.33

    def fake_calculate_recipient_defense(
        enemy_obj: Any,
        static_statement: Any,
        dynamic_statement: Any,
        pen_ratio: float,
        *,
        addon_pen_ratio: float = 0.0,
        addon_pen_numeric: float = 0.0,
    ) -> float:
        helper_calls.append(
            (
                "recipient-defense",
                enemy_obj,
                static_statement,
                dynamic_statement,
                pen_ratio,
                addon_pen_ratio,
                addon_pen_numeric,
            )
        )
        return 123.0

    monkeypatch.setattr(
        calculator_module,
        "_calculate_attacker_level_coefficient",
        fake_calculate_attacker_level_coefficient,
    )
    monkeypatch.setattr(
        calculator_module,
        "_calculate_pen_ratio",
        fake_calculate_pen_ratio,
    )
    monkeypatch.setattr(
        calculator_module,
        "_calculate_recipient_defense",
        fake_calculate_recipient_defense,
    )

    assert regular_mul.cal_defense_mul(retained_data) == pytest.approx(777.0 / (777.0 + 123.0))
    assert Calculator.RegularMul.cal_pen_ratio(
        retained_data,
        addon_pen_ratio=0.12,
    ) == pytest.approx(0.33)
    assert Calculator.RegularMul.cal_recipient_def(
        retained_data,
        0.44,
        addon_pen_ratio=0.04,
        addon_pen_numeric=5.0,
    ) == pytest.approx(123.0)
    assert Calculator.RegularMul.cal_k_attacker(99) == 777
    assert helper_calls == [
        ("k-attacker", 60),
        ("pen-ratio", retained_data.static, retained_data.dynamic, 0.0),
        (
            "recipient-defense",
            retained_data.enemy_obj,
            retained_data.static,
            retained_data.dynamic,
            0.33,
            0.0,
            0.0,
        ),
        ("pen-ratio", retained_data.static, retained_data.dynamic, 0.12),
        (
            "recipient-defense",
            retained_data.enemy_obj,
            retained_data.static,
            retained_data.dynamic,
            0.44,
            0.04,
            5.0,
        ),
        ("k-attacker", 99),
    ]
    _assert_aggregation_calls(aggregation_calls, fixture, times=1)


def test_regular_mul_branch_matrix_res_vulnerability_and_special_delegate_to_module_helpers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _make_attribute_read_fixture(
        name="抗性易伤特殊倍率委托",
        damage_ratio=1.0,
        hit_times=1,
        diff_multiplier=0,
        element_type=1,
        char_buff_count=1,
        enemy_debuff_count=1,
    )
    fixture.enemy.dynamic.stun = True
    fixture.enemy.stun_DMG_take_ratio = 0.5
    aggregation_calls = _patch_buff_aggregation(
        monkeypatch,
        _dynamic_statement_by_attr(
            fire_dmg_res_decrease=0.05,
            fire_res_pen_increase=0.07,
            all_dmg_res_decrease=0.03,
            all_res_pen_increase=0.02,
            fire_vulnerability=0.25,
            all_vulnerability=0.10,
            stun_vulnerability_increase=0.40,
            stun_vulnerability_increase_all_time=0.15,
            special_multiplier_zone=0.60,
        ),
    )
    retained_data = _legacy_multiplier_data(fixture)
    helper_calls: list[tuple[Any, ...]] = []

    def fake_calculate_resistance_multiplier(
        enemy_obj: Any,
        dynamic_statement: Any,
        element_type: Any,
        *,
        snapshot_res_pen: float = 0,
    ) -> float:
        helper_calls.append(
            (
                "resistance",
                enemy_obj,
                dynamic_statement,
                element_type,
                snapshot_res_pen,
            )
        )
        return 0.42

    def fake_calculate_damage_vulnerability(dynamic_statement: Any, element_type: Any) -> float:
        helper_calls.append(("damage-vulnerability", dynamic_statement, element_type))
        return 1.23

    def fake_calculate_stun_vulnerability(enemy_obj: Any, dynamic_statement: Any) -> float:
        helper_calls.append(("stun-vulnerability", enemy_obj, dynamic_statement))
        return 2.34

    def fake_calculate_special_multiplier(dynamic_statement: Any) -> float:
        helper_calls.append(("special", dynamic_statement))
        return 3.45

    monkeypatch.setattr(
        calculator_module,
        "_calculate_resistance_multiplier",
        fake_calculate_resistance_multiplier,
    )
    monkeypatch.setattr(
        calculator_module,
        "_calculate_damage_vulnerability",
        fake_calculate_damage_vulnerability,
    )
    monkeypatch.setattr(
        calculator_module,
        "_calculate_stun_vulnerability",
        fake_calculate_stun_vulnerability,
    )
    monkeypatch.setattr(
        calculator_module,
        "_calculate_special_multiplier",
        fake_calculate_special_multiplier,
    )

    assert isinstance(retained_data.judge_node, SkillNode)
    judge_node = retained_data.judge_node
    assert Calculator.RegularMul.cal_res_mul(retained_data) == pytest.approx(0.42)
    assert Calculator.RegularMul.cal_res_mul(
        retained_data,
        element_type=3,
        snapshot_res_pen=0.44,
    ) == pytest.approx(0.42)
    assert Calculator.RegularMul.cal_dmg_vulnerability(retained_data) == pytest.approx(1.23)
    assert Calculator.RegularMul.cal_dmg_vulnerability(
        retained_data,
        element_type=4,
    ) == pytest.approx(1.23)
    assert Calculator.RegularMul.cal_stun_vulnerability(retained_data) == pytest.approx(2.34)
    assert Calculator.RegularMul.cal_special_mul(retained_data) == pytest.approx(3.45)
    assert helper_calls == [
        (
            "resistance",
            retained_data.enemy_obj,
            retained_data.dynamic,
            judge_node.element_type,
            0,
        ),
        ("resistance", retained_data.enemy_obj, retained_data.dynamic, 3, 0.44),
        (
            "damage-vulnerability",
            retained_data.dynamic,
            judge_node.element_type,
        ),
        ("damage-vulnerability", retained_data.dynamic, 4),
        ("stun-vulnerability", retained_data.enemy_obj, retained_data.dynamic),
        ("special", retained_data.dynamic),
    ]
    _assert_aggregation_calls(aggregation_calls, fixture, times=1)


def test_regular_mul_full_crit_rate_delegates_to_module_helper(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _make_attribute_read_fixture(
        name="完整暴击率委托",
        crit_rate=0.2,
        damage_ratio=1.0,
        hit_times=1,
        diff_multiplier=0,
        char_buff_count=1,
        enemy_debuff_count=1,
    )
    aggregation_calls = _patch_buff_aggregation(
        monkeypatch,
        _dynamic_statement_by_attr(
            crit_rate=0.1,
            field_crit_rate=0.05,
            crit_rate_received_increase=0.25,
        ),
    )
    retained_data = _legacy_multiplier_data(fixture)
    helper_calls: list[tuple[Any, Any]] = []

    def fake_calculate_full_crit_rate(static_statement: Any, dynamic_statement: Any) -> float:
        helper_calls.append((static_statement, dynamic_statement))
        return 9.87

    monkeypatch.setattr(
        calculator_module,
        "_calculate_full_crit_rate",
        fake_calculate_full_crit_rate,
    )

    first_value = Calculator.RegularMul.cal_crit_rate(retained_data)
    second_value = Calculator.RegularMul.cal_crit_rate(retained_data)

    assert first_value == pytest.approx(9.87)
    assert second_value == pytest.approx(9.87)
    assert helper_calls == [
        (retained_data.static, retained_data.dynamic),
        (retained_data.static, retained_data.dynamic),
    ]
    _assert_aggregation_calls(aggregation_calls, fixture, times=1)


@pytest.mark.parametrize(
    ("crit_rate", "crit_damage", "expected_value"),
    [
        pytest.param(0.60, 1.40, 1.84, id="uses-full-crit-scalars"),
        pytest.param(1.25, 1.40, 2.40, id="clamps-over-100-percent-rate"),
    ],
)
def test_regular_mul_crit_expect_scalar_helper_preserves_current_formula(
    crit_rate: float,
    crit_damage: float,
    expected_value: float,
) -> None:
    assert calculator_module._calculate_crit_expectation(
        crit_rate,
        crit_damage,
    ) == pytest.approx(expected_value)


def test_regular_mul_crit_expect_delegates_to_module_helper(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _make_attribute_read_fixture(
        name="暴击期望委托",
        crit_rate=0.2,
        crit_damage=0.5,
        damage_ratio=1.0,
        hit_times=1,
        diff_multiplier=0,
        char_buff_count=1,
        enemy_debuff_count=1,
    )
    aggregation_calls = _patch_buff_aggregation(
        monkeypatch,
        _dynamic_statement_by_attr(
            crit_rate=0.1,
            field_crit_rate=0.05,
            crit_rate_received_increase=0.25,
            crit_dmg=0.3,
            field_crit_dmg=0.2,
            received_crit_dmg_bonus=0.4,
        ),
    )
    retained_data = _legacy_multiplier_data(fixture)
    regular_mul = _regular_mul_oracle()
    regular_mul.crit_rate = Calculator.RegularMul.cal_crit_rate(retained_data)
    regular_mul.crit_dmg = Calculator.RegularMul.cal_crit_dmg(retained_data)
    helper_calls: list[tuple[float, float]] = []

    def fake_calculate_crit_expectation(
        crit_rate: float,
        crit_damage: float,
    ) -> float:
        helper_calls.append((crit_rate, crit_damage))
        return 7.65

    monkeypatch.setattr(
        calculator_module,
        "_calculate_crit_expectation",
        fake_calculate_crit_expectation,
    )

    value = regular_mul.cal_crit_expect(retained_data)

    assert value == pytest.approx(7.65)
    assert len(helper_calls) == 1
    assert helper_calls[0] == pytest.approx((0.60, 1.40))
    _assert_aggregation_calls(aggregation_calls, fixture, times=1)


def test_regular_mul_personal_crit_damage_delegates_to_module_helper(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _make_attribute_read_fixture(
        name="个人暴击伤害委托",
        crit_damage=0.5,
        damage_ratio=1.0,
        hit_times=1,
        diff_multiplier=0,
        char_buff_count=1,
        enemy_debuff_count=1,
    )
    aggregation_calls = _patch_buff_aggregation(
        monkeypatch,
        _dynamic_statement_by_attr(
            crit_dmg=0.3,
            field_crit_dmg=0.2,
            received_crit_dmg_bonus=0.4,
        ),
    )
    retained_data = _legacy_multiplier_data(fixture)
    helper_calls: list[tuple[Any, Any]] = []

    def fake_calculate_personal_crit_damage(static_statement: Any, dynamic_statement: Any) -> float:
        helper_calls.append((static_statement, dynamic_statement))
        return 8.76

    monkeypatch.setattr(
        calculator_module,
        "_calculate_personal_crit_damage",
        fake_calculate_personal_crit_damage,
    )

    first_value = Calculator.RegularMul.cal_personal_crit_dmg(retained_data)
    second_value = Calculator.RegularMul.cal_personal_crit_dmg(retained_data)

    assert first_value == pytest.approx(8.76)
    assert second_value == pytest.approx(8.76)
    assert helper_calls == [
        (retained_data.static, retained_data.dynamic),
        (retained_data.static, retained_data.dynamic),
    ]
    _assert_aggregation_calls(aggregation_calls, fixture, times=1)


def test_reader_personal_crit_damage_anchor_preserves_full_and_personal_crit_contrast(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    MultiplierData.mul_data_cache.clear()
    fixture = _make_attribute_read_fixture(
        name="个人暴击伤害读口锚点",
        crit_damage=0.5,
        damage_ratio=1.0,
        hit_times=1,
        diff_multiplier=0,
        char_buff_count=1,
        enemy_debuff_count=1,
    )
    aggregation_calls = _patch_buff_aggregation(
        monkeypatch,
        _dynamic_statement_by_attr(
            crit_dmg=0.3,
            field_crit_dmg=0.2,
            received_crit_dmg_bonus=0.4,
        ),
    )
    formula_calls: list[MultiplierData] = []

    def fake_cal_personal_crit_dmg(data: MultiplierData) -> float:
        formula_calls.append(data)
        return 8.76

    monkeypatch.setattr(
        Calculator.RegularMul,
        "cal_personal_crit_dmg",
        fake_cal_personal_crit_dmg,
    )

    reader_value = CalculatorBuffAttributeReader().read_personal_crit_damage(fixture.context)

    assert reader_value == pytest.approx(8.76)
    assert len(formula_calls) == 1
    formula_data = formula_calls[0]
    formula_dynamic = cast(Any, formula_data).dynamic
    assert cast(Any, formula_data).static.crit_damage == pytest.approx(0.5)
    assert formula_dynamic.crit_dmg == pytest.approx(0.3)
    assert formula_dynamic.field_crit_dmg == pytest.approx(0.2)
    assert formula_dynamic.received_crit_dmg_bonus == pytest.approx(0.4)
    assert Calculator.RegularMul.cal_crit_dmg(formula_data) == pytest.approx(1.4)
    _assert_aggregation_calls(aggregation_calls, fixture, times=1)


def test_full_crit_damage_reader_api_and_snapshot_contract_stay_bounded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    MultiplierData.mul_data_cache.clear()
    contract_cls = getattr(calculator_module, "RetainedFormulaSnapshot")
    snapshot_cls = getattr(calculator_module, "_CalculatorRetainedFormulaSnapshot")
    snapshot_fields = [field_info.name for field_info in fields(snapshot_cls)]
    expected_snapshot_fields = [
        "static",
        "dynamic",
        "judge_node",
        "enemy_obj",
        "char_level",
    ]
    forbidden_snapshot_fields = {
        "char_instance",
        "runtime_view",
        "array_output",
        "copied_output_payload",
    }

    assert snapshot_cls.__name__.startswith("_")
    assert RetainedFormulaSnapshot is contract_cls
    assert issubclass(snapshot_cls, contract_cls)
    assert issubclass(MultiplierData, contract_cls)
    assert snapshot_fields == expected_snapshot_fields
    assert set(contract_cls.__annotations__) == set(expected_snapshot_fields)
    assert (
        CalculatorBuffAttributeReader._build_formula_snapshot.__annotations__["return"]
        is contract_cls
    )
    for helper in (
        Calculator.RegularMul.cal_crit_rate,
        Calculator.RegularMul.cal_personal_crit_rate,
        Calculator.RegularMul.cal_personal_crit_dmg,
        Calculator.StunMul.cal_imp,
        Calculator.AnomalyMul.cal_am,
        Calculator.AnomalyMul.cal_ap,
    ):
        assert getattr(helper, "__annotations__", {}).get("data") is contract_cls
    assert forbidden_snapshot_fields.isdisjoint(snapshot_fields)
    assert not hasattr(CalculatorBuffAttributeReader(), "read_full_crit_damage")

    fixture = _make_attribute_read_fixture(
        name="完整暴伤读口边界",
        crit_damage=0.5,
        damage_ratio=1.0,
        hit_times=1,
        diff_multiplier=0,
        char_buff_count=1,
        enemy_debuff_count=1,
    )
    aggregation_calls = _patch_buff_aggregation(
        monkeypatch,
        _dynamic_statement_by_attr(
            crit_dmg=0.3,
            field_crit_dmg=0.2,
            received_crit_dmg_bonus=0.4,
        ),
    )

    retained_data = _legacy_multiplier_data(fixture)
    retained_dynamic = cast(Any, retained_data).dynamic
    full_crit_damage = Calculator.RegularMul.cal_crit_dmg(retained_data)
    personal_crit_damage = Calculator.RegularMul.cal_personal_crit_dmg(retained_data)
    reader_personal_crit_damage = CalculatorBuffAttributeReader().read_personal_crit_damage(
        fixture.context
    )

    assert full_crit_damage == pytest.approx(1.4)
    assert personal_crit_damage == pytest.approx(1.0)
    assert reader_personal_crit_damage == pytest.approx(personal_crit_damage)
    assert full_crit_damage - personal_crit_damage == pytest.approx(
        retained_dynamic.received_crit_dmg_bonus
    )
    assert retained_dynamic.received_crit_dmg_bonus == pytest.approx(0.4)
    _assert_aggregation_calls(aggregation_calls, fixture, times=2)


def test_regular_mul_sheer_reader_snapshot_contract_stays_module_local() -> None:
    snapshot_cls = getattr(calculator_module, "_CalculatorRetainedFormulaSnapshot")
    snapshot_fields = [field_info.name for field_info in fields(snapshot_cls)]
    public_reader_methods = {
        name
        for name, value in vars(CalculatorBuffAttributeReader).items()
        if name.startswith("read_") and callable(value)
    }

    assert snapshot_cls.__name__.startswith("_")
    assert snapshot_fields == [
        "static",
        "dynamic",
        "judge_node",
        "enemy_obj",
        "char_level",
    ]
    assert public_reader_methods == {
        "read_anomaly_mastery",
        "read_anomaly_proficiency",
        "read_impact",
        "read_full_crit_rate",
        "read_personal_crit_rate",
        "read_personal_crit_damage",
        "read_pen_ratio",
    }
    assert {
        "read_base_attr",
        "read_base_sheer_atk",
        "read_sheer_atk",
        "read_sheer_dmg_bonus",
    }.isdisjoint(public_reader_methods)


@pytest.mark.parametrize(
    (
        "fixture_kwargs",
        "dynamic_attrs",
        "enemy_stunned",
        "enemy_stun_dmg_take_ratio",
        "sheer_conversion",
        "expected_values",
        "reader_snapshot_supported",
    ),
    [
        pytest.param(
            {
                "name": "直伤矩阵-火属性失衡",
                "atk": 100.0,
                "crit_rate": 0.20,
                "crit_damage": 0.50,
                "damage_ratio": 2.0,
                "hit_times": 2,
                "diff_multiplier": 0,
                "element_type": 1,
                "trigger_buff_level": 1,
                "skill_labels": {"aftershock_attack": 1},
                "enemy_max_def": 500.0,
                "enemy_damage_resistance_attrs": {"FIRE_damage_resistance": 0.20},
                "char_buff_count": 1,
                "enemy_debuff_count": 1,
                "enemy_dot_count": 0,
            },
            {
                "field_atk_percentage": 0.20,
                "atk": 10.0,
                "extra_damage_ratio": 0.10,
                "base_dmg_increase_percentage": 0.50,
                "base_dmg_increase": 5.0,
                "fire_dmg_bonus": 0.30,
                "special_skill_dmg_bonus": 0.25,
                "aftershock_attack_dmg_bonus": 0.15,
                "all_dmg_bonus": 0.10,
                "crit_rate": 0.10,
                "field_crit_rate": 0.05,
                "crit_rate_received_increase": 0.20,
                "crit_dmg": 0.30,
                "field_crit_dmg": 0.10,
                "received_crit_dmg_bonus": 0.40,
                "percentage_def_reduction": 0.20,
                "def_reduction": 50.0,
                "pen_ratio": 0.10,
                "pen_numeric": 20.0,
                "fire_dmg_res_decrease": 0.05,
                "fire_res_pen_increase": 0.07,
                "all_dmg_res_decrease": 0.03,
                "all_res_pen_increase": 0.02,
                "fire_vulnerability": 0.25,
                "all_vulnerability": 0.10,
                "stun_vulnerability_increase": 0.40,
                "stun_vulnerability_increase_all_time": 0.15,
                "special_multiplier_zone": 0.60,
            },
            True,
            0.50,
            None,
            {
                "cal_base_dmg": 219.5,
                "cal_dmg_bonus": 1.80,
                "cal_crit_rate": 0.55,
                "cal_crit_dmg": 1.30,
                "cal_crit_expect": 1.715,
                "cal_personal_crit_dmg": 0.90,
                "cal_defense_mul": 794.0 / (794.0 + 295.0),
                "cal_res_mul": 0.97,
                "cal_dmg_vulnerability": 1.35,
                "cal_stun_vulnerability": 2.05,
                "cal_special_mul": 1.60,
                "cal_sheer_dmg_bonus": 1.0,
            },
            True,
            id="fire-stunned-reader-snapshot",
        ),
        pytest.param(
            {
                "name": "直伤矩阵-贯穿 retained only",
                "atk": 100.0,
                "hp": 200.0,
                "defense": 300.0,
                "ap": 400.0,
                "damage_ratio": 1.5,
                "hit_times": 1,
                "diff_multiplier": 4,
                "element_type": 4,
                "trigger_buff_level": 10,
                "enemy_max_def": 500.0,
                "enemy_damage_resistance_attrs": {"ETHER_damage_resistance": 0.10},
                "char_buff_count": 1,
                "enemy_debuff_count": 1,
                "enemy_dot_count": 0,
            },
            {
                "field_atk_percentage": 0.10,
                "atk": 10.0,
                "field_hp_percentage": 0.20,
                "hp": 20.0,
                "field_def_percentage": 0.30,
                "defense": 30.0,
                "field_anomaly_proficiency": 0.40,
                "anomaly_proficiency": 40.0,
                "ether_dmg_bonus": 0.20,
                "all_dmg_bonus": 0.10,
                "ether_dmg_res_decrease": 0.03,
                "ether_res_pen_increase": 0.02,
                "all_dmg_res_decrease": 0.01,
                "all_res_pen_increase": 0.04,
                "ether_vulnerability": 0.20,
                "all_vulnerability": 0.05,
                "stun_vulnerability_increase": 0.40,
                "stun_vulnerability_increase_all_time": 0.15,
                "special_multiplier_zone": 0.20,
                "sheer_atk": 5.0,
                "sheer_dmg_bonus": 0.45,
            },
            False,
            0.50,
            {0: 0.50, 1: 0.10, 2: 0.20, 3: 0.30},
            {
                "cal_base_dmg": 532.5,
                "cal_dmg_bonus": 1.30,
                "cal_crit_rate": 0.0,
                "cal_crit_dmg": 0.0,
                "cal_crit_expect": 1.0,
                "cal_personal_crit_dmg": 0.0,
                "cal_defense_mul": 1.0,
                "cal_res_mul": 1.0,
                "cal_dmg_vulnerability": 1.25,
                "cal_stun_vulnerability": 1.15,
                "cal_special_mul": 1.20,
                "cal_sheer_dmg_bonus": 1.45,
            },
            False,
            id="sheer-retained-only",
        ),
    ],
)
def test_calculator_regular_mul_branch_matrix_characterizes_selected_methods(
    monkeypatch: pytest.MonkeyPatch,
    fixture_kwargs: dict[str, Any],
    dynamic_attrs: dict[str, float],
    enemy_stunned: bool,
    enemy_stun_dmg_take_ratio: float,
    sheer_conversion: dict[int, float] | None,
    expected_values: dict[str, float],
    reader_snapshot_supported: bool,
) -> None:
    fixture = _make_attribute_read_fixture(**fixture_kwargs)
    fixture.enemy.dynamic.stun = enemy_stunned
    fixture.enemy.stun_DMG_take_ratio = enemy_stun_dmg_take_ratio
    if sheer_conversion is not None:
        fixture.char.sheer_attack_conversion_rate = sheer_conversion
    aggregation_calls = _patch_buff_aggregation(
        monkeypatch,
        _dynamic_statement_by_attr(**dynamic_attrs),
    )

    retained_data = _legacy_multiplier_data(fixture)
    assert _regular_mul_branch_matrix_values(retained_data) == pytest.approx(expected_values)

    if reader_snapshot_supported:
        assert _regular_mul_branch_matrix_values(
            _reader_snapshot_data(fixture.context)
        ) == pytest.approx(expected_values)

    _assert_aggregation_calls(
        aggregation_calls,
        fixture,
        times=2 if reader_snapshot_supported else 1,
    )


def test_regular_mul_retained_sheer_base_attr_requires_char_instance_conversion_rate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _make_attribute_read_fixture(
        name="直伤矩阵-贯穿 retained only",
        atk=100.0,
        hp=200.0,
        defense=300.0,
        ap=400.0,
        damage_ratio=1.5,
        hit_times=1,
        diff_multiplier=4,
        element_type=4,
        trigger_buff_level=10,
        enemy_max_def=500.0,
        enemy_damage_resistance_attrs={"ETHER_damage_resistance": 0.10},
        char_buff_count=1,
        enemy_debuff_count=1,
        enemy_dot_count=0,
    )
    fixture.char.sheer_attack_conversion_rate = {0: 0.50, 1: 0.10, 2: 0.20, 3: 0.30}
    aggregation_calls = _patch_buff_aggregation(
        monkeypatch,
        _dynamic_statement_by_attr(
            field_atk_percentage=0.10,
            atk=10.0,
            field_hp_percentage=0.20,
            hp=20.0,
            field_def_percentage=0.30,
            defense=30.0,
            field_anomaly_proficiency=0.40,
            anomaly_proficiency=40.0,
            sheer_atk=5.0,
            sheer_dmg_bonus=0.45,
        ),
    )

    retained_data = _legacy_multiplier_data(fixture)
    assert _regular_mul_base_attr(retained_data, 4) == pytest.approx(355.0)
    assert Calculator.RegularMul.cal_sheer_dmg_bonus(retained_data) == pytest.approx(1.45)

    reader_snapshot_data = _reader_snapshot_data(fixture.context)
    assert not hasattr(reader_snapshot_data, "char_instance")
    with pytest.raises(AttributeError, match="char_instance"):
        _regular_mul_base_attr(reader_snapshot_data, 4)
    assert Calculator.RegularMul.cal_sheer_dmg_bonus(reader_snapshot_data) == pytest.approx(1.45)

    _assert_aggregation_calls(aggregation_calls, fixture, times=2)


@pytest.mark.parametrize(
    (
        "static_crit_rate",
        "field_crit_rate",
        "flat_crit_rate",
        "received_crit_rate",
        "char_buff_count",
        "enemy_debuff_count",
        "expected_full",
        "expected_personal",
    ),
    [
        pytest.param(0.05, 0.0, 0.0, 0.0, 1, 1, 0.05, 0.05, id="baseline"),
        pytest.param(0.1, 0.2, 0.0, 0.0, 1, 1, 0.3, 0.3, id="field-buff"),
        pytest.param(0.1, 0.0, 0.12, 0.0, 1, 1, 0.22, 0.22, id="flat-buff"),
        pytest.param(
            0.1,
            0.0,
            0.0,
            0.15,
            0,
            1,
            0.25,
            0.1,
            id="received-enemy-debuff",
        ),
        pytest.param(
            0.95,
            0.10,
            0.05,
            0.15,
            1,
            1,
            1.25,
            1.10,
            id="over-one-full-crit-received-boundary",
        ),
        pytest.param(0.2, 0.0, 0.0, 0.0, 0, 0, 0.2, 0.2, id="no-buff"),
    ],
)
def test_p2b_parity_fixture_matches_old_full_and_personal_crit_rate_helpers(
    monkeypatch: pytest.MonkeyPatch,
    static_crit_rate: float,
    field_crit_rate: float,
    flat_crit_rate: float,
    received_crit_rate: float,
    char_buff_count: int,
    enemy_debuff_count: int,
    expected_full: float,
    expected_personal: float,
) -> None:
    MultiplierData.mul_data_cache.clear()
    fixture = _make_attribute_read_fixture(
        name="双暴测试",
        crit_rate=static_crit_rate,
        char_buff_count=char_buff_count,
        enemy_debuff_count=enemy_debuff_count,
    )
    aggregation_calls = _patch_buff_aggregation(
        monkeypatch,
        {
            "局内暴击率": field_crit_rate,
            "固定暴击率": flat_crit_rate,
            "被暴击几率增加": received_crit_rate,
        },
    )

    reader = CalculatorBuffAttributeReader()
    reader_full = reader.read_full_crit_rate(fixture.context)
    reader_personal = reader.read_personal_crit_rate(fixture.context)
    old_full = _legacy_full_crit_rate_oracle(fixture)
    old_personal = _legacy_personal_crit_rate_oracle(fixture)

    assert reader_full == pytest.approx(old_full)
    assert reader_personal == pytest.approx(old_personal)
    assert reader_full == pytest.approx(expected_full)
    assert reader_personal == pytest.approx(expected_personal)
    assert reader_full - reader_personal == pytest.approx(received_crit_rate)
    _assert_aggregation_calls(aggregation_calls, fixture, times=3)


def test_p2b_full_crit_rate_includes_received_bonus_but_personal_excludes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    MultiplierData.mul_data_cache.clear()
    fixture = _make_attribute_read_fixture(
        name="受暴击测试",
        crit_rate=0.2,
        enemy_debuff_count=1,
    )
    aggregation_calls = _patch_buff_aggregation(
        monkeypatch,
        {
            "固定暴击率": 0.1,
            "局内暴击率": 0.05,
            "被暴击几率增加": 0.25,
        },
    )

    reader = CalculatorBuffAttributeReader()
    full_crit_rate = reader.read_full_crit_rate(fixture.context)
    personal_crit_rate = reader.read_personal_crit_rate(fixture.context)

    assert full_crit_rate == pytest.approx(0.6)
    assert personal_crit_rate == pytest.approx(0.35)
    assert full_crit_rate - personal_crit_rate == pytest.approx(0.25)
    _assert_aggregation_calls(aggregation_calls, fixture, times=2)


@pytest.mark.parametrize(
    (
        "static_crit_damage",
        "field_crit_damage",
        "flat_crit_damage",
        "received_crit_damage",
        "char_buff_count",
        "enemy_debuff_count",
        "expected_personal",
    ),
    [
        pytest.param(0.5, 0.0, 0.0, 0.0, 1, 1, 0.5, id="baseline"),
        pytest.param(0.5, 0.4, 0.0, 0.0, 1, 1, 0.9, id="field-buff"),
        pytest.param(0.5, 0.0, 0.3, 0.0, 1, 1, 0.8, id="flat-buff"),
        pytest.param(
            0.5,
            0.0,
            0.0,
            0.2,
            0,
            1,
            0.5,
            id="received-enemy-debuff-excluded",
        ),
        pytest.param(0.75, 0.0, 0.0, 0.0, 0, 0, 0.75, id="no-buff"),
    ],
)
def test_p2b_parity_fixture_matches_old_personal_crit_damage_helper(
    monkeypatch: pytest.MonkeyPatch,
    static_crit_damage: float,
    field_crit_damage: float,
    flat_crit_damage: float,
    received_crit_damage: float,
    char_buff_count: int,
    enemy_debuff_count: int,
    expected_personal: float,
) -> None:
    MultiplierData.mul_data_cache.clear()
    fixture = _make_attribute_read_fixture(
        name="暴伤测试",
        crit_damage=static_crit_damage,
        char_buff_count=char_buff_count,
        enemy_debuff_count=enemy_debuff_count,
    )
    aggregation_calls = _patch_buff_aggregation(
        monkeypatch,
        {
            "局内暴击伤害": field_crit_damage,
            "固定暴击伤害": flat_crit_damage,
            "受暴击伤害增加": received_crit_damage,
        },
    )

    reader_value = CalculatorBuffAttributeReader().read_personal_crit_damage(fixture.context)
    reader_data = _reader_snapshot_data(fixture.context)
    old_value = _legacy_personal_crit_damage_oracle(fixture)

    assert reader_value == pytest.approx(old_value)
    assert reader_value == pytest.approx(expected_personal)
    assert cast(Any, reader_data).dynamic.received_crit_dmg_bonus == pytest.approx(
        received_crit_damage
    )
    _assert_aggregation_calls(aggregation_calls, fixture, times=3)


def test_p2b_personal_crit_damage_excludes_received_crit_damage_bonus(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    MultiplierData.mul_data_cache.clear()
    fixture = _make_attribute_read_fixture(
        name="受暴伤测试",
        crit_damage=0.5,
        enemy_debuff_count=1,
    )
    aggregation_calls = _patch_buff_aggregation(
        monkeypatch,
        {
            "固定暴击伤害": 0.3,
            "局内暴击伤害": 0.2,
            "受暴击伤害增加": 0.4,
        },
    )

    personal_crit_damage = CalculatorBuffAttributeReader().read_personal_crit_damage(
        fixture.context
    )
    reader_data = _reader_snapshot_data(fixture.context)

    assert personal_crit_damage == pytest.approx(1.0)
    assert cast(Any, reader_data).dynamic.received_crit_dmg_bonus == pytest.approx(0.4)
    _assert_aggregation_calls(aggregation_calls, fixture, times=2)


def test_calculator_am_ap_impact_formula_boundaries_remain_retained_compatibility(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    MultiplierData.mul_data_cache.clear()
    fixture = _make_attribute_read_fixture(
        name="AM/AP/冲击力边界测试",
        am=100.0,
        ap=300.0,
        imp=80.0,
        char_buff_count=1,
        enemy_debuff_count=1,
    )
    aggregation_calls = _patch_buff_aggregation(
        monkeypatch,
        {
            "局内异常掌控": 0.2,
            "固定异常掌控": 15.0,
            "局内异常精通": 0.25,
            "固定异常精通": 40.0,
            "局内冲击力%": 0.1,
            "固定冲击力": 9.0,
        },
    )

    retained_data = _legacy_multiplier_data(fixture)
    reader_snapshot_data = _reader_snapshot_data(fixture.context)
    expected_dynamic_fields = {
        "field_anomaly_mastery": 0.2,
        "anomaly_mastery": 15.0,
        "field_anomaly_proficiency": 0.25,
        "anomaly_proficiency": 40.0,
        "field_imp_percentage": 0.1,
        "imp": 9.0,
    }

    assert isinstance(retained_data, MultiplierData)
    assert not isinstance(reader_snapshot_data, MultiplierData)

    for source_label, data in (
        ("retained", retained_data),
        ("reader-snapshot", reader_snapshot_data),
    ):
        assert isinstance(data.dynamic, MultiplierData.DynamicStatement), source_label
        for attr_name, expected_value in expected_dynamic_fields.items():
            assert getattr(data.dynamic, attr_name) == pytest.approx(expected_value), (
                f"{source_label}:{attr_name}"
            )

    retained_formula_values = {
        "cal_am": Calculator.AnomalyMul.cal_am(retained_data),
        "cal_ap": Calculator.AnomalyMul.cal_ap(retained_data),
        "cal_imp": Calculator.StunMul.cal_imp(retained_data),
    }
    reader_snapshot_formula_values = {
        "cal_am": Calculator.AnomalyMul.cal_am(reader_snapshot_data),
        "cal_ap": Calculator.AnomalyMul.cal_ap(reader_snapshot_data),
        "cal_imp": Calculator.StunMul.cal_imp(reader_snapshot_data),
    }
    expected_formula_values = {
        "cal_am": 135.0,
        "cal_ap": 415.0,
        "cal_imp": 97.0,
    }

    reader = CalculatorBuffAttributeReader()
    reader_values = {
        "cal_am": reader.read_anomaly_mastery(fixture.context),
        "cal_ap": reader.read_anomaly_proficiency(fixture.context),
        "cal_imp": reader.read_impact(fixture.context),
    }

    assert retained_formula_values == pytest.approx(expected_formula_values)
    # P2-A/P2-B reader parity 只是兼容性证据，不能作为删除 AM/AP/冲击力公式的依据。
    assert reader_snapshot_formula_values == pytest.approx(retained_formula_values)
    assert reader_values == pytest.approx(retained_formula_values)
    _assert_aggregation_calls(aggregation_calls, fixture, times=5)


def test_calculator_attribute_formula_boundaries_remain_retained_compatibility(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    MultiplierData.mul_data_cache.clear()
    fixture = _make_attribute_read_fixture(
        name="双暴公式边界测试",
        crit_rate=0.2,
        crit_damage=0.5,
        damage_ratio=1.0,
        char_buff_count=1,
        enemy_debuff_count=1,
    )
    aggregation_calls = _patch_buff_aggregation(
        monkeypatch,
        {
            "固定暴击率": 0.1,
            "局内暴击率": 0.05,
            "被暴击几率增加": 0.25,
            "固定暴击伤害": 0.3,
            "局内暴击伤害": 0.2,
            "受暴击伤害增加": 0.4,
        },
    )

    retained_data = _legacy_multiplier_data(fixture)
    retained_dynamic = cast(Any, retained_data).dynamic
    formula_boundaries = {
        "cal_crit_rate": Calculator.RegularMul.cal_crit_rate(retained_data),
        "cal_personal_crit_rate": Calculator.RegularMul.cal_personal_crit_rate(retained_data),
        "cal_crit_dmg": Calculator.RegularMul.cal_crit_dmg(retained_data),
        "cal_personal_crit_dmg": Calculator.RegularMul.cal_personal_crit_dmg(retained_data),
    }
    expected_boundaries = {
        "cal_crit_rate": 0.6,
        "cal_personal_crit_rate": 0.35,
        "cal_crit_dmg": 1.4,
        "cal_personal_crit_dmg": 1.0,
    }

    reader = CalculatorBuffAttributeReader()
    reader_values = {
        "cal_crit_rate": reader.read_full_crit_rate(fixture.context),
        "cal_personal_crit_rate": reader.read_personal_crit_rate(fixture.context),
        "cal_personal_crit_dmg": reader.read_personal_crit_damage(fixture.context),
    }

    assert formula_boundaries == pytest.approx(expected_boundaries)
    # 受暴击字段仍只属于完整双暴公式；个人双暴读口不接收这些字段。
    assert reader_values == pytest.approx({key: formula_boundaries[key] for key in reader_values})
    assert (
        formula_boundaries["cal_crit_rate"] - formula_boundaries["cal_personal_crit_rate"]
    ) == pytest.approx(retained_dynamic.crit_rate_received_increase)
    assert (
        formula_boundaries["cal_crit_dmg"] - formula_boundaries["cal_personal_crit_dmg"]
    ) == pytest.approx(retained_dynamic.received_crit_dmg_bonus)
    assert retained_dynamic.crit_rate_received_increase == pytest.approx(0.25)
    assert retained_dynamic.received_crit_dmg_bonus == pytest.approx(0.4)
    assert formula_boundaries["cal_personal_crit_dmg"] == pytest.approx(
        cast(Any, retained_data).static.crit_damage
        + retained_dynamic.crit_dmg
        + retained_dynamic.field_crit_dmg
    )
    _assert_aggregation_calls(aggregation_calls, fixture, times=4)


def test_anomaly_bar_settlement_and_copied_snapshot_inputs_remain_retained_compatibility() -> None:
    sim_instance = SimpleNamespace(tick=120)
    bar = AnomalyBar(sim_instance=cast(Any, sim_instance), element_type=0)
    first_snapshot = np.array(
        [[100.0, 1.10, 2.0, 60.0, 1.30, 0.0, 0.05, 8.0, 0.10, 1.20, 1.40]],
        dtype=np.float64,
    )
    second_snapshot = np.array(
        [[200.0, 1.40, 3.0, 50.0, 1.60, 0.0, 0.15, 4.0, 0.20, 1.60, 1.80]],
        dtype=np.float64,
    )
    ineffective_snapshot: np.ndarray = np.full((1, 11), 999.0, dtype=np.float64)
    effective_hit = SimpleNamespace(effective_anomlay_buildup=lambda: True)
    ineffective_hit = SimpleNamespace(effective_anomlay_buildup=lambda: False)

    assert len(_ANOMALY_CURRENT_NDARRAY_FIELDS) == first_snapshot.shape[1]

    bar.update_snap_shot(
        (0, np.float64(20.0), first_snapshot),
        cast(Any, effective_hit),
    )
    bar.update_snap_shot(
        (0, np.float64(10.0), second_snapshot),
        cast(Any, effective_hit),
    )
    bar.update_snap_shot(
        (0, np.float64(99.0), ineffective_snapshot),
        cast(Any, ineffective_hit),
    )

    assert bar.current_anomaly == pytest.approx(129.0)
    assert len(cast(list[tuple[Any, ...]], bar.ndarray_box)) == 2

    bar.anomaly_settled()

    expected_snapshot = ((first_snapshot * 20.0) + (second_snapshot * 10.0)) / 30.0
    assert bar.settled is True
    assert bar.current_effective_anomaly == pytest.approx(30.0)
    assert bar.ndarray_box == []
    assert bar.current_ndarray.shape == expected_snapshot.shape
    assert bar.current_ndarray.shape == (1, len(_ANOMALY_CURRENT_NDARRAY_FIELDS))
    np.testing.assert_allclose(bar.current_ndarray, expected_snapshot)
    source_current_ndarray = bar.current_ndarray

    activation = SimpleNamespace(skill=SimpleNamespace(char_obj=SimpleNamespace(NAME="快照角色")))
    copied = NewAnomaly(
        bar,
        active_by=cast(Any, activation),
        sim_instance=cast(Any, SimpleNamespace(tick=121)),
    )

    assert copied.current_ndarray is not source_current_ndarray
    assert copied.current_ndarray.shape == (1, len(_ANOMALY_CURRENT_NDARRAY_FIELDS))
    np.testing.assert_allclose(copied.current_ndarray, expected_snapshot)
    source_current_ndarray[0, 0] = -999.0
    assert copied.current_ndarray[0, 0] == pytest.approx(expected_snapshot[0, 0])
    copied.current_ndarray[0, 1] = -888.0
    assert source_current_ndarray[0, 1] == pytest.approx(expected_snapshot[0, 1])
    assert copied.activated_by is activation
    assert copied.activate_by is activation


def test_anomaly_bar_current_ndarray_reset_deepcopy_and_shallow_copy_matrix() -> None:
    assert _ANOMALY_CURRENT_NDARRAY_FIELDS == (
        "base_dmg",
        "dmg_bonus",
        "anomaly_mastery",
        "virtual_character_level",
        "anomaly_bonus",
        "snapshot_anomaly_crit",
        "snapshot_pen_ratio",
        "snapshot_pen_numeric",
        "snapshot_res_pen",
        "snapshot_impact",
        "snapshot_stun_bonus",
    )

    sim_instance = SimpleNamespace(tick=240)
    source_bar = AnomalyBar(sim_instance=cast(Any, sim_instance), element_type=0)
    source_bar.current_ndarray = _make_anomaly_snapshot(
        (
            321.0,
            1.25,
            4.0,
            60.0,
            1.45,
            777.0,
            0.11,
            16.0,
            0.13,
            1.35,
            1.55,
        )
    )
    source_bar.current_effective_anomaly = np.float64(40.0)
    source_bar.current_anomaly = np.float64(144.0)
    source_bar.ndarray_box = [
        (
            0,
            np.float64(40.0),
            source_bar.current_ndarray.copy(),
        )
    ]
    source_bar.settled = True
    source_bar.anomaly_times = 2
    source_bar.last_active = 80
    source_bar.ready = False
    source_bar.active = True
    source_bar.max_anomaly = 120
    activation = SimpleNamespace(skill=SimpleNamespace(char_obj=SimpleNamespace(NAME="矩阵角色")))
    source_bar.activated_by = cast(Any, activation)

    shallow = AnomalyBar.create_new_from_existing(source_bar)
    assert shallow is not source_bar
    assert shallow.current_ndarray is source_bar.current_ndarray
    assert shallow.current_ndarray.shape == (1, len(_ANOMALY_CURRENT_NDARRAY_FIELDS))
    assert shallow.activated_by is activation
    assert shallow.UUID == source_bar.UUID

    source_snapshot_before_deepcopy = source_bar.current_ndarray.copy()
    deep = copy.deepcopy(source_bar)
    assert deep is not source_bar
    assert deep.sim_instance is sim_instance
    assert deep.current_ndarray is not source_bar.current_ndarray
    assert deep.current_ndarray.shape == (1, len(_ANOMALY_CURRENT_NDARRAY_FIELDS))
    np.testing.assert_allclose(deep.current_ndarray, source_snapshot_before_deepcopy)
    assert deep.activated_by is not None
    assert deep.activated_by is not activation
    assert deep.activated_by.skill is activation.skill
    assert deep.UUID != source_bar.UUID

    source_bar.current_ndarray[0, 0] = -10.0
    assert shallow.current_ndarray[0, 0] == pytest.approx(-10.0)
    assert deep.current_ndarray[0, 0] == pytest.approx(source_snapshot_before_deepcopy[0, 0])
    deep.current_ndarray[0, 1] = -20.0
    assert source_bar.current_ndarray[0, 1] == pytest.approx(source_snapshot_before_deepcopy[0, 1])

    active_change_bar = AnomalyBar(sim_instance=cast(Any, sim_instance), element_type=0)
    active_change_bar.current_ndarray = _make_anomaly_snapshot()
    active_change_bar.current_effective_anomaly = np.float64(22.0)
    active_change_bar.current_anomaly = np.float64(88.0)
    active_change_bar.ndarray_box = [
        (
            0,
            np.float64(22.0),
            active_change_bar.current_ndarray.copy(),
        )
    ]
    active_change_bar.basic_max_duration = 480
    active_change_bar.settled = True
    active_change_snapshot = active_change_bar.current_ndarray
    active_change_snapshot_values = active_change_bar.current_ndarray.copy()
    active_change_box = active_change_bar.ndarray_box
    activation_update = SimpleNamespace(
        skill_tag="101_snapshot_test",
        skill=SimpleNamespace(char_obj=SimpleNamespace(NAME="激活角色")),
    )

    active_change_bar.change_info_cause_active(
        333,
        cast(Any, activation_update),
        cast(Any, {"enemy": []}),
    )

    assert active_change_bar.ready is False
    assert active_change_bar.anomaly_times == 1
    assert active_change_bar.last_active == 333
    assert active_change_bar.active is True
    assert active_change_bar.activated_by is activation_update
    assert active_change_bar.max_duration == 480
    assert active_change_bar.current_ndarray is active_change_snapshot
    np.testing.assert_allclose(
        active_change_bar.current_ndarray,
        active_change_snapshot_values,
    )
    assert active_change_bar.current_effective_anomaly == pytest.approx(22.0)
    assert active_change_bar.current_anomaly == pytest.approx(88.0)
    assert active_change_bar.ndarray_box is active_change_box
    assert active_change_bar.settled is True

    output_reset_bar = AnomalyBar(sim_instance=cast(Any, sim_instance), element_type=0)
    output_reset_bar.current_ndarray = _make_anomaly_snapshot()
    output_reset_bar.current_effective_anomaly = np.float64(30.0)
    output_reset_bar.current_anomaly = np.float64(129.0)
    output_reset_bar.ndarray_box = [
        (
            0,
            np.float64(30.0),
            output_reset_bar.current_ndarray.copy(),
        )
    ]
    output_reset_bar.settled = True

    output_reset_bar.reset_current_info_cause_output()

    assert output_reset_bar.current_ndarray.shape == (1, 1)
    np.testing.assert_allclose(
        output_reset_bar.current_ndarray,
        np.zeros((1, 1), dtype=np.float64),
    )
    assert output_reset_bar.current_effective_anomaly == pytest.approx(0.0)
    assert output_reset_bar.current_anomaly == pytest.approx(0.0)
    assert output_reset_bar.ndarray_box == []
    assert output_reset_bar.settled is False

    full_reset_bar = AnomalyBar(sim_instance=cast(Any, sim_instance), element_type=0)
    full_reset_bar.current_ndarray = _make_anomaly_snapshot()
    full_reset_bar.current_anomaly = np.float64(129.0)
    full_reset_bar.anomaly_times = 5
    full_reset_bar.last_active = 200
    full_reset_bar.ready = False
    full_reset_bar.active = True
    full_reset_bar.max_anomaly = 120
    full_reset_bar.ndarray_box = [
        (
            0,
            np.float64(30.0),
            full_reset_bar.current_ndarray.copy(),
        )
    ]

    full_reset_bar.reset_myself()

    assert full_reset_bar.current_ndarray.shape == (1, 1)
    np.testing.assert_allclose(
        full_reset_bar.current_ndarray,
        np.zeros((1, 1), dtype=np.float64),
    )
    assert full_reset_bar.current_anomaly == pytest.approx(0.0)
    assert full_reset_bar.anomaly_times == 0
    assert full_reset_bar.last_active == 0
    assert full_reset_bar.ready is True
    assert full_reset_bar.active is False
    assert full_reset_bar.max_anomaly is None
    assert full_reset_bar.ndarray_box == []


def test_cal_anomaly_rejects_unsettled_or_bad_snapshot_shape() -> None:
    unsettled_fixture = _make_settled_anomaly_formula_fixture()
    unsettled_fixture.anomaly_bar.settled = False

    with pytest.raises(ValueError, match="尚未结算快照"):
        cal_anomaly_module.CalAnomaly(
            anomaly_obj=unsettled_fixture.anomaly_bar,
            enemy_obj=cast(Any, unsettled_fixture.enemy),
            dynamic_buff=unsettled_fixture.active_buff_view,
            sim_instance=cast(Any, unsettled_fixture.sim_instance),
        )

    bad_shape_fixture = _make_settled_anomaly_formula_fixture(
        snapshot=_make_anomaly_snapshot(
            (100.0, 1.10, 2.0, 60.0, 1.30, 999.0, 0.05, 8.0, 0.10, 1.20)
        )
    )

    with pytest.raises(AssertionError, match="异常伤害快照形状错误"):
        cal_anomaly_module.CalAnomaly(
            anomaly_obj=bad_shape_fixture.anomaly_bar,
            enemy_obj=cast(Any, bad_shape_fixture.enemy),
            dynamic_buff=bad_shape_fixture.active_buff_view,
            sim_instance=cast(Any, bad_shape_fixture.sim_instance),
        )


@pytest.mark.parametrize(
    "case",
    _CAL_ANOMALY_LEVEL_CLAMP_ORACLE_CASES,
    ids=lambda case: case.case_id,
)
def test_cal_anomaly_level_clamp_remains_retained_lookup(
    monkeypatch: pytest.MonkeyPatch,
    case: _CalAnomalyLevelClampOracleCase,
) -> None:
    log_messages: list[str] = []
    monkeypatch.setattr(cal_anomaly_module, "report_to_log", log_messages.append)

    result = cal_anomaly_module.CalAnomaly.cal_k_level(case.input_level)

    assert isinstance(result, np.float64)
    assert result == pytest.approx(case.expected_value)
    assert log_messages == list(case.expected_log_messages)


def test_cal_anomaly_final_multiplier_helper_preserves_order_and_damage_expectation() -> None:
    snapshot = _make_anomaly_snapshot(
        (100.0, 1.10, 2.0, 60.0, 1.30, 999.0, 0.05, 8.0, 0.10, 1.20, 1.40)
    )
    final_multipliers = cal_anomaly_module._assemble_final_multiplier_vector(
        snapshot,
        k_level=np.float64(2.0),
        active_crit=np.float64(1.10),
        def_mul=np.float64(0.5),
        res_mul=np.float64(0.7),
        vulnerability_mul=np.float64(0.9),
        snapshot_impact=np.float64(snapshot[0, 9]),
        snapshot_stun_bonus=np.float64(snapshot[0, 10]),
        stun_vulnerability=np.float64(0.8),
        special_mul=np.float64(1.2),
    )

    expected_multipliers = np.array(
        [
            100.0,
            1.10,
            2.0,
            2.0,
            1.30,
            1.10,
            0.5,
            0.7,
            0.9,
            1.20,
            1.40,
            0.8,
            1.2,
        ],
        dtype=np.float64,
    )
    np.testing.assert_allclose(final_multipliers, expected_multipliers)
    assert final_multipliers.dtype == np.dtype(np.float64)
    assert final_multipliers.shape == (len(_CAL_ANOMALY_FINAL_MULTIPLIER_ORDER),)
    final_multiplier_by_slot = {
        label: final_multipliers[index]
        for index, label in enumerate(_CAL_ANOMALY_FINAL_MULTIPLIER_ORDER)
    }
    assert list(final_multiplier_by_slot) == list(_CAL_ANOMALY_FINAL_MULTIPLIER_ORDER)
    assert final_multiplier_by_slot["snapshot_impact"] == pytest.approx(snapshot[0, 9])
    assert final_multiplier_by_slot["snapshot_stun_bonus"] == pytest.approx(snapshot[0, 10])

    damage = cal_anomaly_module._calculate_anomaly_damage_expectation(
        final_multipliers,
        snapshot_impact=np.float64(snapshot[0, 9]),
        snapshot_stun_bonus=np.float64(snapshot[0, 10]),
        scaling_factor=np.float64(1.25),
    )

    assert isinstance(damage, np.float64)
    assert damage == pytest.approx(
        np.prod(expected_multipliers) / (expected_multipliers[9] * expected_multipliers[10]) * 1.25
    )


@pytest.mark.parametrize(
    "case",
    _ANOMALY_MUL_SNAPSHOT_ORACLE_CASES,
    ids=lambda case: case.case_id,
)
def test_anomaly_mul_snapshot_vector_matches_expected_retained_fields(
    monkeypatch: pytest.MonkeyPatch,
    case: _AnomalyMulSnapshotOracleCase,
) -> None:
    character = _make_character(
        name=case.character_name,
        **case.character_kwargs,
    )
    skill_node = _make_skill_node(
        char_name=case.character_name,
        **case.skill_kwargs,
    )
    enemy = _make_enemy()
    active_buff_view: dict[str, list[object]] = {character.NAME: []}
    aggregation_calls = _patch_buff_aggregation(
        monkeypatch,
        _dynamic_statement_by_attr(**case.dynamic_attrs),
    )

    retained_data = MultiplierData(
        enemy,
        active_buff_view,
        character,
        skill_node,
    )
    anomaly_mul = Calculator.AnomalyMul(retained_data)

    assert aggregation_calls == [
        (
            (),
            skill_node,
            enemy.sim_instance,
            character.NAME,
        )
    ]
    assert anomaly_mul.anomaly_snapshot.shape == (len(_ANOMALY_MUL_SNAPSHOT_FIELDS),)
    np.testing.assert_allclose(
        anomaly_mul.anomaly_snapshot,
        np.array(case.expected_snapshot, dtype=np.float64),
    )
    snapshot_by_field = {
        label: anomaly_mul.anomaly_snapshot[index]
        for index, label in enumerate(_ANOMALY_MUL_SNAPSHOT_FIELDS)
    }
    expected_by_field = {
        label: case.expected_snapshot[index]
        for index, label in enumerate(_ANOMALY_MUL_SNAPSHOT_FIELDS)
    }
    assert snapshot_by_field == pytest.approx(expected_by_field)
    dynamic_inputs = {
        attr_name: getattr(retained_data.dynamic, attr_name) for attr_name in case.dynamic_attrs
    }
    assert dynamic_inputs == pytest.approx(case.dynamic_attrs)

    copied_output_payload = _make_anomaly_snapshot(
        _ANOMALY_SNAPSHOT_ORACLE_CASES[0].snapshot_values
    )
    assert copied_output_payload.shape == (
        1,
        len(_ANOMALY_CURRENT_NDARRAY_FIELDS),
    )
    assert copied_output_payload.shape[1] != anomaly_mul.anomaly_snapshot.shape[0]
    snapshot_before_payload_mutation = anomaly_mul.anomaly_snapshot.copy()
    copied_output_payload[0, 0] = -777.0
    np.testing.assert_allclose(
        anomaly_mul.anomaly_snapshot,
        snapshot_before_payload_mutation,
    )


def test_cal_anomaly_uses_settled_snapshot_mul_data_and_retained_damage_ratios(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    created_mul_data: list[Any] = []
    helper_calls: list[tuple[Any, ...]] = []

    class _MulDataProbe:
        def __init__(
            self,
            *,
            enemy_obj: object,
            dynamic_buff: object,
            judge_node: object,
            character_obj: object,
        ) -> None:
            self.enemy_obj = enemy_obj
            self.dynamic_buff = dynamic_buff
            self.judge_node = judge_node
            self.character_obj = character_obj
            self.dynamic = SimpleNamespace(
                strike_crit_rate_increase=0.25,
                strike_crit_dmg_increase=0.4,
            )
            created_mul_data.append(self)

    def _cal_def_mul_probe(self: object, data: object, v_char_level: int) -> np.float64:
        helper_calls.append(("cal_def_mul", data, v_char_level))
        return np.float64(0.5)

    def _cal_res_mul_probe(
        data: object, *, element_type: object, snapshot_res_pen: object
    ) -> np.float64:
        helper_calls.append(("cal_res_mul", data, element_type, snapshot_res_pen))
        return np.float64(0.7)

    def _cal_dmg_vulnerability_probe(data: object, *, element_type: object) -> np.float64:
        helper_calls.append(("cal_dmg_vulnerability", data, element_type))
        return np.float64(0.9)

    def _cal_stun_vulnerability_probe(data: object) -> np.float64:
        helper_calls.append(("cal_stun_vulnerability", data))
        return np.float64(0.8)

    def _cal_special_mul_probe(data: object) -> np.float64:
        helper_calls.append(("cal_special_mul", data))
        return np.float64(1.2)

    monkeypatch.setattr(cal_anomaly_module, "MulData", _MulDataProbe)
    monkeypatch.setattr(
        cal_anomaly_module.CalAnomaly,
        "cal_def_mul",
        _cal_def_mul_probe,
    )
    monkeypatch.setattr(
        cal_anomaly_module.Cal.RegularMul,
        "cal_res_mul",
        staticmethod(_cal_res_mul_probe),
    )
    monkeypatch.setattr(
        cal_anomaly_module.Cal.RegularMul,
        "cal_dmg_vulnerability",
        staticmethod(_cal_dmg_vulnerability_probe),
    )
    monkeypatch.setattr(
        cal_anomaly_module.Cal.RegularMul,
        "cal_stun_vulnerability",
        staticmethod(_cal_stun_vulnerability_probe),
    )
    monkeypatch.setattr(
        cal_anomaly_module.Cal.RegularMul,
        "cal_special_mul",
        staticmethod(_cal_special_mul_probe),
    )

    anomaly_fixture = _make_settled_anomaly_formula_fixture(
        snapshot=_make_anomaly_snapshot(
            (
                100.0,
                1.10,
                2.0,
                59.99999995,
                1.30,
                999.0,
                0.05,
                8.0,
                0.10,
                1.20,
                1.40,
            )
        )
    )
    sim_instance = anomaly_fixture.sim_instance
    character = anomaly_fixture.character
    activation = anomaly_fixture.activation
    enemy = anomaly_fixture.enemy
    enemy_debuffs = (object(), object())
    enemy_dots = (object(),)
    enemy.dynamic.dynamic_debuff_list = list(enemy_debuffs)
    enemy.dynamic.dynamic_dot_list = list(enemy_dots)
    active_buff_view = anomaly_fixture.active_buff_view
    anomaly_bar = anomaly_fixture.anomaly_bar
    settled_snapshot = anomaly_bar.current_ndarray

    calculator = cal_anomaly_module.CalAnomaly(
        anomaly_obj=anomaly_bar,
        enemy_obj=cast(Any, enemy),
        dynamic_buff=active_buff_view,
        sim_instance=cast(Any, sim_instance),
    )

    expected_multipliers = np.array(
        [
            100.0,
            1.10,
            2.0,
            2.0,
            1.30,
            1.10,
            0.5,
            0.7,
            0.9,
            1.20,
            1.40,
            0.8,
            1.2,
        ],
        dtype=np.float64,
    )
    assert len(created_mul_data) == 1
    assert created_mul_data[0].enemy_obj is enemy
    assert created_mul_data[0].judge_node is anomaly_bar
    assert created_mul_data[0].dynamic_buff is active_buff_view
    assert created_mul_data[0].character_obj is character
    assert tuple(created_mul_data[0].enemy_obj.dynamic.dynamic_debuff_list) == enemy_debuffs
    assert tuple(created_mul_data[0].enemy_obj.dynamic.dynamic_dot_list) == enemy_dots
    assert calculator.v_char_level == 60
    assert calculator.dmg_sp is anomaly_bar.current_ndarray
    assert calculator.dmg_sp.shape == (1, 11)
    assert [call[0] for call in helper_calls] == [
        "cal_def_mul",
        "cal_res_mul",
        "cal_dmg_vulnerability",
        "cal_stun_vulnerability",
        "cal_special_mul",
    ]
    assert helper_calls[0][1] is created_mul_data[0]
    assert helper_calls[0][2] == 60
    assert helper_calls[1][1] is created_mul_data[0]
    assert helper_calls[1][2] == anomaly_bar.element_type
    assert helper_calls[1][3] == pytest.approx(settled_snapshot[0, 8])
    assert helper_calls[2][1] is created_mul_data[0]
    assert helper_calls[2][2] == anomaly_bar.element_type
    assert helper_calls[3][1] is created_mul_data[0]
    assert helper_calls[4][1] is created_mul_data[0]
    np.testing.assert_allclose(calculator.final_multipliers, expected_multipliers)
    assert calculator.cal_anomaly_dmg() == pytest.approx(
        np.prod(expected_multipliers)
        / (settled_snapshot[0, 9] * settled_snapshot[0, 10])
        * anomaly_bar.scaling_factor
    )

    abloom = DirgeOfDestinyAnomaly(
        anomaly_bar,
        active_by=cast(Any, activation),
        sim_instance=cast(Any, sim_instance),
    )
    abloom.anomaly_dmg_ratio = 1.3
    abloom.scaling_factor = 1.0
    created_mul_data.clear()

    abloom_calculator = cal_anomaly_module.CalAbloom(
        abloom_obj=abloom,
        enemy_obj=cast(Any, enemy),
        dynamic_buff=active_buff_view,
        sim_instance=cast(Any, sim_instance),
    )

    expected_abloom_multipliers = expected_multipliers.copy()
    expected_abloom_multipliers[0] *= abloom.anomaly_dmg_ratio
    assert len(created_mul_data) == 1
    assert created_mul_data[0].judge_node is abloom
    assert abloom_calculator.dmg_sp is abloom.current_ndarray
    np.testing.assert_allclose(
        abloom_calculator.final_multipliers,
        expected_abloom_multipliers,
    )


@pytest.mark.parametrize(
    "case",
    _CAL_ANOMALY_MULTIPLIER_ORACLE_CASES,
    ids=lambda case: case.case_id,
)
def test_cal_anomaly_multiplier_inputs_remain_retained_mul_data_snapshot(
    monkeypatch: pytest.MonkeyPatch,
    case: _CalAnomalyMultiplierOracleCase,
) -> None:
    fixture = _make_settled_anomaly_formula_fixture(
        element_type=case.element_type,
        snapshot=_make_anomaly_snapshot(case.snapshot_values),
        scaling_factor=case.scaling_factor,
    )
    fixture.enemy.max_DEF = case.enemy_max_def
    for attr_name, value in case.enemy_damage_resistance_attrs.items():
        setattr(fixture.enemy, attr_name, value)
    fixture.enemy.dynamic.stun = case.enemy_stunned
    fixture.enemy.stun_DMG_take_ratio = case.enemy_stun_ratio
    aggregation_calls = _patch_buff_aggregation(
        monkeypatch,
        _dynamic_statement_by_attr(**case.dynamic_attrs),
    )

    calculator = cal_anomaly_module.CalAnomaly(
        anomaly_obj=fixture.anomaly_bar,
        enemy_obj=cast(Any, fixture.enemy),
        dynamic_buff=fixture.active_buff_view,
        sim_instance=cast(Any, fixture.sim_instance),
    )

    assert isinstance(calculator.data, MultiplierData)
    assert calculator.data.judge_node is fixture.anomaly_bar
    assert calculator.data.char_instance is fixture.character
    assert calculator.dmg_sp is fixture.anomaly_bar.current_ndarray
    assert aggregation_calls == [
        (
            (),
            fixture.anomaly_bar,
            fixture.enemy.sim_instance,
            fixture.character.NAME,
        )
    ]
    snapshot_inputs = {
        "virtual_character_level": calculator.dmg_sp[0, 3],
        "snapshot_pen_ratio": calculator.dmg_sp[0, 6],
        "snapshot_pen_numeric": calculator.dmg_sp[0, 7],
        "snapshot_res_pen": calculator.dmg_sp[0, 8],
        "snapshot_impact": calculator.dmg_sp[0, 9],
        "snapshot_stun_bonus": calculator.dmg_sp[0, 10],
    }
    dynamic_inputs = {
        attr_name: getattr(calculator.data.dynamic, attr_name)
        for attr_name in case.expected_dynamic_fields
    }

    assert snapshot_inputs == pytest.approx(case.expected_snapshot_fields)
    assert dynamic_inputs == pytest.approx(case.expected_dynamic_fields)
    assert calculator.v_char_level == int(case.expected_snapshot_fields["virtual_character_level"])
    np.testing.assert_allclose(
        calculator.final_multipliers,
        np.array(case.expected_final_multipliers, dtype=np.float64),
    )
    assert len(calculator.final_multipliers) == len(_CAL_ANOMALY_FINAL_MULTIPLIER_ORDER)
    final_multiplier_by_slot = {
        label: calculator.final_multipliers[index]
        for index, label in enumerate(_CAL_ANOMALY_FINAL_MULTIPLIER_ORDER)
    }
    expected_final_multiplier_by_slot = {
        label: case.expected_final_multipliers[index]
        for index, label in enumerate(_CAL_ANOMALY_FINAL_MULTIPLIER_ORDER)
    }
    assert final_multiplier_by_slot == pytest.approx(expected_final_multiplier_by_slot)
    assert final_multiplier_by_slot["snapshot_impact"] == pytest.approx(
        case.expected_snapshot_fields["snapshot_impact"]
    )
    assert final_multiplier_by_slot["snapshot_stun_bonus"] == pytest.approx(
        case.expected_snapshot_fields["snapshot_stun_bonus"]
    )
    product_with_snapshot_impact_and_stun = np.prod(case.expected_final_multipliers)
    unscaled_damage = product_with_snapshot_impact_and_stun / (
        final_multiplier_by_slot["snapshot_impact"]
        * final_multiplier_by_slot["snapshot_stun_bonus"]
    )
    assert fixture.anomaly_bar.scaling_factor == pytest.approx(case.scaling_factor)
    assert calculator.cal_anomaly_dmg() == pytest.approx(unscaled_damage * case.scaling_factor)


@pytest.mark.parametrize(
    "case",
    _CAL_ABLOOM_ORACLE_CASES,
    ids=lambda case: case.case_id,
)
def test_cal_abloom_formula_inputs_and_fixture_blockers(
    monkeypatch: pytest.MonkeyPatch,
    case: _CalAbloomOracleCase,
) -> None:
    _reset_formula_oracle_caches()
    base_case = case.base_case
    fixture = _make_settled_anomaly_formula_fixture(
        element_type=base_case.element_type,
        snapshot=_make_anomaly_snapshot(base_case.snapshot_values),
        scaling_factor=base_case.scaling_factor,
    )
    fixture.enemy.max_DEF = base_case.enemy_max_def
    for attr_name, value in base_case.enemy_damage_resistance_attrs.items():
        setattr(fixture.enemy, attr_name, value)
    fixture.enemy.dynamic.stun = base_case.enemy_stunned
    fixture.enemy.stun_DMG_take_ratio = base_case.enemy_stun_ratio
    aggregation_calls = _patch_buff_aggregation(
        monkeypatch,
        _dynamic_statement_by_attr(**base_case.dynamic_attrs),
    )

    abloom_payload = DirgeOfDestinyAnomaly(
        fixture.anomaly_bar,
        active_by=cast(Any, fixture.activation),
        sim_instance=cast(Any, fixture.sim_instance),
    )
    abloom_payload.anomaly_dmg_ratio = case.anomaly_dmg_ratio
    for attr_name, value in case.copied_payload_sentinel_fields.items():
        setattr(abloom_payload, attr_name, value)

    original_apply_abloom_ratio = cal_anomaly_module._apply_abloom_anomaly_damage_ratio
    helper_calls: list[tuple[np.ndarray, float, float]] = []

    def _spy_apply_abloom_ratio(
        final_multipliers: np.ndarray,
        *,
        anomaly_dmg_ratio: float | np.float64,
    ) -> np.ndarray:
        helper_calls.append(
            (
                final_multipliers,
                float(final_multipliers[0]),
                float(anomaly_dmg_ratio),
            )
        )
        return original_apply_abloom_ratio(
            final_multipliers,
            anomaly_dmg_ratio=anomaly_dmg_ratio,
        )

    monkeypatch.setattr(
        cal_anomaly_module,
        "_apply_abloom_anomaly_damage_ratio",
        _spy_apply_abloom_ratio,
    )

    calculator = cal_anomaly_module.CalAbloom(
        abloom_obj=abloom_payload,
        enemy_obj=cast(Any, fixture.enemy),
        dynamic_buff=fixture.active_buff_view,
        sim_instance=cast(Any, fixture.sim_instance),
    )

    assert len(helper_calls) == 1
    helper_vector, helper_base_multiplier, helper_ratio = helper_calls[0]
    assert helper_vector is calculator.final_multipliers
    assert helper_base_multiplier == pytest.approx(base_case.expected_final_multipliers[0])
    assert helper_ratio == pytest.approx(case.anomaly_dmg_ratio)
    assert abloom_payload.current_ndarray is not fixture.anomaly_bar.current_ndarray
    np.testing.assert_allclose(
        abloom_payload.current_ndarray,
        fixture.anomaly_bar.current_ndarray,
    )
    assert abloom_payload.activated_by is fixture.activation
    assert calculator.dmg_sp is abloom_payload.current_ndarray
    assert calculator.data.judge_node is abloom_payload
    assert aggregation_calls == [
        (
            (),
            abloom_payload,
            fixture.enemy.sim_instance,
            fixture.character.NAME,
        )
    ]
    for attr_name, value in case.copied_payload_sentinel_fields.items():
        assert getattr(abloom_payload, attr_name) == value
    assert tuple(case.copied_payload_sentinel_fields) == case.fixture_blocker_fields

    snapshot_inputs = {
        "virtual_character_level": calculator.dmg_sp[0, 3],
        "snapshot_pen_ratio": calculator.dmg_sp[0, 6],
        "snapshot_pen_numeric": calculator.dmg_sp[0, 7],
        "snapshot_res_pen": calculator.dmg_sp[0, 8],
        "snapshot_impact": calculator.dmg_sp[0, 9],
        "snapshot_stun_bonus": calculator.dmg_sp[0, 10],
    }
    dynamic_inputs = {
        attr_name: getattr(calculator.data.dynamic, attr_name)
        for attr_name in base_case.expected_dynamic_fields
    }
    deterministic_fields = {
        "source_base_snapshot": fixture.anomaly_bar.current_ndarray[0, 0],
        "anomaly_dmg_ratio": abloom_payload.anomaly_dmg_ratio,
        "abloom_base_multiplier": calculator.final_multipliers[0],
        "scaling_factor": abloom_payload.scaling_factor,
        "snapshot_impact": calculator.final_multipliers[9],
        "snapshot_stun_bonus": calculator.final_multipliers[10],
        "cal_anomaly_dmg": calculator.cal_anomaly_dmg(),
    }
    formula_expectation_fields = (
        set(snapshot_inputs) | set(dynamic_inputs) | set(deterministic_fields)
    )

    assert snapshot_inputs == pytest.approx(base_case.expected_snapshot_fields)
    assert dynamic_inputs == pytest.approx(base_case.expected_dynamic_fields)
    assert deterministic_fields == pytest.approx(case.expected_deterministic_fields)
    assert set(case.copied_payload_sentinel_fields).isdisjoint(formula_expectation_fields)
    np.testing.assert_allclose(
        calculator.final_multipliers,
        np.array(case.expected_final_multipliers, dtype=np.float64),
    )


@pytest.mark.parametrize(
    "case",
    _CAL_DISORDER_ORACLE_CASES,
    ids=lambda case: case.case_id,
)
def test_cal_disorder_formula_inputs_remain_separate_from_copied_payload(
    monkeypatch: pytest.MonkeyPatch,
    case: _CalDisorderOracleCase,
) -> None:
    _reset_formula_oracle_caches()
    fixture = _make_settled_anomaly_formula_fixture(
        element_type=case.element_type,
        snapshot=_make_anomaly_snapshot(case.snapshot_values),
        scaling_factor=case.scaling_factor,
    )
    fixture.sim_instance.tick = case.runtime_tick
    fixture.anomaly_bar.max_duration = case.max_duration
    fixture.anomaly_bar.last_active = case.last_active
    fixture.enemy.dynamic.stun = False
    fixture.enemy.stun_resistance_dict[case.element_type] = case.enemy_stun_resistance
    aggregation_calls = _patch_buff_aggregation(
        monkeypatch,
        _dynamic_statement_by_attr(**case.dynamic_attrs),
    )

    disorder_payload = Disorder(
        fixture.anomaly_bar,
        active_by=cast(Any, fixture.activation),
        sim_instance=cast(Any, fixture.sim_instance),
    )
    for attr_name, value in case.payload_fields.items():
        setattr(disorder_payload, attr_name, value)

    calculator = cal_anomaly_module.CalDisorder(
        disorder_obj=disorder_payload,
        enemy_obj=cast(Any, fixture.enemy),
        dynamic_buff=fixture.active_buff_view,
        sim_instance=cast(Any, fixture.sim_instance),
    )

    assert disorder_payload.is_disorder is True
    assert disorder_payload.current_ndarray is not fixture.anomaly_bar.current_ndarray
    assert disorder_payload.remaining_tick() == pytest.approx(case.expected_remaining_tick)
    for attr_name, value in case.payload_fields.items():
        assert getattr(disorder_payload, attr_name) == value
    assert calculator.dmg_sp is disorder_payload.current_ndarray
    assert calculator.data.judge_node is disorder_payload
    assert aggregation_calls == [
        (
            (),
            disorder_payload,
            fixture.enemy.sim_instance,
            fixture.character.NAME,
        )
    ]
    dynamic_inputs = {
        attr_name: getattr(calculator.data.dynamic, attr_name)
        for attr_name in case.expected_dynamic_fields
    }
    assert dynamic_inputs == pytest.approx(case.expected_dynamic_fields)
    np.testing.assert_allclose(
        calculator.final_multipliers,
        np.array(case.expected_final_multipliers, dtype=np.float64),
    )
    assert calculator.cal_disorder_base_dmg(np.float64(case.snapshot_values[0])) == pytest.approx(
        case.expected_final_multipliers[0]
    )
    assert cal_anomaly_module._calculate_disorder_base_damage(
        element_type=case.element_type,
        base_mul=np.float64(case.snapshot_values[0]),
        remaining_tick=disorder_payload.remaining_tick(),
        disorder_basic_mul_map=calculator.data.dynamic.disorder_basic_mul_map,
    ) == pytest.approx(case.expected_final_multipliers[0])
    assert calculator.cal_disorder_extra_mul() == pytest.approx(case.expected_final_multipliers[4])
    assert cal_anomaly_module._calculate_disorder_extra_multiplier(
        calculator.data.dynamic.ano_extra_bonus
    ) == pytest.approx(case.expected_final_multipliers[4])
    assert calculator.cal_disorder_stun() == pytest.approx(case.expected_disorder_stun)
    assert cal_anomaly_module._calculate_disorder_stun_multiplier(
        impact=np.float64(calculator.final_multipliers[9]),
        snapshot_stun_bonus=np.float64(calculator.final_multipliers[10]),
        stun_res=Calculator.StunMul.cal_stun_res(calculator.data, calculator.element_type),
        received_stun_increase=Calculator.StunMul.cal_stun_received(calculator.data),
        v_char_level=calculator.v_char_level,
    ) == pytest.approx(case.expected_disorder_stun)
    product_with_snapshot_impact_and_stun = np.prod(case.expected_final_multipliers)
    assert calculator.cal_anomaly_dmg() == pytest.approx(
        product_with_snapshot_impact_and_stun
        / (case.expected_final_multipliers[9] * case.expected_final_multipliers[10])
        * case.scaling_factor
    )


@pytest.mark.parametrize(
    "case",
    _CAL_POLARITY_DISORDER_ORACLE_CASES,
    ids=lambda case: case.case_id,
)
def test_cal_polarity_disorder_formula_inputs_and_payload_boundary(
    monkeypatch: pytest.MonkeyPatch,
    case: _CalPolarityDisorderOracleCase,
) -> None:
    _reset_formula_oracle_caches()
    base_case = case.base_case
    fixture = _make_settled_anomaly_formula_fixture(
        element_type=base_case.element_type,
        snapshot=_make_anomaly_snapshot(base_case.snapshot_values),
        scaling_factor=base_case.scaling_factor,
    )
    fixture.sim_instance.tick = base_case.runtime_tick
    fixture.anomaly_bar.max_duration = base_case.max_duration
    fixture.anomaly_bar.last_active = base_case.last_active
    fixture.enemy.dynamic.stun = False
    fixture.enemy.stun_resistance_dict[base_case.element_type] = base_case.enemy_stun_resistance
    aggregation_calls = _patch_buff_aggregation(
        monkeypatch,
        _dynamic_statement_by_attr(**case.dynamic_attrs),
    )

    class _YanagiFormulaProbe(SimpleNamespace):
        pass

    monkeypatch.setattr(cal_anomaly_module, "Yanagi", _YanagiFormulaProbe)
    yanagi_statement = _make_character(name="柳", ap=case.yanagi_static_ap).statement
    yanagi = _YanagiFormulaProbe(
        NAME="柳",
        CID=1221,
        level=60,
        statement=yanagi_statement,
    )
    fixture.sim_instance.char_data = SimpleNamespace(char_obj_dict={"柳": yanagi})
    fixture.active_buff_view[yanagi.NAME] = []

    polarity_payload = PolarityDisorder(
        fixture.anomaly_bar,
        case.polarity_disorder_ratio,
        active_by=cast(Any, fixture.activation),
        sim_instance=cast(Any, fixture.sim_instance),
    )
    payload_fields = {
        **base_case.payload_fields,
        "additional_dmg_ap_ratio": case.additional_dmg_ap_ratio,
    }
    for attr_name, value in payload_fields.items():
        setattr(polarity_payload, attr_name, value)

    calculator = cal_anomaly_module.CalPolarityDisorder(
        disorder_obj=polarity_payload,
        enemy_obj=cast(Any, fixture.enemy),
        dynamic_buff=fixture.active_buff_view,
        sim_instance=cast(Any, fixture.sim_instance),
    )

    assert polarity_payload.is_disorder is True
    assert polarity_payload.current_ndarray is not fixture.anomaly_bar.current_ndarray
    assert polarity_payload.remaining_tick() == pytest.approx(base_case.expected_remaining_tick)
    for attr_name, value in payload_fields.items():
        assert getattr(polarity_payload, attr_name) == value
    assert polarity_payload.polarity_disorder_ratio == pytest.approx(case.polarity_disorder_ratio)
    assert polarity_payload.additional_dmg_ap_ratio == pytest.approx(case.additional_dmg_ap_ratio)
    assert calculator.dmg_sp is polarity_payload.current_ndarray
    assert calculator.data.judge_node is polarity_payload
    assert aggregation_calls == [
        (
            (),
            polarity_payload,
            fixture.enemy.sim_instance,
            fixture.character.NAME,
        ),
        (
            (),
            None,
            fixture.enemy.sim_instance,
            yanagi.NAME,
        ),
    ]
    snapshot_inputs = {
        "base_snapshot": calculator.dmg_sp[0, 0],
        "virtual_character_level": calculator.dmg_sp[0, 3],
        "snapshot_impact": calculator.dmg_sp[0, 9],
        "snapshot_stun_bonus": calculator.dmg_sp[0, 10],
    }
    assert snapshot_inputs == pytest.approx(
        {
            "base_snapshot": base_case.snapshot_values[0],
            "virtual_character_level": base_case.snapshot_values[3],
            "snapshot_impact": base_case.snapshot_values[9],
            "snapshot_stun_bonus": base_case.snapshot_values[10],
        }
    )
    dynamic_inputs = {
        attr_name: getattr(calculator.data.dynamic, attr_name)
        for attr_name in case.expected_dynamic_fields
    }
    assert dynamic_inputs == pytest.approx(case.expected_dynamic_fields)
    assert cal_anomaly_module.Cal.AnomalyMul.cal_ap(
        cal_anomaly_module.MulData(
            enemy_obj=cast(Any, fixture.enemy),
            dynamic_buff=fixture.active_buff_view,
            character_obj=yanagi,
        )
    ) == pytest.approx(case.expected_yanagi_ap)
    assert calculator.cal_polarity_disorder_base_dmg(
        np.float64(case.expected_base_disorder_dmg),
        np.float64(case.expected_yanagi_ap),
        polarity_disorder_ratio=case.polarity_disorder_ratio,
        additional_dmg_ap_ratio=case.additional_dmg_ap_ratio,
    ) == pytest.approx(case.expected_final_multipliers[0])
    np.testing.assert_allclose(
        calculator.final_multipliers,
        np.array(case.expected_final_multipliers, dtype=np.float64),
    )
    assert calculator.cal_disorder_base_dmg(
        np.float64(base_case.snapshot_values[0])
    ) == pytest.approx(case.expected_base_disorder_dmg)
    assert calculator.cal_disorder_extra_mul() == pytest.approx(
        base_case.expected_final_multipliers[4]
    )
    assert calculator.cal_anomaly_dmg() == pytest.approx(
        np.prod(case.expected_final_multipliers)
        / (case.expected_final_multipliers[9] * case.expected_final_multipliers[10])
        * base_case.scaling_factor
    )


@pytest.mark.parametrize(
    ("static_am", "field_am", "flat_am", "expected_gate"),
    [
        (80.0, 0.25, 10.0, False),
        (100.0, 0.10, 5.0, True),
        (116.0, 0.0, 0.0, True),
    ],
)
def test_branch_blade_song_gate_uses_attribute_reader_with_old_helper_parity(
    monkeypatch: pytest.MonkeyPatch,
    static_am: float,
    field_am: float,
    flat_am: float,
    expected_gate: bool,
) -> None:
    MultiplierData.mul_data_cache.clear()
    fixture = _make_attribute_read_fixture(am=static_am)
    aggregation_calls = _patch_buff_aggregation(
        monkeypatch,
        {
            "局内异常掌控": field_am,
            "固定异常掌控": flat_am,
        },
    )

    logic = cast(
        Any,
        BranchBladeSongCritDamageBonus.__new__(BranchBladeSongCritDamageBonus),
    )
    logic.buff_instance = SimpleNamespace(sim_instance=fixture.enemy.sim_instance)
    logic.record = SimpleNamespace(
        enemy=fixture.enemy,
        dynamic_buff_list=fixture.active_buff_view,
        char=fixture.char,
    )
    get_prepared_calls: list[dict[str, object]] = []
    logic.check_record_module = lambda: None
    logic.get_prepared = lambda **kwargs: get_prepared_calls.append(kwargs)

    reader_gate = logic.special_judge_logic()
    old_data = MultiplierData(
        cast(Any, fixture.enemy),
        fixture.active_buff_view,
        cast(Any, fixture.char),
    )
    old_gate = Calculator.AnomalyMul.cal_am(old_data) >= 115

    source = inspect.getsource(BranchBladeSongCritDamageBonus.special_judge_logic)
    assert "MultiplierData" not in source
    assert "Mul(" not in source
    assert "create_calculator_runtime_read_context_from_sim_instance" in source
    assert "active_buff_view=self.record.dynamic_buff_list" not in source
    assert "read_anomaly_mastery" in source
    assert reader_gate == old_gate
    assert reader_gate is expected_gate
    assert get_prepared_calls == [{"equipper": "折枝剑歌", "enemy": 1}]
    assert aggregation_calls == [
        (
            fixture.expected_enabled_buff,
            None,
            fixture.enemy.sim_instance,
            fixture.char.NAME,
        ),
        (
            fixture.expected_enabled_buff,
            None,
            fixture.enemy.sim_instance,
            fixture.char.NAME,
        ),
    ]


@pytest.mark.parametrize(
    ("static_ap", "field_ap", "flat_ap", "expected_gate"),
    [
        (240.0, 0.25, 50.0, False),
        (300.0, 0.20, 15.0, True),
        (376.0, 0.0, 0.0, True),
    ],
)
def test_timeweaver_disorder_gate_uses_attribute_reader_with_old_helper_parity(
    monkeypatch: pytest.MonkeyPatch,
    static_ap: float,
    field_ap: float,
    flat_ap: float,
    expected_gate: bool,
) -> None:
    MultiplierData.mul_data_cache.clear()
    fixture = _make_attribute_read_fixture(name="时流贤者", ap=static_ap)
    aggregation_calls = _patch_buff_aggregation(
        monkeypatch,
        {
            "局内异常精通": field_ap,
            "固定异常精通": flat_ap,
        },
    )

    logic = cast(
        Any,
        TimeweaverDisorderDmgMul.__new__(TimeweaverDisorderDmgMul),
    )
    logic.buff_instance = SimpleNamespace(sim_instance=fixture.enemy.sim_instance)
    logic.record = SimpleNamespace(
        enemy=fixture.enemy,
        dynamic_buff_list=fixture.active_buff_view,
        char=fixture.char,
    )
    get_prepared_calls: list[dict[str, object]] = []
    logic.check_record_module = lambda: None
    logic.get_prepared = lambda **kwargs: get_prepared_calls.append(kwargs)

    reader_gate = logic.special_judge_logic()
    old_data = MultiplierData(
        cast(Any, fixture.enemy),
        fixture.active_buff_view,
        cast(Any, fixture.char),
    )
    old_gate = Calculator.AnomalyMul.cal_ap(old_data) >= 375

    source = inspect.getsource(TimeweaverDisorderDmgMul.special_judge_logic)
    assert "MultiplierData" not in source
    assert "Mul(" not in source
    assert "create_calculator_runtime_read_context_from_sim_instance" in source
    assert "active_buff_view=self.record.dynamic_buff_list" not in source
    assert "read_anomaly_proficiency" in source
    assert reader_gate == old_gate
    assert bool(reader_gate) is expected_gate
    assert get_prepared_calls == [{"equipper": "时流贤者", "preload_data": 1, "enemy": 1}]
    assert aggregation_calls == [
        (
            fixture.expected_enabled_buff,
            None,
            fixture.enemy.sim_instance,
            fixture.char.NAME,
        ),
        (
            fixture.expected_enabled_buff,
            None,
            fixture.enemy.sim_instance,
            fixture.char.NAME,
        ),
    ]


def test_lina_pen_ratio_bonus_uses_reader_service_with_old_helper_parity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    MultiplierData.mul_data_cache.clear()
    fixture = _make_attribute_read_fixture(
        name="丽娜",
        static_statement_attrs={"PEN_ratio": 0.10},
    )
    fixture.enemy.sim_instance.tick = 123
    aggregation_calls = _patch_buff_aggregation(
        monkeypatch,
        _dynamic_statement_by_attr(pen_ratio=0.15),
    )

    logic = cast(
        Any,
        LinaCoreSkillPenRatioBonus.__new__(LinaCoreSkillPenRatioBonus),
    )
    sub_exist_buff_dict: dict[str, object] = {"lina": object()}
    buff_0 = SimpleNamespace(
        ft=SimpleNamespace(step=2.0),
        dy=SimpleNamespace(count=20.0),
    )
    simple_start_calls: list[tuple[int, object]] = []
    update_calls: list[object] = []
    buff_instance = SimpleNamespace(
        sim_instance=fixture.enemy.sim_instance,
        ft=SimpleNamespace(maxcount=99.0),
        dy=SimpleNamespace(count=0.0),
    )
    buff_instance.simple_start = lambda tick, sub_exist: simple_start_calls.append(
        (tick, sub_exist)
    )
    buff_instance.update_to_buff_0 = lambda buff_0_arg: update_calls.append(buff_0_arg)
    logic.buff_instance = buff_instance
    logic.buff_0 = buff_0
    logic.record = SimpleNamespace(
        enemy=fixture.enemy,
        char=fixture.char,
        sub_exist_buff_dict=sub_exist_buff_dict,
    )
    get_prepared_calls: list[dict[str, object]] = []
    logic.check_record_module = lambda: None
    logic.get_prepared = lambda **kwargs: get_prepared_calls.append(kwargs)

    logic.special_start_logic()
    retained_pen_ratio = _legacy_pen_ratio_oracle(fixture)

    source = inspect.getsource(LinaCoreSkillPenRatioBonus.special_start_logic)
    assert "MultiplierData" not in source
    assert "Mul(" not in source
    assert "Cal.RegularMul.cal_pen_ratio" not in source
    assert "create_calculator_runtime_read_context_from_sim_instance" in source
    assert "read_pen_ratio" in source
    assert "dynamic_buff_list=1" not in source
    assert retained_pen_ratio == pytest.approx(0.25)
    assert buff_0.dy.count == pytest.approx(18.0)
    assert buff_instance.dy.count == pytest.approx(17.0)
    assert simple_start_calls == [(123, sub_exist_buff_dict)]
    assert update_calls == [buff_0]
    assert get_prepared_calls == [
        {
            "action_stack": 1,
            "char_CID": 1211,
            "enemy": 1,
            "sub_exist_buff_dict": 1,
        }
    ]
    assert aggregation_calls == [
        (
            fixture.expected_enabled_buff,
            None,
            fixture.enemy.sim_instance,
            fixture.char.NAME,
        ),
        (
            fixture.expected_enabled_buff,
            None,
            fixture.enemy.sim_instance,
            fixture.char.NAME,
        ),
    ]
