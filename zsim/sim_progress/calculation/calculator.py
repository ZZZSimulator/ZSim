import json
from collections.abc import Mapping as MappingABC
from dataclasses import dataclass, field
from functools import lru_cache
from typing import TYPE_CHECKING, Any, Callable, Literal, Mapping, Protocol, Sequence

import numpy as np

from zsim.define import CHECK_SKILL_MUL, CHECK_SKILL_MUL_TAG, INVALID_ELEMENT_ERROR, ElementType
from zsim.sim_progress.anomaly_bar.AnomalyBarClass import AnomalyBar
from zsim.sim_progress.calculation.formulas.regular.damage import (
    assemble_regular_damage_multiplier_array,
    calculate_base_damage,
    calculate_crit_expectation,
    calculate_full_crit_damage,
    calculate_full_crit_rate,
    calculate_non_sheer_base_attribute,
    calculate_personal_crit_damage,
    calculate_personal_crit_rate,
    calculate_regular_damage_bonus,
    calculate_regular_damage_product,
    calculate_sheer_base_attribute,
)
from zsim.sim_progress.calculation.identities import (
    AURIC_INK_DAMAGE,
    ELECTRIC_DAMAGE,
    ETHER_DAMAGE,
    FIRE_DAMAGE,
    FROST_DAMAGE,
    ICE_DAMAGE,
    PHYSICAL_DAMAGE,
)
from zsim.sim_progress.calculation.inputs.common import DamageIdentityProfile
from zsim.sim_progress.calculation.inputs.regular import (
    AffinityValueMap,
    DamageVulnerabilityInput,
    DefenseMultiplierInput,
    RegularBaseAttributeInput,
    RegularCritInput,
    RegularDamageBonusInput,
    RegularDamageMultipliers,
    ResistanceMultiplierInput,
    SpecialMultiplierInput,
    StunVulnerabilityInput,
    multiplier_affinity_from_regular_element_type,
)
from zsim.sim_progress.calculation.multipliers.defense import (
    calculate_attacker_level_coefficient,
    calculate_pen_ratio,
    calculate_recipient_defense,
)
from zsim.sim_progress.calculation.multipliers.resistance import (
    calculate_resistance_multiplier,
)
from zsim.sim_progress.calculation.multipliers.special import (
    calculate_sheer_damage_bonus,
    calculate_special_multiplier,
)
from zsim.sim_progress.calculation.multipliers.vulnerability import (
    calculate_damage_vulnerability,
    calculate_stun_vulnerability,
)
from zsim.sim_progress.Character import Character
from zsim.sim_progress.data_struct import cal_buff_total_bonus
from zsim.sim_progress.Enemy import Enemy
from zsim.sim_progress.Preload import SkillNode
from zsim.sim_progress.Report import report_to_log
from zsim.sim_progress.ScheduledEvent.constants import EventConstants

if TYPE_CHECKING:
    from zsim.sim_progress.ScheduledEvent.buff_runtime import BuffRuntimeReadPort
    from zsim.sim_progress.ScheduledEvent.event_handlers.context import EventContext

with open(
    file="./zsim/sim_progress/ScheduledEvent/buff_effect_trans.json",
    mode="r",
    encoding="utf-8-sig",
) as f:
    buff_effect_trans: dict = json.load(f)


@dataclass(frozen=True, slots=True)
class BuffAttributeReadContext:
    """Calculator Buff 属性读取的运行时输入上下文。"""

    enemy: Enemy
    active_buff_view: Mapping[str, Sequence[Any]]
    character: Character | None = None
    query_node: SkillNode | AnomalyBar | None = None
    enemy_debuffs: Sequence[Any] | None = None
    sim_instance: Any | None = None
    char_name: str | None = None

    @property
    def active_buffs_by_beneficiary(self) -> Mapping[str, Sequence[Any]]:
        """按受益者暴露 active Buff 只读视图。"""

        return self.active_buff_view

    @property
    def formula_char_name(self) -> str | None:
        if self.char_name is not None:
            return self.char_name
        if self.character is None:
            return None
        return self.character.NAME

    @property
    def formula_sim_instance(self) -> Any:
        if self.sim_instance is not None:
            return self.sim_instance
        return self.enemy.sim_instance


CalculatorRuntimeReadContext = BuffAttributeReadContext


@dataclass(frozen=True, slots=True)
class CalculatorBuffBonusReadContext:
    """Calculator 在读取面板、能量、喧响值时使用的 Buff 加成聚合输入。

    这个上下文是面向 runtime 的适配层，用于复用带缓存的
    `cal_buff_total_bonus` 辅助函数。它只携带受益者的激活 Buff 快照和公式身份字段，
    保留原辅助函数的缓存键与返回形状，同时不暴露原始 Buff runtime 容器。
    """

    active_buffs: Sequence[Any]
    query_node: SkillNode | AnomalyBar | None = None
    sim_instance: Any | None = None
    char_name: str | None = None


class RetainedFormulaSnapshot:
    """旧版 Calculator 公式辅助函数仍会读取的字段集合。

    迁移期间保留旧公式实现；旧版 `MultiplierData` 对象与读取器持有的快照都会暴露这组字段。
    """

    static: Any
    dynamic: Any
    judge_node: SkillNode | AnomalyBar | None
    enemy_obj: Enemy
    char_level: int | None


@dataclass(frozen=True, slots=True)
class _CalculatorRetainedFormulaSnapshot(RetainedFormulaSnapshot):
    """读取器持有的 DTO，供保留的 Calculator 公式辅助函数使用。"""

    static: Any
    dynamic: Any
    judge_node: SkillNode | AnomalyBar | None
    enemy_obj: Enemy = field(compare=False, hash=False)
    char_level: int | None = None


def create_anomaly_attribute_read_context(
    *,
    enemy: Enemy,
    active_buff_view: Mapping[str, Sequence[Any]],
    character: Character | None = None,
    query_node: SkillNode | AnomalyBar | None = None,
    enemy_debuffs: Sequence[Any] | None = None,
    sim_instance: Any | None = None,
    char_name: str | None = None,
) -> BuffAttributeReadContext:
    """为异常掌控/异常精通读取器构造最小读取上下文。"""

    return BuffAttributeReadContext(
        enemy=enemy,
        active_buff_view=active_buff_view,
        character=character,
        query_node=query_node,
        enemy_debuffs=enemy_debuffs,
        sim_instance=sim_instance,
        char_name=char_name,
    )


def create_calculator_runtime_read_context(
    *,
    runtime_view: "BuffRuntimeReadPort",
    enemy: Enemy,
    character: Character | None = None,
    query_node: SkillNode | AnomalyBar | None = None,
    beneficiary: str | None = None,
    sim_instance: Any | None = None,
) -> CalculatorRuntimeReadContext:
    """从 Buff runtime read port 构造 Calculator 读取上下文。"""

    return CalculatorRuntimeReadContext(
        enemy=enemy,
        active_buff_view=runtime_view.get_active_buff_view(),
        character=character,
        query_node=query_node,
        enemy_debuffs=tuple(runtime_view.get_active_buffs("enemy")),
        sim_instance=sim_instance,
        char_name=beneficiary,
    )


def create_calculator_runtime_read_context_from_event_context(
    *,
    event_context: "EventContext",
    character: Character | None = None,
    query_node: SkillNode | AnomalyBar | None = None,
    beneficiary: str | None = None,
) -> CalculatorRuntimeReadContext:
    """从 EventContext 构造 Calculator 读取上下文，不暴露旧 Buff 容器。"""

    return create_calculator_runtime_read_context(
        runtime_view=event_context.get_buff_runtime_view(),
        enemy=event_context.get_enemy(),
        character=character,
        query_node=query_node,
        beneficiary=beneficiary,
        sim_instance=event_context.get_sim_instance(),
    )


def create_calculator_runtime_read_context_from_sim_instance(
    *,
    sim_instance: Any,
    enemy: Enemy,
    character: Character | None = None,
    query_node: SkillNode | AnomalyBar | None = None,
    beneficiary: str | None = None,
) -> CalculatorRuntimeReadContext:
    """从 Simulator 持有的 Buff runtime state 构造 Calculator 读取上下文。"""

    runtime_state = getattr(sim_instance, "buff_runtime_state", None)
    if runtime_state is None:
        raise AttributeError("sim_instance 必须暴露 buff_runtime_state")
    return create_calculator_runtime_read_context(
        runtime_view=runtime_state.create_read_port(),
        enemy=enemy,
        character=character,
        query_node=query_node,
        beneficiary=beneficiary,
        sim_instance=sim_instance,
    )


def create_calculator_buff_bonus_context(
    *,
    active_buffs: Sequence[Any],
    query_node: SkillNode | AnomalyBar | None = None,
    sim_instance: Any | None = None,
    char_name: str | None = None,
) -> CalculatorBuffBonusReadContext:
    """构造限定作用域的 Calculator 加成上下文，不暴露原始 Buff 容器。"""

    return CalculatorBuffBonusReadContext(
        active_buffs=tuple(active_buffs),
        query_node=query_node,
        sim_instance=sim_instance,
        char_name=char_name,
    )


def create_calculator_buff_bonus_context_from_runtime_view(
    *,
    runtime_view: "BuffRuntimeReadPort",
    beneficiary: str,
    query_node: SkillNode | AnomalyBar | None = None,
    sim_instance: Any | None = None,
) -> CalculatorBuffBonusReadContext:
    """从 Buff runtime 读口构造面板、能量、喧响值加成上下文。"""

    return create_calculator_buff_bonus_context(
        active_buffs=runtime_view.get_active_buffs(beneficiary),
        query_node=query_node,
        sim_instance=sim_instance,
        char_name=beneficiary,
    )


def create_calculator_buff_bonus_context_from_sim_instance(
    *,
    sim_instance: Any,
    beneficiary: str,
    query_node: SkillNode | AnomalyBar | None = None,
) -> CalculatorBuffBonusReadContext:
    """从 Simulator 持有的 runtime state 构造面板、能量、喧响值加成上下文。"""

    runtime_state = getattr(sim_instance, "buff_runtime_state", None)
    if runtime_state is None:
        raise AttributeError("sim_instance 必须暴露 buff_runtime_state")
    return create_calculator_buff_bonus_context_from_runtime_view(
        runtime_view=runtime_state.create_read_port(),
        beneficiary=beneficiary,
        query_node=query_node,
        sim_instance=sim_instance,
    )


def calculate_calculator_buff_total_bonus(
    context: CalculatorBuffBonusReadContext,
) -> dict[str, float]:
    """通过报表与 runtime 共用的辅助函数聚合激活 Buff 加成。

    tuple 转换是缓存约定的一部分：runtime 调用方可能拿到 list 支撑的 Buff 容器，
    但共用辅助函数要求可哈希快照，并把 `judge_obj`、`sim_instance`、`char_name`
    一起纳入缓存键。
    """

    try:
        return cal_buff_total_bonus(
            enabled_buff=tuple(context.active_buffs),
            judge_obj=context.query_node,
            sim_instance=context.sim_instance,
            char_name=context.char_name,
        )
    except TypeError as err:
        raise TypeError(
            f"参数错误！enabled_buff为{type(context.active_buffs)}，node为{type(context.query_node)}"
        ) from err


class BuffAttributeReader(Protocol):
    """高频属性读取接口，避免新读口直接依赖 MultiplierData 快照。"""

    def read_anomaly_mastery(self, context: BuffAttributeReadContext) -> np.float64:
        """读取异常掌控。"""
        ...

    def read_anomaly_proficiency(self, context: BuffAttributeReadContext) -> np.float64:
        """读取异常精通。"""
        ...

    def read_impact(self, context: BuffAttributeReadContext) -> float:
        """读取冲击力。"""
        ...

    def read_full_crit_rate(self, context: BuffAttributeReadContext) -> float:
        """读取完整暴击率，包含受暴击概率增加。"""
        ...

    def read_personal_crit_rate(self, context: BuffAttributeReadContext) -> float:
        """读取个人实时暴击率。"""
        ...

    def read_personal_crit_damage(self, context: BuffAttributeReadContext) -> float:
        """读取个人实时暴击伤害。"""
        ...

    def read_pen_ratio(
        self,
        context: BuffAttributeReadContext,
        *,
        addon_pen_ratio: float = 0.0,
    ) -> float:
        """读取穿透率。"""
        ...


def _legacy_enemy_debuffs(
    enemy_obj: Enemy,
    dynamic_buff: Mapping[str, Sequence[Any]],
) -> Sequence[Any]:
    try:
        return enemy_obj.dynamic.dynamic_debuff_list
    except AttributeError:
        report_to_log("[警告] self.enemy_obj 中找不到动态buff列表", level=4)
        try:
            return dynamic_buff["enemy"]
        except KeyError:
            report_to_log("[警告] dynamic_buff 中依然找不到动态buff列表", level=4)
            return ()


def _calculate_dynamic_statement(
    enemy_obj: Enemy,
    dynamic_buff: Mapping[str, Sequence[Any]],
    character_obj: Character | None,
    node: SkillNode | AnomalyBar | None,
    *,
    enemy_debuffs: Sequence[Any] | None = None,
    sim_instance: Any | None = None,
    char_name: str | None = None,
) -> dict:
    resolved_char_name = char_name
    if resolved_char_name is None and character_obj is not None:
        resolved_char_name = character_obj.NAME
    if resolved_char_name is None:
        char_buff: Sequence[Any] = ()
    else:
        try:
            char_buff = dynamic_buff[resolved_char_name]
        except KeyError:
            char_buff = ()
            report_to_log(f"[警告] 动态Buff列表内没有角色 {resolved_char_name}", level=4)

    if enemy_debuffs is None:
        enemy_buff = _legacy_enemy_debuffs(enemy_obj, dynamic_buff)
    else:
        enemy_buff = enemy_debuffs
    formula_sim_instance = sim_instance if sim_instance is not None else enemy_obj.sim_instance
    enabled_buff = tuple(char_buff) + tuple(enemy_buff)
    try:
        dynamic_statement: dict = cal_buff_total_bonus(
            enabled_buff=enabled_buff,
            judge_obj=node,
            sim_instance=formula_sim_instance,
            char_name=resolved_char_name,
        )
    except TypeError as err:
        raise TypeError(
            f"参数错误！enabled_buff为{type(enabled_buff)}，node为{type(node)}"
        ) from err
    return dynamic_statement


def _calculate_anomaly_mastery(static_statement: Any, dynamic_statement: Any) -> np.float64:
    return np.float64(
        static_statement.am * (1 + dynamic_statement.field_anomaly_mastery)
        + dynamic_statement.anomaly_mastery
    )


def _calculate_anomaly_proficiency(static_statement: Any, dynamic_statement: Any) -> np.float64:
    return np.float64(
        static_statement.ap * (1 + dynamic_statement.field_anomaly_proficiency)
        + dynamic_statement.anomaly_proficiency
    )


def _regular_damage_identity_profile(element_type: ElementType) -> DamageIdentityProfile:
    try:
        affinity = multiplier_affinity_from_regular_element_type(int(element_type))
    except ValueError as err:
        raise ValueError(f"无效的元素类型：{element_type}，必须是 0~6 的整数") from err

    damage_identity_by_element = {
        0: PHYSICAL_DAMAGE,
        1: FIRE_DAMAGE,
        2: ICE_DAMAGE,
        3: ELECTRIC_DAMAGE,
        4: ETHER_DAMAGE,
        5: FROST_DAMAGE,
        6: AURIC_INK_DAMAGE,
    }
    return DamageIdentityProfile(
        damage_identity=damage_identity_by_element[int(element_type)],
        multiplier_affinity=affinity,
    )


def _regular_static_damage_bonus_map(static_statement: Any) -> AffinityValueMap:
    return AffinityValueMap(
        {
            multiplier_affinity_from_regular_element_type(0): static_statement.phy_dmg_bonus,
            multiplier_affinity_from_regular_element_type(1): static_statement.fire_dmg_bonus,
            multiplier_affinity_from_regular_element_type(2): static_statement.ice_dmg_bonus,
            multiplier_affinity_from_regular_element_type(3): static_statement.electric_dmg_bonus,
            multiplier_affinity_from_regular_element_type(4): static_statement.ether_dmg_bonus,
        }
    )


def _regular_dynamic_damage_bonus_map(dynamic_statement: Any) -> AffinityValueMap:
    return AffinityValueMap(
        {
            multiplier_affinity_from_regular_element_type(0): dynamic_statement.phy_dmg_bonus,
            multiplier_affinity_from_regular_element_type(1): dynamic_statement.fire_dmg_bonus,
            multiplier_affinity_from_regular_element_type(2): dynamic_statement.ice_dmg_bonus,
            multiplier_affinity_from_regular_element_type(3): dynamic_statement.electric_dmg_bonus,
            multiplier_affinity_from_regular_element_type(4): dynamic_statement.ether_dmg_bonus,
        }
    )


def _regular_trigger_damage_bonuses(dynamic_statement: Any) -> tuple[float, ...]:
    return (
        dynamic_statement.normal_attack_dmg_bonus,
        dynamic_statement.special_skill_dmg_bonus,
        dynamic_statement.ex_special_skill_dmg_bonus,
        dynamic_statement.dash_attack_dmg_bonus,
        dynamic_statement.counter_attack_dmg_bonus,
        dynamic_statement.qte_dmg_bonus,
        dynamic_statement.ultimate_dmg_bonus,
        dynamic_statement.quick_aid_dmg_bonus,
        dynamic_statement.defensive_aid_dmg_bonus,
        dynamic_statement.assault_aid_dmg_bonus,
    )


def _is_aftershock_attack(judge_node: SkillNode) -> bool:
    return (
        judge_node.skill.labels is not None
        and judge_node.skill.labels.get("aftershock_attack") == 1
    )


def _regular_crit_input(
    static_statement: Any,
    dynamic_statement: Any,
    *,
    aftershock_attack: bool = False,
) -> RegularCritInput:
    return RegularCritInput(
        static_crit_rate=static_statement.crit_rate,
        dynamic_crit_rate=dynamic_statement.crit_rate,
        field_crit_rate=dynamic_statement.field_crit_rate,
        crit_rate_received_increase=dynamic_statement.crit_rate_received_increase,
        static_crit_damage=static_statement.crit_damage,
        dynamic_crit_damage=dynamic_statement.crit_dmg,
        field_crit_damage=dynamic_statement.field_crit_dmg,
        received_crit_damage_bonus=dynamic_statement.received_crit_dmg_bonus,
        aftershock_attack=aftershock_attack,
        aftershock_attack_crit_damage_bonus=dynamic_statement.aftershock_attack_crit_dmg_bonus,
    )


def _regular_base_attribute_input(data: RetainedFormulaSnapshot) -> RegularBaseAttributeInput:
    assert isinstance(data.judge_node, SkillNode), "非法的调用，没有获取到skill node"
    diff_multiplier = data.judge_node.skill.diff_multiplier
    if diff_multiplier not in [0, 1, 2, 3, 4]:
        raise AssertionError(INVALID_ELEMENT_ERROR)
    sheer_attack_conversion_rates: tuple[tuple[int, float], ...] = ()
    if diff_multiplier == 4:
        char_instance = getattr(data, "char_instance", None)
        assert char_instance is not None
        if not hasattr(char_instance, "sheer_attack_conversion_rate"):
            raise AttributeError(
                f"{char_instance.NAME}作为命破属性代理人，必须拥有贯穿力转化字典！"
            )
        assert char_instance.sheer_attack_conversion_rate is not None
        for key in char_instance.sheer_attack_conversion_rate:
            if key not in [0, 1, 2, 3]:
                raise ValueError(f"无法解析的贯穿力转化率key：{key}")
        if data.dynamic.field_sheer_atk_percentage != 0:
            raise ValueError(
                "警告！检测到非0的“局内贯穿力%Buff”，该效果目前还无法处理，请注意检查buff_effect"
            )
        sheer_attack_conversion_rates = tuple(char_instance.sheer_attack_conversion_rate.items())

    return RegularBaseAttributeInput(
        damage_ratio=data.judge_node.skill.damage_ratio,
        hit_times=data.judge_node.hit_times,
        diff_multiplier=diff_multiplier,
        attack=data.static.atk,
        field_attack_percentage=data.dynamic.field_atk_percentage,
        flat_attack=data.dynamic.atk,
        hp=data.static.hp,
        field_hp_percentage=data.dynamic.field_hp_percentage,
        flat_hp=data.dynamic.hp,
        defense=data.static.defense,
        field_defense_percentage=data.dynamic.field_def_percentage,
        flat_defense=data.dynamic.defense,
        anomaly_proficiency=data.static.ap,
        field_anomaly_proficiency=data.dynamic.field_anomaly_proficiency,
        flat_anomaly_proficiency=data.dynamic.anomaly_proficiency,
        extra_damage_ratio=data.dynamic.extra_damage_ratio,
        base_damage_increase_percentage=data.dynamic.base_dmg_increase_percentage,
        base_damage_increase=data.dynamic.base_dmg_increase,
        sheer_attack_conversion_rates=sheer_attack_conversion_rates,
        field_sheer_attack_percentage=data.dynamic.field_sheer_atk_percentage,
        flat_sheer_attack=data.dynamic.sheer_atk,
    )


def _regular_target_resistance_map(enemy_obj: Any) -> AffinityValueMap:
    return AffinityValueMap(
        {
            multiplier_affinity_from_regular_element_type(0): enemy_obj.PHY_damage_resistance,
            multiplier_affinity_from_regular_element_type(1): enemy_obj.FIRE_damage_resistance,
            multiplier_affinity_from_regular_element_type(2): enemy_obj.ICE_damage_resistance,
            multiplier_affinity_from_regular_element_type(3): enemy_obj.ELECTRIC_damage_resistance,
            multiplier_affinity_from_regular_element_type(4): enemy_obj.ETHER_damage_resistance,
        }
    )


def _regular_resistance_decrease_map(dynamic_statement: Any) -> AffinityValueMap:
    return AffinityValueMap(
        {
            multiplier_affinity_from_regular_element_type(
                0
            ): dynamic_statement.physical_dmg_res_decrease,
            multiplier_affinity_from_regular_element_type(
                1
            ): dynamic_statement.fire_dmg_res_decrease,
            multiplier_affinity_from_regular_element_type(
                2
            ): dynamic_statement.ice_dmg_res_decrease,
            multiplier_affinity_from_regular_element_type(
                3
            ): dynamic_statement.electric_dmg_res_decrease,
            multiplier_affinity_from_regular_element_type(
                4
            ): dynamic_statement.ether_dmg_res_decrease,
        }
    )


def _regular_resistance_penetration_map(dynamic_statement: Any) -> AffinityValueMap:
    return AffinityValueMap(
        {
            multiplier_affinity_from_regular_element_type(
                0
            ): dynamic_statement.physical_res_pen_increase,
            multiplier_affinity_from_regular_element_type(
                1
            ): dynamic_statement.fire_res_pen_increase,
            multiplier_affinity_from_regular_element_type(
                2
            ): dynamic_statement.ice_res_pen_increase,
            multiplier_affinity_from_regular_element_type(
                3
            ): dynamic_statement.electric_res_pen_increase,
            multiplier_affinity_from_regular_element_type(
                4
            ): dynamic_statement.ether_res_pen_increase,
        }
    )


def _regular_damage_vulnerability_map(dynamic_statement: Any) -> AffinityValueMap:
    return AffinityValueMap(
        {
            multiplier_affinity_from_regular_element_type(
                0
            ): dynamic_statement.physical_vulnerability,
            multiplier_affinity_from_regular_element_type(1): dynamic_statement.fire_vulnerability,
            multiplier_affinity_from_regular_element_type(2): dynamic_statement.ice_vulnerability,
            multiplier_affinity_from_regular_element_type(
                3
            ): dynamic_statement.electric_vulnerability,
            multiplier_affinity_from_regular_element_type(4): dynamic_statement.ether_vulnerability,
        }
    )


def _calculate_non_sheer_base_attribute(
    base_attr: int, static_statement: Any, dynamic_statement: Any
) -> float:
    if base_attr not in [0, 1, 2, 3]:
        raise AssertionError(INVALID_ELEMENT_ERROR)
    return calculate_non_sheer_base_attribute(
        base_attr,
        attack=static_statement.atk,
        field_attack_percentage=dynamic_statement.field_atk_percentage,
        flat_attack=dynamic_statement.atk,
        hp=static_statement.hp,
        field_hp_percentage=dynamic_statement.field_hp_percentage,
        flat_hp=dynamic_statement.hp,
        defense=static_statement.defense,
        field_defense_percentage=dynamic_statement.field_def_percentage,
        flat_defense=dynamic_statement.defense,
        anomaly_proficiency=static_statement.ap,
        field_anomaly_proficiency=dynamic_statement.field_anomaly_proficiency,
        flat_anomaly_proficiency=dynamic_statement.anomaly_proficiency,
    )


def _calculate_sheer_base_attribute(
    character_obj: Any,
    dynamic_statement: Any,
    base_attribute_reader: Callable[[int], float],
) -> float:
    if not hasattr(character_obj, "sheer_attack_conversion_rate"):
        raise AttributeError(f"{character_obj.NAME}作为命破属性代理人，必须拥有贯穿力转化字典！")
    assert character_obj.sheer_attack_conversion_rate is not None
    for key, value in character_obj.sheer_attack_conversion_rate.items():
        if key not in [0, 1, 2, 3]:
            raise ValueError(f"无法解析的贯穿力转化率key：{key}")
    if dynamic_statement.field_sheer_atk_percentage != 0:
        raise ValueError(
            "警告！检测到非0的“局内贯穿力%Buff”，该效果目前还无法处理，请注意检查buff_effect"
        )
    return calculate_sheer_base_attribute(
        tuple(character_obj.sheer_attack_conversion_rate.items()),
        base_attribute_reader=base_attribute_reader,
        field_sheer_attack_percentage=dynamic_statement.field_sheer_atk_percentage,
        flat_sheer_attack=dynamic_statement.sheer_atk,
    )


def _calculate_base_damage(damage_ratio: float, attr: float, dynamic_statement: Any) -> float:
    return calculate_base_damage(
        damage_ratio,
        attr,
        extra_damage_ratio=dynamic_statement.extra_damage_ratio,
        base_damage_increase_percentage=dynamic_statement.base_dmg_increase_percentage,
        base_damage_increase=dynamic_statement.base_dmg_increase,
    )


def _calculate_impact(static_statement: Any, dynamic_statement: Any) -> float:
    return (
        static_statement.imp * (1 + dynamic_statement.field_imp_percentage) + dynamic_statement.imp
    )


def _calculate_full_crit_rate(static_statement: Any, dynamic_statement: Any) -> float:
    return calculate_full_crit_rate(_regular_crit_input(static_statement, dynamic_statement))


def _calculate_personal_crit_rate(static_statement: Any, dynamic_statement: Any) -> float:
    return calculate_personal_crit_rate(_regular_crit_input(static_statement, dynamic_statement))


def _calculate_personal_crit_damage(static_statement: Any, dynamic_statement: Any) -> float:
    return calculate_personal_crit_damage(_regular_crit_input(static_statement, dynamic_statement))


def _calculate_full_crit_damage(
    static_statement: Any, dynamic_statement: Any, judge_node: SkillNode
) -> float:
    return calculate_full_crit_damage(
        _regular_crit_input(
            static_statement,
            dynamic_statement,
            aftershock_attack=_is_aftershock_attack(judge_node),
        )
    )


def _calculate_crit_expectation(crit_rate: float, crit_damage: float) -> float:
    return calculate_crit_expectation(crit_rate, crit_damage)


def _calculate_damage_bonus(
    static_statement: Any, dynamic_statement: Any, judge_node: SkillNode
) -> float:
    return calculate_regular_damage_bonus(
        RegularDamageBonusInput(
            identity=_regular_damage_identity_profile(judge_node.element_type),
            static_damage_bonuses=_regular_static_damage_bonus_map(static_statement),
            dynamic_damage_bonuses=_regular_dynamic_damage_bonus_map(dynamic_statement),
            trigger_buff_level=judge_node.skill.trigger_buff_level,
            trigger_damage_bonuses=_regular_trigger_damage_bonuses(dynamic_statement),
            all_damage_bonus=dynamic_statement.all_dmg_bonus,
            aftershock_attack=_is_aftershock_attack(judge_node),
            aftershock_attack_damage_bonus=dynamic_statement.aftershock_attack_dmg_bonus,
        )
    )


def _calculate_pen_ratio(
    static_statement: Any,
    dynamic_statement: Any,
    *,
    addon_pen_ratio: float = 0.0,
) -> float:
    return calculate_pen_ratio(
        static_statement.pen_ratio,
        dynamic_statement.pen_ratio,
        addon_pen_ratio=addon_pen_ratio,
    )


def _calculate_recipient_defense(
    enemy_obj: Any,
    static_statement: Any,
    dynamic_statement: Any,
    pen_ratio: float,
    *,
    addon_pen_ratio: float = 0.0,
    addon_pen_numeric: float = 0.0,
) -> float:
    return calculate_recipient_defense(
        enemy_obj.max_DEF,
        dynamic_statement.percentage_def_reduction,
        dynamic_statement.def_reduction,
        static_statement.pen_numeric,
        dynamic_statement.pen_numeric,
        pen_ratio,
        addon_pen_ratio=addon_pen_ratio,
        addon_pen_numeric=addon_pen_numeric,
    )


def _calculate_attacker_level_coefficient(attacker_level: int) -> int:
    # 定义域检查
    if attacker_level < 0:
        report_to_log(f"角色等级{attacker_level}过低，将被设置为0")
        attacker_level = 0
    elif attacker_level > 60:
        report_to_log(f"角色等级{attacker_level}过高，将被设置为60")
        attacker_level = 60
    # 攻击方等级系数
    return calculate_attacker_level_coefficient(attacker_level)


def _calculate_defense_multiplier(
    enemy_obj: Any,
    static_statement: Any,
    dynamic_statement: Any,
    base_attr: int,
    attacker_level: int,
) -> float:
    if base_attr == 4:
        return 1.0
    input_snapshot = DefenseMultiplierInput(
        max_defense=enemy_obj.max_DEF,
        percentage_defense_reduction=dynamic_statement.percentage_def_reduction,
        flat_defense_reduction=dynamic_statement.def_reduction,
        static_pen_ratio=static_statement.pen_ratio,
        dynamic_pen_ratio=dynamic_statement.pen_ratio,
        static_pen_numeric=static_statement.pen_numeric,
        dynamic_pen_numeric=dynamic_statement.pen_numeric,
        base_attribute=base_attr,
        attacker_level=attacker_level,
    )
    k_attacker = _calculate_attacker_level_coefficient(input_snapshot.attacker_level)
    pen_ratio = _calculate_pen_ratio(static_statement, dynamic_statement)
    effective_def = _calculate_recipient_defense(
        enemy_obj,
        static_statement,
        dynamic_statement,
        pen_ratio,
    )
    return k_attacker / (effective_def + k_attacker)


def _calculate_resistance_multiplier(
    enemy_obj: Any,
    dynamic_statement: Any,
    element_type: ElementType,
    *,
    snapshot_res_pen: float = 0,
) -> float:
    try:
        affinity = multiplier_affinity_from_regular_element_type(int(element_type))
    except ValueError as err:
        raise AssertionError(INVALID_ELEMENT_ERROR) from err
    return calculate_resistance_multiplier(
        ResistanceMultiplierInput(
            affinity=affinity,
            target_resistances=_regular_target_resistance_map(enemy_obj),
            damage_resistance_decreases=_regular_resistance_decrease_map(dynamic_statement),
            resistance_penetrations=_regular_resistance_penetration_map(dynamic_statement),
            all_damage_resistance_decrease=dynamic_statement.all_dmg_res_decrease,
            all_resistance_penetration=dynamic_statement.all_res_pen_increase,
            snapshot_resistance_penetration=snapshot_res_pen,
        )
    )


def _calculate_damage_vulnerability(dynamic_statement: Any, element_type: ElementType) -> float:
    try:
        affinity = multiplier_affinity_from_regular_element_type(int(element_type))
    except ValueError as err:
        raise AssertionError(INVALID_ELEMENT_ERROR) from err
    return calculate_damage_vulnerability(
        DamageVulnerabilityInput(
            affinity=affinity,
            damage_vulnerabilities=_regular_damage_vulnerability_map(dynamic_statement),
            all_vulnerability=dynamic_statement.all_vulnerability,
        )
    )


def _calculate_stun_vulnerability(enemy_obj: Any, dynamic_statement: Any) -> float:
    return calculate_stun_vulnerability(
        StunVulnerabilityInput(
            is_stunned=enemy_obj.dynamic.stun,
            stun_damage_taken_ratio=enemy_obj.stun_DMG_take_ratio,
            stun_vulnerability_increase=dynamic_statement.stun_vulnerability_increase,
            stun_vulnerability_increase_all_time=dynamic_statement.stun_vulnerability_increase_all_time,
        )
    )


def _calculate_special_multiplier(dynamic_statement: Any) -> float:
    return calculate_special_multiplier(
        SpecialMultiplierInput(
            special_multiplier_zone=dynamic_statement.special_multiplier_zone,
            diff_multiplier=0,
            sheer_damage_bonus=0.0,
        )
    )


def _calculate_sheer_damage_bonus(judge_node: SkillNode, dynamic_statement: Any) -> float:
    return calculate_sheer_damage_bonus(
        SpecialMultiplierInput(
            special_multiplier_zone=0.0,
            diff_multiplier=judge_node.skill.diff_multiplier,
            sheer_damage_bonus=dynamic_statement.sheer_dmg_bonus,
        )
    )


def _build_stun_multiplier_array(
    imp: float,
    stun_ratio: float,
    stun_res: float,
    stun_bonus: float,
    stun_received: float,
) -> np.ndarray:
    return np.array(
        [
            imp,
            stun_ratio,
            stun_res,
            stun_bonus,
            stun_received,
        ],
        dtype=np.float64,
    )


class MultiplierData(RetainedFormulaSnapshot):
    """
    乘数数据缓存管理类

    使用缓存机制来存储和重用乘数计算结果，提高性能。
    采用 LRU (Least Recently Used) 缓存策略来自动管理缓存大小。
    """

    mul_data_cache: dict[tuple, "MultiplierData"] = {}
    MAX_CACHE_SIZE = EventConstants.MAX_CACHE_SIZE

    def __new__(
        cls,
        enemy_obj: Enemy,
        dynamic_buff: Mapping[str, Sequence[Any]],
        character_obj: Character | None = None,
        judge_node: SkillNode | AnomalyBar | None = None,
    ):
        hashable_dynamic_buff = tuple((key, tuple(value)) for key, value in dynamic_buff.items())
        enemy_hashable = (
            tuple(enemy_obj.dynamic.dynamic_debuff_list),
            tuple(enemy_obj.dynamic.dynamic_dot_list),
        )

        node_id: Any = id(judge_node)
        if isinstance(judge_node, AnomalyBar):
            node_id = judge_node.UUID

        # 使用更稳定的唯一标识符，避免垃圾回收后的问题
        character_id = (
            getattr(character_obj, "UUID", None)
            or getattr(character_obj, "CID", None)
            or f"{character_obj.__class__.__name__}_{id(character_obj)}"
        )
        cache_key = tuple((enemy_hashable, hashable_dynamic_buff, character_id, node_id))
        if cache_key in cls.mul_data_cache:
            return cls.mul_data_cache[cache_key]
        else:
            instance = super().__new__(cls)
            if len(cls.mul_data_cache) >= cls.MAX_CACHE_SIZE:
                cls.mul_data_cache.popitem()
            cls.mul_data_cache[cache_key] = instance
            return instance

    def __init__(
        self,
        enemy_obj: Enemy,
        dynamic_buff: Mapping[str, Sequence[Any]] | None = None,
        character_obj: Character | None = None,
        judge_node: SkillNode | AnomalyBar | None = None,
    ):
        """
        初始化乘数数据实例

        Args:
            enemy_obj: 敌人对象
            dynamic_buff: 动态buff字典
            character_obj: 角色对象
            judge_node: 判断节点（技能节点或异常条）
        """
        if dynamic_buff is None:
            dynamic_buff = {}

        if not hasattr(self, "char_name"):
            self.judge_node: SkillNode | AnomalyBar | None = judge_node
            self.enemy_instance = enemy_obj
            if character_obj is None:
                self.char_name = None
                self.char_level = None
                self.cid = None
                self.char_instance = None
            else:
                self.char_name = character_obj.NAME
                self.char_level = character_obj.level
                self.cid = character_obj.CID
                self.char_instance = character_obj

            # 获取角色局外面板数据
            static_statement: Character.Statement | None = getattr(character_obj, "statement", None)
            self.static = self.StaticStatement(static_statement)

            # 获取敌人数据
            self.enemy_obj = enemy_obj

            # 获取buff动态加成
            dynamic_statement: dict = self.get_buff_bonus(dynamic_buff, self.judge_node)
            self.dynamic = self.DynamicStatement(dynamic_statement)

    def get_buff_bonus(
        self,
        dynamic_buff: Mapping[str, Sequence[Any]],
        node: SkillNode | AnomalyBar | None,
    ) -> dict:
        """
        获取buff加成数据

        Args:
            dynamic_buff: 动态buff字典
            node: 判断节点

        Returns:
            dict: 包含所有buff加成的字典
        """
        return _calculate_dynamic_statement(
            self.enemy_obj,
            dynamic_buff,
            self.char_instance,
            node,
        )

    class StaticStatement:
        _instance_cache: dict[tuple | None, Any] = {}
        _max_cache_size = 128

        def __new__(cls, static_statement: Character.Statement | None):
            if static_statement is None:
                cache_key = None
            else:
                cache_key = tuple(sorted(static_statement.statement.items()))
            if cache_key in cls._instance_cache:
                return cls._instance_cache[cache_key]
            else:
                instance = super().__new__(cls)
                if len(cls._instance_cache) >= cls._max_cache_size:
                    cls._instance_cache.popitem()
                cls._instance_cache[cache_key] = instance
                return instance

        def __init__(self, static_statement: Character.Statement | None):
            """将角色面板抄下来！！！！！如果没有角色传入，那就生成屎！！！"""
            self.atk: float = 0.0
            self.hp: float = 0.0
            self.defense: float = 0.0
            self.imp: float = 0.0
            self.ap: float = 0.0
            self.am: float = 0.0
            self.crit_rate: float = 0.0
            self.crit_damage: float = 0.0
            self.sp_regen: float = 0.0
            self.sp_get_ratio: float = 0.0
            self.sp_limit: float = 0.0
            self.pen_ratio: float = 0.0
            self.pen_numeric: float = 0.0
            self.phy_dmg_bonus: float = 0.0
            self.ice_dmg_bonus: float = 0.0
            self.fire_dmg_bonus: float = 0.0
            self.ether_dmg_bonus: float = 0.0
            self.electric_dmg_bonus: float = 0.0

            attribute_map = {
                "atk": "ATK",
                "hp": "HP",
                "defense": "DEF",
                "imp": "IMP",
                "ap": "AP",
                "am": "AM",
                "crit_rate": "CRIT_rate",
                "crit_damage": "CRIT_damage",
                "sp_regen": "sp_regen",
                "sp_get_ratio": "sp_get_ratio",
                "sp_limit": "sp_limit",
                "pen_ratio": "PEN_ratio",
                "pen_numeric": "PEN_numeric",
                "phy_dmg_bonus": "PHY_DMG_bonus",
                "ice_dmg_bonus": "ICE_DMG_bonus",
                "fire_dmg_bonus": "FIRE_DMG_bonus",
                "ether_dmg_bonus": "ETHER_DMG_bonus",
                "electric_dmg_bonus": "ELECTRIC_DMG_bonus",
            }
            if static_statement is None:
                pass
            else:
                for attr, static_attr in attribute_map.items():
                    setattr(self, attr, getattr(static_statement, static_attr, 0.0))

    class DynamicStatement:
        def __init__(self, dynamic_statement):
            """
            buff动态加成的初始化蟑螂桶，这一百多行不是屎山，是为了IDE能认识这些傻逼玩意
            """
            self.buff_name: float = 0.0
            self.hp: float = 0.0
            self.atk: float = 0.0
            self.defense: float = 0.0
            self.imp: float = 0.0
            self.crit_rate: float = 0.0
            self.crit_dmg: float = 0.0
            self.anomaly_proficiency: float = 0.0
            self.anomaly_mastery: float = 0.0
            self.pen_ratio: float = 0.0
            self.pen_numeric: float = 0.0
            self.sp_regen: float = 0.0
            self.sp_get_ratio: float = 0.0
            self.sp_limit: float = 0.0
            self.phy_dmg_bonus: float = 0.0
            self.fire_dmg_bonus: float = 0.0
            self.ice_dmg_bonus: float = 0.0
            self.electric_dmg_bonus: float = 0.0
            self.ether_dmg_bonus: float = 0.0
            self.field_hp_percentage: float = 0.0
            self.field_atk_percentage: float = 0.0
            self.field_def_percentage: float = 0.0
            self.field_imp_percentage: float = 0.0
            self.field_crit_rate: float = 0.0
            self.field_crit_dmg: float = 0.0
            self.field_anomaly_proficiency: float = 0.0
            self.field_anomaly_mastery: float = 0.0
            self.field_pen_ratio: float = 0.0
            self.field_pen_numeric: float = 0.0
            self.field_sp_regen: float = 0.0
            self.field_sp_get_ratio: float = 0.0
            self.field_sp_limit: float = 0.0
            self.extra_damage_ratio: float = 0.0  # 基础伤害倍率
            self.decibel_get_ratio: float = 0.0  # 喧响获得效率

            self.phy_crit_dmg_bonus: float = 0.0
            self.fire_crit_dmg_bonus: float = 0.0
            self.ice_crit_dmg_bonus: float = 0.0
            self.electric_crit_dmg_bonus: float = 0.0
            self.ether_crit_dmg_bonus: float = 0.0

            self.phy_crit_rate_bonus: float = 0.0
            self.fire_crit_rate_bonus: float = 0.0
            self.ice_crit_rate_bonus: float = 0.0
            self.electric_crit_rate_bonus: float = 0.0
            self.ether_crit_rate_bonus: float = 0.0

            self.attack_type_dmg_bonus: float = 0.0
            self.normal_attack_dmg_bonus: float = 0.0
            self.special_skill_dmg_bonus: float = 0.0
            self.ex_special_skill_dmg_bonus: float = 0.0
            self.dash_attack_dmg_bonus: float = 0.0
            self.counter_attack_dmg_bonus: float = 0.0
            self.qte_dmg_bonus: float = 0.0
            self.ultimate_dmg_bonus: float = 0.0
            self.quick_aid_dmg_bonus: float = 0.0
            self.defensive_aid_dmg_bonus: float = 0.0
            self.assault_aid_dmg_bonus: float = 0.0
            self.anomaly_dmg_bonus: float = 0.0
            self.all_dmg_bonus: float = 0.0

            self.percentage_def_reduction: float = 0.0
            self.def_reduction: float = 0.0

            self.all_dmg_res_decrease: float = 0.0
            self.physical_dmg_res_decrease: float = 0.0
            self.fire_dmg_res_decrease: float = 0.0
            self.ice_dmg_res_decrease: float = 0.0
            self.electric_dmg_res_decrease: float = 0.0
            self.ether_dmg_res_decrease: float = 0.0

            self.all_res_pen_increase: float = 0.0
            self.physical_res_pen_increase: float = 0.0
            self.fire_res_pen_increase: float = 0.0
            self.ice_res_pen_increase: float = 0.0
            self.electric_res_pen_increase: float = 0.0
            self.ether_res_pen_increase: float = 0.0

            self.all_anomaly_res_decrease: float = 0.0
            self.physical_anomaly_res_decrease: float = 0.0
            self.fire_anomaly_res_decrease: float = 0.0
            self.ice_anomaly_res_decrease: float = 0.0
            self.electric_anomaly_res_decrease: float = 0.0
            self.ether_anomaly_res_decrease: float = 0.0

            self.received_crit_dmg_bonus: float = 0.0
            self.crit_rate_received_increase: float = 0.0

            self.physical_vulnerability: float = 0.0
            self.fire_vulnerability: float = 0.0
            self.ice_vulnerability: float = 0.0
            self.electric_vulnerability: float = 0.0
            self.ether_vulnerability: float = 0.0
            self.anomaly_vulnerability: float = 0.0
            self.all_vulnerability: float = 0.0

            self.stun_res: float = 0.0
            self.stun_bonus: float = 0.0
            self.received_stun_increase: float = 0.0
            self.stun_vulnerability_increase: float = 0.0
            self.stun_vulnerability_increase_all_time: float = 0.0

            self.normal_attack_stun_bonus: float = 0.0
            self.special_skill_stun_bonus: float = 0.0
            self.ex_special_skill_stun_bonus: float = 0.0
            self.dash_attack_stun_bonus: float = 0.0
            self.counter_attack_stun_bonus: float = 0.0
            self.qte_stun_bonus: float = 0.0
            self.ultimate_stun_bonus: float = 0.0
            self.quick_aid_stun_bonus: float = 0.0
            self.defensive_aid_stun_bonus: float = 0.0
            self.assault_aid_stun_bonus: float = 0.0

            self.physical_anomaly_buildup_bonus: float = 0.0
            self.fire_anomaly_buildup_bonus: float = 0.0
            self.ice_anomaly_buildup_bonus: float = 0.0
            self.electric_anomaly_buildup_bonus: float = 0.0
            self.ether_anomaly_buildup_bonus: float = 0.0
            self.frost_anomaly_buildup_bonus: float = 0.0
            self.all_anomaly_buildup_bonus: float = 0.0

            self.normal_attack_anomaly_buildup_bonus: float = 0.0
            self.special_skill_anomaly_buildup_bonus: float = 0.0
            self.ex_special_skill_anomaly_buildup_bonus: float = 0.0
            self.dash_attack_anomaly_buildup_bonus: float = 0.0
            self.counter_attack_anomaly_buildup_bonus: float = 0.0
            self.qte_anomaly_buildup_bonus: float = 0.0
            self.ultimate_anomaly_buildup_bonus: float = 0.0
            self.quick_aid_anomaly_buildup_bonus: float = 0.0
            self.defensive_aid_anomaly_buildup_bonus: float = 0.0
            self.assault_aid_anomaly_buildup_bonus: float = 0.0

            self.assault_dmg_mul: float = 0.0
            self.burn_dmg_mul: float = 0.0
            self.freeze_dmg_mul: float = 0.0
            self.shock_dmg_mul: float = 0.0
            self.chaos_dmg_mul: float = 0.0
            self.disorder_dmg_mul: float = 0.0
            self.all_anomaly_dmg_mul: float = 0.0

            self.special_multiplier_zone: float = 0.0

            self.stun_tick_increase: int = 0

            self.base_dmg_increase: float = 0.0
            self.base_dmg_increase_percentage: float = 0.0

            self.aftershock_attack_dmg_bonus: float = 0.0
            self.aftershock_attack_crit_dmg_bonus: float = 0.0
            self.aftershock_attack_stun_bonus: float = 0.0

            self.assault_time_increase: float = 0.0
            self.assault_time_increase_percentage: float = 0.0
            self.burn_time_increase: float = 0.0
            self.burn_time_increase_percentage: float = 0.0
            self.shock_time_increase: float = 0.0
            self.shock_time_increase_percentage: float = 0.0
            self.corruption_time_increase: float = 0.0
            self.corruption_time_increase_percentage: float = 0.0
            self.frostbite_time_increase: float = 0.0
            self.frostbite_time_increase_percentage: float = 0.0
            self.frost_frostbite_time_increase: float = 0.0
            self.frost_frostbite_time_increase_percentage: float = 0.0
            self.all_anomaly_time_increase: float = 0.0
            self.all_anomaly_time_increase_percentage: float = 0.0

            self.strike_crit_rate_increase: float = 0.0
            self.strike_crit_dmg_increase: float = 0.0
            self.strike_ignore_defense: float = 0.0

            # 异常其他属性
            self.strike_crit_rate_increase: float = 0.0
            self.strike_crit_dmg_increase: float = 0.0
            self.strike_ignore_defense: float = 0.0

            self.all_disorder_basic_mul: float = 0.0
            self.strike_disorder_basic_mul: float = 0.0
            self.burn_disorder_basic_mul: float = 0.0
            self.frostbite_disorder_basic_mul: float = 0.0
            self.shock_disorder_basic_mul: float = 0.0
            self.chaos_disorder_basic_mul: float = 0.0

            self.sheer_atk: float = 0.0  # 固定贯穿力增幅
            self.field_sheer_atk_percentage: float = 0.0  # 局内百分比贯穿力增幅
            self.sheer_dmg_bonus: float = 0.0  # 贯穿伤害增加

            self.__read_dynamic_statement(dynamic_statement)
            """在更新完全部Buff效果后，再组成字典（提前组成字典会导致字典内容和后置的赋值脱钩）"""
            self.ano_extra_bonus: dict[ElementType | Literal["all", -1], float] = {
                0: self.assault_dmg_mul,
                1: self.burn_dmg_mul,
                2: self.freeze_dmg_mul,
                3: self.shock_dmg_mul,
                4: self.chaos_dmg_mul,
                5: self.freeze_dmg_mul,
                -1: self.disorder_dmg_mul,
                "all": self.all_anomaly_dmg_mul,
            }
            self.anomaly_time_increase: dict[ElementType | Literal["all"], float] = {
                0: self.assault_time_increase,
                1: self.burn_time_increase,
                2: self.shock_time_increase,
                3: self.frostbite_time_increase,
                4: self.corruption_time_increase,
                5: self.frost_frostbite_time_increase,
                "all": self.all_anomaly_time_increase,
            }

            self.anomaly_time_increase_percentage: dict[ElementType | Literal["all"], float] = {
                0: self.assault_time_increase_percentage,
                1: self.burn_time_increase_percentage,
                2: self.shock_time_increase_percentage,
                3: self.frostbite_time_increase_percentage,
                4: self.corruption_time_increase_percentage,
                5: self.frost_frostbite_time_increase_percentage,
                "all": self.all_anomaly_time_increase_percentage,
            }

            self.disorder_basic_mul_map: dict[ElementType | Literal["all"], float] = {
                0: self.strike_disorder_basic_mul,
                1: self.burn_disorder_basic_mul,
                2: self.frostbite_disorder_basic_mul,
                3: self.shock_disorder_basic_mul,
                4: self.chaos_disorder_basic_mul,
                5: self.frostbite_disorder_basic_mul,
                6: self.chaos_disorder_basic_mul,
                "all": self.all_disorder_basic_mul,
            }

        def __read_dynamic_statement(self, dynamic_statement: dict) -> None:
            """使用翻译json初始化动态面板"""
            # 打开buff_effect_trans.json

            # 确保所有的属性都有默认值
            # for value in buff_effect_trans.values():
            #     if not hasattr(self, value):
            #         setattr(self, value, 0.0)
            # 遍历dynamic_statement，根据json翻译，设置对应的属性值
            for CNkey, value in dynamic_statement.items():
                if CNkey in buff_effect_trans:
                    attr_name = buff_effect_trans[CNkey]
                    setattr(self, attr_name, getattr(self, attr_name) + value)
                else:
                    raise KeyError(f"无效的 Buff 乘区键：{CNkey}")


class CalculatorBuffAttributeReader(BuffAttributeReader):
    """基于现有 Calculator 聚合规则的属性读取适配器。"""

    def read_anomaly_mastery(self, context: BuffAttributeReadContext) -> np.float64:
        static, dynamic = self._build_statements(context)
        return _calculate_anomaly_mastery(static, dynamic)

    def read_anomaly_proficiency(self, context: BuffAttributeReadContext) -> np.float64:
        static, dynamic = self._build_statements(context)
        return _calculate_anomaly_proficiency(static, dynamic)

    def read_impact(self, context: BuffAttributeReadContext) -> float:
        data = self._build_formula_snapshot(context)
        return Calculator.StunMul.cal_imp(data)

    def read_full_crit_rate(self, context: BuffAttributeReadContext) -> float:
        data = self._build_formula_snapshot(context)
        return Calculator.RegularMul.cal_crit_rate(data)

    def read_personal_crit_rate(self, context: BuffAttributeReadContext) -> float:
        data = self._build_formula_snapshot(context)
        return Calculator.RegularMul.cal_personal_crit_rate(data)

    def read_personal_crit_damage(self, context: BuffAttributeReadContext) -> float:
        data = self._build_formula_snapshot(context)
        return Calculator.RegularMul.cal_personal_crit_dmg(data)

    def read_pen_ratio(
        self,
        context: BuffAttributeReadContext,
        *,
        addon_pen_ratio: float = 0.0,
    ) -> float:
        static, dynamic = self._build_statements(context)
        return _calculate_pen_ratio(
            static,
            dynamic,
            addon_pen_ratio=addon_pen_ratio,
        )

    @staticmethod
    def _build_formula_snapshot(
        context: BuffAttributeReadContext,
    ) -> RetainedFormulaSnapshot:
        static, dynamic = CalculatorBuffAttributeReader._build_statements(context)
        return _CalculatorRetainedFormulaSnapshot(
            static=static,
            dynamic=dynamic,
            judge_node=context.query_node,
            enemy_obj=context.enemy,
            char_level=getattr(context.character, "level", None),
        )

    @staticmethod
    def _build_statements(context: BuffAttributeReadContext) -> tuple[Any, Any]:
        static_statement = getattr(context.character, "statement", None)
        static = MultiplierData.StaticStatement(static_statement)
        dynamic = MultiplierData.DynamicStatement(
            _calculate_dynamic_statement(
                context.enemy,
                context.active_buff_view,
                context.character,
                context.query_node,
                enemy_debuffs=context.enemy_debuffs,
                sim_instance=context.formula_sim_instance,
                char_name=context.formula_char_name,
            )
        )
        return static, dynamic


@dataclass(frozen=True, slots=True)
class CalculatorBuffAttributeReaderService:
    """共享 Calculator Buff 属性 reader 生命周期的轻量服务。"""

    _reader: BuffAttributeReader = field(
        default_factory=CalculatorBuffAttributeReader,
        repr=False,
    )

    def read_anomaly_mastery(self, context: BuffAttributeReadContext) -> np.float64:
        return self._reader.read_anomaly_mastery(context)

    def read_anomaly_proficiency(self, context: BuffAttributeReadContext) -> np.float64:
        return self._reader.read_anomaly_proficiency(context)

    def read_impact(self, context: BuffAttributeReadContext) -> float:
        return self._reader.read_impact(context)

    def read_full_crit_rate(self, context: BuffAttributeReadContext) -> float:
        return self._reader.read_full_crit_rate(context)

    def read_personal_crit_rate(self, context: BuffAttributeReadContext) -> float:
        return self._reader.read_personal_crit_rate(context)

    def read_personal_crit_damage(self, context: BuffAttributeReadContext) -> float:
        return self._reader.read_personal_crit_damage(context)

    def read_pen_ratio(
        self,
        context: BuffAttributeReadContext,
        *,
        addon_pen_ratio: float = 0.0,
    ) -> float:
        return self._reader.read_pen_ratio(
            context,
            addon_pen_ratio=addon_pen_ratio,
        )

    def calculate_buff_total_bonus(
        self,
        context: CalculatorBuffBonusReadContext,
    ) -> dict[str, float]:
        return calculate_calculator_buff_total_bonus(context)


_CALCULATOR_BUFF_ATTRIBUTE_READER_SERVICE = CalculatorBuffAttributeReaderService()


def get_calculator_buff_attribute_reader_service() -> CalculatorBuffAttributeReaderService:
    """返回可安全复用的 Calculator Buff 属性 reader 服务。"""

    return _CALCULATOR_BUFF_ATTRIBUTE_READER_SERVICE


class Calculator:
    def __init__(
        self,
        skill_node: SkillNode,
        character_obj: Character,
        enemy_obj: Enemy,
        dynamic_buff: Mapping[str, Sequence[Any]] | None = None,
    ):
        """
        Calculator 是 Schedule 阶段获得 SkillNode 后的计算处理逻辑

        当计划事件读取到 SkillNode 时，Calculator 会根据目前的角色的面板、enemy 对象、角色的动态buff，
        计算出角色的直伤、异常、失衡的各乘区，并根据需求计算出输出、异常值、异常快照、失衡值
        """
        if dynamic_buff is None:
            dynamic_buff = {}

        if not isinstance(skill_node, SkillNode):
            raise ValueError("错误的参数类型，应该为SkillNode")
        if not isinstance(character_obj, Character):
            raise ValueError("错误的参数类型，应该为Character")
        if not isinstance(enemy_obj, Enemy):
            raise ValueError("错误的参数类型，应该为Enemy")
        if not isinstance(dynamic_buff, MappingABC):
            raise ValueError("错误的参数类型，应该为dict")

        # 创建MultiplierData对象，用于计算各种战斗中的乘区数据
        data = MultiplierData(enemy_obj, dynamic_buff, character_obj, skill_node)

        # 初始化角色名称和角色ID

        self.char_name: str | None = data.char_name
        self.cid: int | None = data.cid
        self.skill_node = skill_node
        assert isinstance(data.judge_node, SkillNode)
        self.element_type = data.judge_node.element_type
        self.skill_tag = data.judge_node.skill_tag

        # 初始化各种乘区
        self.regular_multipliers = self.RegularMul(data)
        self.anomaly_multipliers = self.AnomalyMul(data)
        self.stun_multipliers = self.StunMul(data)

        # 处理失衡时间增加
        self.update_stun_tick(enemy_obj, data)

    class RegularMul:
        """
        负责计算与储存与常规直伤有关的属性

        常规直伤 = 基础伤害区 * 增伤区 * 暴击区 * 防御区 * 抗性区 * 减易伤区 * 失衡易伤区 * 特殊乘区
        """

        def __init__(self, data: MultiplierData):
            self.base_dmg = self.cal_base_dmg(data)
            self.dmg_bonus = self.cal_dmg_bonus(data)
            self.crit_rate = self.cal_crit_rate(data)
            self.crit_dmg = self.cal_crit_dmg(data)
            self.crit_expect = self.cal_crit_expect(data)
            self.defense_mul = self.cal_defense_mul(data)
            self.res_mul = self.cal_res_mul(data)
            self.dmg_vulnerability = self.cal_dmg_vulnerability(data)
            self.stun_vulnerability = self.cal_stun_vulnerability(data)
            self.special_multiplier_zone = self.cal_special_mul(data)
            self.sheer_dmg_bonus = self.cal_sheer_dmg_bonus(data)
            # 常规伤害
            self.regular_dmg_multipliers = {
                "基础伤害区": self.base_dmg,
                "增伤区": self.dmg_bonus,
                "暴击率": self.crit_rate,
                "暴击伤害": self.crit_dmg,
                "暴击期望": self.crit_expect,
                "防御区": self.defense_mul,
                "抗性区": self.res_mul,
                "减易伤区": self.dmg_vulnerability,
                "失衡易伤区": self.stun_vulnerability,
                "特殊倍率区": self.special_multiplier_zone,
                "贯穿伤害区": self.sheer_dmg_bonus,
            }

        def _as_domain_multipliers(self) -> RegularDamageMultipliers:
            return RegularDamageMultipliers(
                base_damage=self.base_dmg,
                damage_bonus=self.dmg_bonus,
                crit_rate=self.crit_rate,
                crit_damage=self.crit_dmg,
                crit_expectation=self.crit_expect,
                defense_multiplier=self.defense_mul,
                resistance_multiplier=self.res_mul,
                damage_vulnerability_multiplier=self.dmg_vulnerability,
                stun_vulnerability_multiplier=self.stun_vulnerability,
                special_multiplier=self.special_multiplier_zone,
                sheer_damage_bonus=self.sheer_dmg_bonus,
            )

        def get_array_expect(self) -> np.ndarray:
            return assemble_regular_damage_multiplier_array(
                self._as_domain_multipliers(),
                mode="expect",
            )

        def get_array_crit(self) -> np.ndarray:
            return assemble_regular_damage_multiplier_array(
                self._as_domain_multipliers(),
                mode="crit",
            )

        def get_array_not_crit(self) -> np.ndarray:
            return assemble_regular_damage_multiplier_array(
                self._as_domain_multipliers(),
                mode="not_crit",
            )

        def cal_base_dmg(self, data: MultiplierData) -> float:
            """
            基础伤害区 = 伤害倍率 * 对应属性

            如非特殊注明，代理人技能的伤害倍率都是基于自身攻击力的，在代理人的技能页面可以轻易查阅技能的伤害倍率，
            玩家也可以在战斗中于暂停菜单中看到技能的伤害倍率。
            而代理人的攻击力也可以在代理人页面或战斗中的暂停菜单中查阅，当然考虑到战斗中可能存在的各种Buff，
            实时的伤害计算请关注战斗中实际的攻击力数值。
            """
            assert isinstance(data.judge_node, SkillNode), "非法的调用，没有获取到skill node"
            _regular_base_attribute_input(data)
            dmg_ratio = data.judge_node.skill.damage_ratio / data.judge_node.hit_times
            base_attr = data.judge_node.skill.diff_multiplier
            attr = self.cal_base_attr(base_attr, data)
            base_dmg = _calculate_base_damage(dmg_ratio, attr, data.dynamic)
            # if data.judge_node.char_name == "雅":
            #     print(f"雅的基础乘区为：{dmg_ratio:.2f}, 基础攻击力{data.static.atk:.2f} 局内百分比 {data.dynamic.field_atk_percentage:.2f}固定攻击力{data.dynamic.atk:.2f}")
            return base_dmg

        def cal_base_attr(self, base_attr: int, data: MultiplierData):
            """根据base_attr来计算对应属性的值"""
            if base_attr in [0, 1, 2, 3]:
                return _calculate_non_sheer_base_attribute(base_attr, data.static, data.dynamic)
            elif base_attr == 4:
                assert data.char_instance is not None
                attr = _calculate_sheer_base_attribute(
                    data.char_instance,
                    data.dynamic,
                    lambda key: self.cal_base_attr(base_attr=key, data=data),
                )
            else:
                raise AssertionError(INVALID_ELEMENT_ERROR)
            return attr

        @staticmethod
        def cal_dmg_bonus(data: MultiplierData) -> float:
            """
            增伤区 = 100% + 属性增伤 + 伤害类型增伤 + 进攻类型增伤 + 全类型增伤

            增伤区包含游戏中各种百分比形式的伤害提升/加成，造成伤害降低同样作用于该乘区，理解为负的增伤即可。
            属性增伤即针对游戏中5种伤害属性(火(Fire)、电(Electric)、冰(Ice)、物理(Physical)和以太(Ether))的伤害加成。属性增伤常见于驱动盘位的主属性和音擎效果。
            伤害类型增伤包括针对于各类技能(如普通攻击，强化特殊技，终结技等)的增伤。常见于音擎效果和鸣徽效果中。
            进攻类型增伤即针对于角色进攻类型(斩击(Slash)、打击(Strike)和穿透(Pierce))的增伤。全类型增伤就是未作类型限定的增伤。
            """
            assert isinstance(data.judge_node, SkillNode)
            return _calculate_damage_bonus(data.static, data.dynamic, data.judge_node)

        @staticmethod
        def cal_crit_rate(data: RetainedFormulaSnapshot) -> float:
            """暴击率 = 面板暴击率 + buff暴击率 + 受暴击概率增加"""
            return _calculate_full_crit_rate(data.static, data.dynamic)

        @staticmethod
        def cal_personal_crit_rate(data: RetainedFormulaSnapshot) -> float:
            """个人实时暴击率 = 面板暴击率 + buff暴击率"""
            return _calculate_personal_crit_rate(data.static, data.dynamic)

        @staticmethod
        def cal_crit_dmg(data: MultiplierData) -> float:
            """暴击伤害 = 静态面板暴击伤害 + buff暴击伤害 + 受暴击伤害增加"""
            assert isinstance(data.judge_node, SkillNode)
            return _calculate_full_crit_damage(
                data.static,
                data.dynamic,
                data.judge_node,
            )

        def cal_crit_expect(self, data: MultiplierData) -> float:
            """暴击期望 = 1 + 暴击率 * 暴击伤害"""
            return _calculate_crit_expectation(self.crit_rate, self.crit_dmg)

        @staticmethod
        def cal_personal_crit_dmg(data: RetainedFormulaSnapshot) -> float:
            """面板暴击伤害 = 静态面板暴击伤害 + buff暴击伤害"""
            return _calculate_personal_crit_damage(data.static, data.dynamic)

        def cal_defense_mul(self, data: MultiplierData) -> float:
            """
            防御区 = 攻击方等级基数 / (受击方有效防御 + 攻击方等级基数)
            当检测到攻击属性为4时，说明是贯穿伤害，无视防御区，所以直接返回1

            受击方有效防御 = 受击方防御 * (1 - 攻击方穿透率%) - 攻击方穿透值 ≥ 0
            受击方防御 = (基础防御 * (1 + 战斗外防御%) + 战斗外固定防御) * (1 + 防御加成% - 防御降低%) + 固定防御
            """
            assert isinstance(data.judge_node, SkillNode)
            base_attr = data.judge_node.skill.diff_multiplier
            attacker_level: int = data.char_level if data.char_level is not None else 1
            return _calculate_defense_multiplier(
                data.enemy_obj,
                data.static,
                data.dynamic,
                base_attr,
                attacker_level,
            )

        @staticmethod
        def cal_recipient_def(
            data: MultiplierData,
            pen_ratio: float,
            *,
            addon_pen_ratio: float = 0.0,
            addon_pen_numeric: float = 0.0,
        ) -> float:
            return _calculate_recipient_defense(
                data.enemy_obj,
                data.static,
                data.dynamic,
                pen_ratio,
                addon_pen_ratio=addon_pen_ratio,
                addon_pen_numeric=addon_pen_numeric,
            )

        @staticmethod
        def cal_pen_ratio(data: MultiplierData, *, addon_pen_ratio: float = 0.0) -> float:
            return _calculate_pen_ratio(
                data.static,
                data.dynamic,
                addon_pen_ratio=addon_pen_ratio,
            )

        @staticmethod
        def cal_k_attacker(attacker_level: int) -> int:
            return _calculate_attacker_level_coefficient(attacker_level)

        @staticmethod
        def cal_res_mul(
            data: MultiplierData,
            *,
            element_type: ElementType | None = None,
            snapshot_res_pen=0,
        ) -> float:
            """抗性区 = 1 - 受击方抗性 + 受击方抗性降低 + 攻击方抗性穿透"""
            if element_type is None:
                assert isinstance(data.judge_node, SkillNode)
                element_type = data.judge_node.element_type
            res_mul = _calculate_resistance_multiplier(
                data.enemy_obj,
                data.dynamic,
                element_type,
                snapshot_res_pen=snapshot_res_pen,
            )
            return res_mul

        @staticmethod
        def cal_dmg_vulnerability(
            data: MultiplierData, *, element_type: ElementType | None = None
        ) -> float:
            """
            减易伤区 = 1 + 减易伤
            """
            if element_type is None:
                assert isinstance(data.judge_node, SkillNode)
                element_type = data.judge_node.element_type
            dmg_vulnerability = _calculate_damage_vulnerability(
                data.dynamic,
                element_type,
            )
            return dmg_vulnerability

        @staticmethod
        def cal_stun_vulnerability(data: MultiplierData) -> float:
            """
            失衡时：失衡易伤区 = 1 + 怪物失衡易伤 + 失衡易伤增幅 + 全时段失衡易伤（扳机核心被动那种）
            非失衡时：失衡易伤区 = 1 + 全时段失衡易伤（扳机核心被动那种）
            """
            return _calculate_stun_vulnerability(data.enemy_obj, data.dynamic)

        @staticmethod
        def cal_special_mul(data: MultiplierData) -> float:
            return _calculate_special_multiplier(data.dynamic)

        @staticmethod
        def cal_sheer_dmg_bonus(data: MultiplierData) -> float:
            """计算贯穿伤害增幅区——贯穿伤害增加是一个独立乘区！"""
            assert isinstance(data.judge_node, SkillNode)
            return _calculate_sheer_damage_bonus(data.judge_node, data.dynamic)

    class AnomalyMul:
        """
        负责计算与储存与异常伤害有关的属性

        异常伤害快照以 array 形式储存，顺序为：
        [基础伤害区、增伤区、异常精通区、等级、异常增伤区、异常暴击区、穿透率、穿透值、抗性穿透]

        异常积蓄值 = 基础积蓄值 * 异常掌控/100 * (1 + 属性异常积蓄效率提升) * (1 - 属性异常积蓄抗性)
        基础伤害区 = 攻击力 * 对应属性的异常伤害倍率
        增伤区 = 1 + 属性增伤 + 全增伤
        异常精通区 = 异常精通 / 100
        等级 = 角色等级
        异常增伤区 = 单独异常增伤
        异常暴击区 单独考虑简一个角色
        """

        def __init__(self, data: MultiplierData):
            assert isinstance(data.judge_node, SkillNode)
            self.element_type: ElementType = data.judge_node.element_type
            self.anomaly_buildup: np.float64 = self.cal_anomaly_buildup(data)

            self.base_damage: float = self.cal_base_damage(data)
            self.dmg_bonus: float = self.cal_dmg_bonus(data)
            self.ap_mul: float = self.cal_ap_mul(data)
            self.level: int = data.char_level if data.char_level is not None else 0
            self.anomaly_bonus: float = self.cal_ano_extra_mul(data)
            self.anomaly_crit: float = self.cal_anomaly_crit(data)
            self.pen_ratio: float = data.static.pen_ratio + data.dynamic.pen_ratio
            self.pen_numeric: float = data.static.pen_numeric + data.dynamic.pen_numeric
            self.res_pen: float = self.cal_res_pen(data)

            self.anomaly_snapshot = np.array(
                [
                    self.base_damage,
                    self.dmg_bonus,
                    self.ap_mul,
                    self.level,
                    self.anomaly_bonus,
                    self.anomaly_crit,
                    self.pen_ratio,
                    self.pen_numeric,
                    self.res_pen,
                ],
                dtype=np.float64,
            )

        @staticmethod
        def cal_am(data: RetainedFormulaSnapshot) -> np.float64:
            return _calculate_anomaly_mastery(data.static, data.dynamic)

        @staticmethod
        def cal_anomaly_buildup(data: MultiplierData) -> np.float64:
            """异常积蓄值 = 基础积蓄值 * 异常掌控/100 * (1 + 属性异常积蓄效率提升) * (1 - 属性异常积蓄抗性)"""
            # 基础蓄积值
            assert isinstance(data.judge_node, SkillNode)
            accumulation = data.judge_node.skill.anomaly_accumulation
            # 异常掌控
            am = Calculator.AnomalyMul.cal_am(data)
            # 属性异常积蓄效率提升、属性异常积蓄抗性
            element_type = data.judge_node.element_type

            enemy_buildup_res = data.enemy_obj.anomaly_resistance_dict.get(element_type, 0.0)

            if element_type == 0:
                element_buildup_bonus = (
                    data.dynamic.physical_anomaly_buildup_bonus
                    + data.dynamic.all_anomaly_buildup_bonus
                )
                buildup_res = 1 - data.dynamic.physical_anomaly_res_decrease - enemy_buildup_res
            elif element_type == 1:
                element_buildup_bonus = (
                    data.dynamic.fire_anomaly_buildup_bonus + data.dynamic.all_anomaly_buildup_bonus
                )
                buildup_res = 1 - data.dynamic.fire_anomaly_res_decrease - enemy_buildup_res
            elif element_type == 2:
                element_buildup_bonus = (
                    data.dynamic.ice_anomaly_buildup_bonus + data.dynamic.all_anomaly_buildup_bonus
                )
                buildup_res = 1 - data.dynamic.ice_anomaly_res_decrease - enemy_buildup_res
            elif element_type == 3:
                element_buildup_bonus = (
                    data.dynamic.electric_anomaly_buildup_bonus
                    + data.dynamic.all_anomaly_buildup_bonus
                )
                buildup_res = 1 - data.dynamic.electric_anomaly_res_decrease - enemy_buildup_res
            elif element_type in [4, 6]:
                element_buildup_bonus = (
                    data.dynamic.ether_anomaly_buildup_bonus
                    + data.dynamic.all_anomaly_buildup_bonus
                )
                buildup_res = 1 - data.dynamic.ether_anomaly_res_decrease - enemy_buildup_res
            elif element_type == 5:
                element_buildup_bonus = (
                    data.dynamic.frost_anomaly_buildup_bonus
                    + data.dynamic.all_anomaly_buildup_bonus
                )
                buildup_res = 1 - data.dynamic.ice_anomaly_res_decrease - enemy_buildup_res
            else:
                raise AssertionError(INVALID_ELEMENT_ERROR)

            trigger_buff_level = data.judge_node.skill.trigger_buff_level
            if trigger_buff_level == 0:
                trigger_buildup_bonus = data.dynamic.normal_attack_anomaly_buildup_bonus
            elif trigger_buff_level == 1:
                trigger_buildup_bonus = data.dynamic.special_skill_anomaly_buildup_bonus
            elif trigger_buff_level == 2:
                trigger_buildup_bonus = data.dynamic.ex_special_skill_anomaly_buildup_bonus
            elif trigger_buff_level == 3:
                trigger_buildup_bonus = data.dynamic.dash_attack_anomaly_buildup_bonus
            elif trigger_buff_level == 4:
                trigger_buildup_bonus = data.dynamic.counter_attack_anomaly_buildup_bonus
            elif trigger_buff_level == 5:
                trigger_buildup_bonus = data.dynamic.qte_anomaly_buildup_bonus
            elif trigger_buff_level == 6:
                trigger_buildup_bonus = data.dynamic.ultimate_anomaly_buildup_bonus
            elif trigger_buff_level == 7:
                trigger_buildup_bonus = data.dynamic.quick_aid_anomaly_buildup_bonus
            elif trigger_buff_level == 8:
                trigger_buildup_bonus = data.dynamic.defensive_aid_anomaly_buildup_bonus
            elif trigger_buff_level == 9:
                trigger_buildup_bonus = data.dynamic.assault_aid_anomaly_buildup_bonus
            elif trigger_buff_level == 10:
                trigger_buildup_bonus = 0
            else:
                raise AssertionError(INVALID_ELEMENT_ERROR)

            element_dmg_percentage = data.judge_node.skill.element_damage_percent

            hit_times = data.judge_node.hit_times

            anomaly_buildup = (
                accumulation
                * (am / 100)
                * (1 + element_buildup_bonus + trigger_buildup_bonus)
                * buildup_res
                * element_dmg_percentage
                / hit_times
            )

            return np.float64(anomaly_buildup)

        @staticmethod
        def cal_base_damage(data: MultiplierData) -> float:
            """基础伤害区 = 攻击力 * 对应属性的异常伤害倍率"""
            base_attr = data.static.atk * (1 + data.dynamic.field_atk_percentage) + data.dynamic.atk
            assert isinstance(data.judge_node, SkillNode)
            element_type = data.judge_node.element_type
            if element_type == 0:
                base_damage = 7.13 * base_attr
            elif element_type == 1:
                base_damage = 0.5 * base_attr
            elif element_type == 2 or element_type == 5:
                base_damage = 5 * base_attr
            elif element_type == 3:
                base_damage = 1.25 * base_attr
            elif element_type in [4, 6]:
                base_damage = 0.625 * base_attr
            else:
                raise AssertionError(INVALID_ELEMENT_ERROR)
            return base_damage

        @staticmethod
        def cal_dmg_bonus(data: MultiplierData) -> float:
            """增伤区 = 1 + 属性增伤 + 全增伤"""
            assert isinstance(data.judge_node, SkillNode)
            element_type = data.judge_node.element_type
            if element_type == 0:
                element_dmg_bonus = data.static.phy_dmg_bonus + data.dynamic.phy_dmg_bonus
            elif element_type == 1:
                element_dmg_bonus = data.static.fire_dmg_bonus + data.dynamic.fire_dmg_bonus
            elif element_type == 2 or element_type == 5:
                element_dmg_bonus = data.static.ice_dmg_bonus + data.dynamic.ice_dmg_bonus
            elif element_type == 3:
                element_dmg_bonus = data.static.electric_dmg_bonus + data.dynamic.electric_dmg_bonus
            elif element_type in [4, 6]:
                element_dmg_bonus = data.static.ether_dmg_bonus + data.dynamic.ether_dmg_bonus
            else:
                raise AssertionError(INVALID_ELEMENT_ERROR)

            dmg_bonus = (
                1 + element_dmg_bonus + data.dynamic.all_dmg_bonus + data.dynamic.anomaly_dmg_bonus
            )
            return dmg_bonus

        def cal_ap_mul(self, data: MultiplierData) -> float:
            """异常精通区 = 异常精通 / 100"""
            ap = self.cal_ap(data)
            ap_mul = ap / 100
            return ap_mul

        @staticmethod
        @lru_cache(maxsize=16)
        def cal_ap(data: RetainedFormulaSnapshot):
            return _calculate_anomaly_proficiency(data.static, data.dynamic)

        @staticmethod
        def cal_ano_extra_mul(data: MultiplierData) -> float:
            """异常额外增伤区 = 1 + 对应属性异常额外增伤"""
            assert isinstance(data.judge_node, SkillNode)
            element_type = data.judge_node.element_type
            map = data.dynamic.ano_extra_bonus
            ano_dmg_mul = 1 + map.get(element_type, 0) + map["all"]
            return ano_dmg_mul

        def cal_anomaly_crit(self, data: MultiplierData) -> float:
            """已弃用，避免大范围重构数据类型，保留一个1"""
            return 1

        @staticmethod
        def _select_res_pen_for_element(
            dynamic: MultiplierData.DynamicStatement, element_type: ElementType
        ) -> float:
            if element_type == 0:
                element_res_pen = dynamic.physical_res_pen_increase
            elif element_type == 1:
                element_res_pen = dynamic.fire_res_pen_increase
            elif element_type == 2 or element_type == 5:
                element_res_pen = dynamic.ice_res_pen_increase
            elif element_type == 3:
                element_res_pen = dynamic.electric_res_pen_increase
            elif element_type in [4, 6]:
                element_res_pen = dynamic.ether_res_pen_increase
            else:
                raise AssertionError(INVALID_ELEMENT_ERROR)
            return element_res_pen

        def cal_res_pen(self, data: MultiplierData) -> float:
            assert isinstance(data.judge_node, SkillNode)
            return self._select_res_pen_for_element(data.dynamic, data.judge_node.element_type)

    class StunMul:
        """
        负责计算与储存与失衡值有关的属性，并负责与enemy互相

        失衡值累积 = 冲击力 * 失衡倍率 * (1 - 失衡抗性) * (1 + 失衡值提升 - 失衡值降低) * (1+ 受到失衡值提升 - 受到失衡值降低)
        """

        def __init__(self, data: MultiplierData):
            assert isinstance(data.judge_node, SkillNode)
            self.element_type: ElementType = data.judge_node.element_type
            self.imp = self.cal_imp(data)
            self.stun_ratio = self.cal_stun_ratio(data)
            self.stun_res = self.cal_stun_res(data, self.element_type)
            self.stun_bonus = self.cal_stun_bonus(data)
            self.stun_received = self.cal_stun_received(data)

        def get_stun_array(self) -> np.ndarray:
            return _build_stun_multiplier_array(
                self.imp,
                self.stun_ratio,
                self.stun_res,
                self.stun_bonus,
                self.stun_received,
            )

        @staticmethod
        def cal_imp(data: RetainedFormulaSnapshot) -> float:
            return _calculate_impact(data.static, data.dynamic)

        @staticmethod
        def cal_stun_ratio(data: MultiplierData) -> float:
            assert isinstance(data.judge_node, SkillNode)
            stun_ratio = data.judge_node.skill.stun_ratio / data.judge_node.hit_times
            return stun_ratio

        @staticmethod
        def cal_stun_res(
            data: MultiplierData, element_type: ElementType, *, over_stun_res: float = 0
        ) -> float:
            enemy_stun_res = data.enemy_obj.stun_resistance_dict.get(element_type, 0.0)
            stun_res = 1 - data.dynamic.stun_res - over_stun_res - enemy_stun_res
            return stun_res

        @staticmethod
        def cal_stun_bonus(data: MultiplierData) -> float:
            # 获取指定label失衡值增加
            assert isinstance(data.judge_node, SkillNode)
            if (
                data.judge_node.skill.labels is not None
                and data.judge_node.skill.labels.get("aftershock_attack") == 1
            ):
                label_stun_bonus = data.dynamic.aftershock_attack_stun_bonus
            else:
                label_stun_bonus = 0
            # 接下来计算标签类失衡值
            tbl = data.judge_node.skill.trigger_buff_level
            if tbl == 0:
                stun_bonus_tbl = data.dynamic.normal_attack_stun_bonus
            elif tbl == 1:
                stun_bonus_tbl = data.dynamic.special_skill_stun_bonus
            elif tbl == 2:
                stun_bonus_tbl = data.dynamic.ex_special_skill_stun_bonus
            elif tbl == 3:
                stun_bonus_tbl = data.dynamic.dash_attack_stun_bonus
            elif tbl == 4:
                stun_bonus_tbl = data.dynamic.counter_attack_stun_bonus
            elif tbl == 5:
                stun_bonus_tbl = data.dynamic.qte_stun_bonus
            elif tbl == 6:
                stun_bonus_tbl = data.dynamic.ultimate_stun_bonus
            elif tbl == 7:
                stun_bonus_tbl = data.dynamic.quick_aid_stun_bonus
            elif tbl == 8:
                stun_bonus_tbl = data.dynamic.defensive_aid_stun_bonus
            elif tbl == 9:
                stun_bonus_tbl = data.dynamic.assault_aid_stun_bonus
            elif tbl == 10:
                stun_bonus_tbl = 0
            else:
                raise ValueError(
                    f"{data.judge_node.skill_tag}的trigger_buff_level为{tbl}，无法解析！"
                )
            all_stun_bonus = data.dynamic.stun_bonus  # 全品类失衡增幅
            stun_bonus = 1 + stun_bonus_tbl + all_stun_bonus + label_stun_bonus
            return stun_bonus

        @staticmethod
        def cal_stun_received(data: MultiplierData, over_stun_received: float = 0) -> float:
            stun_received = 1 + data.dynamic.received_stun_increase + over_stun_received
            return stun_received

    def cal_dmg_expect(self) -> np.float64:
        """计算伤害期望"""
        multipliers: np.ndarray = self.regular_multipliers.get_array_expect()
        dmg_expect = calculate_regular_damage_product(
            self.regular_multipliers._as_domain_multipliers(),
            mode="expect",
        )
        self.check_skill_node_mul(multipliers)
        return np.float64(dmg_expect)

    def check_skill_node_mul(self, multipliers):
        """检查技能节点的乘区"""
        if not CHECK_SKILL_MUL:
            return
        if any([__tag in self.skill_tag for __tag in CHECK_SKILL_MUL_TAG]):
            tag_list = [
                "基础乘区",
                "增伤区",
                "双暴区",
                "防御区",
                "抗性区",
                "易伤区",
                "失衡易伤区",
                "特殊乘区",
                "贯穿伤害区",
            ]
            print(
                self.skill_node.skill.skill_text,
                f"第{self.skill_node.loading_mission.hitted_count if self.skill_node.loading_mission else 1}次命中",
                "：",
                [
                    f"{__tag} : {__value:.2f}"
                    for __tag, __value in zip(tag_list, multipliers, strict=True)
                ],
            )

    def cal_dmg_crit(self) -> np.float64:
        """计算暴击伤害"""
        dmg_crit = calculate_regular_damage_product(
            self.regular_multipliers._as_domain_multipliers(),
            mode="crit",
        )
        return np.float64(dmg_crit)

    def cal_dmg_not_crit(self) -> np.float64:
        """计算非暴击伤害"""
        dmg_not_crit = calculate_regular_damage_product(
            self.regular_multipliers._as_domain_multipliers(),
            mode="not_crit",
        )
        return np.float64(dmg_not_crit)

    def cal_snapshot(self) -> tuple[int, np.float64, np.ndarray]:
        """计算异常值与失衡值快照，返回一个一维数组，用于计算异常伤害的虚拟角色，鬼知道为什么那么麻烦"""
        element_type: int = self.element_type
        build_up: np.float64 = self.anomaly_multipliers.anomaly_buildup
        anomaly_snapshot: np.ndarray = self.anomaly_multipliers.anomaly_snapshot
        stun_snapshot: np.ndarray = np.array(
            [self.stun_multipliers.imp, self.stun_multipliers.stun_bonus]
        )
        snapshot = np.concatenate((anomaly_snapshot, stun_snapshot))
        return element_type, build_up, snapshot

    def cal_stun(self) -> np.float64:
        """计算失衡值"""
        multipliers: np.ndarray = self.stun_multipliers.get_stun_array()
        stun = np.prod(multipliers)
        return np.float64(stun)

    @staticmethod
    def update_stun_tick(enemy_obj: Enemy, data: MultiplierData):
        """专门更新延长失衡时间的 buff"""
        if data.dynamic.stun_tick_increase >= 1:
            enemy_obj.increase_stun_recovery_time(data.dynamic.stun_tick_increase)

    # TODO：当前动作是否能够被打断的计算。
    #  技能自身有抗打断系数，但是考虑到凯撒之类的抗打断Buff的存在，所以需要在Schedule阶段进行一个全局的计算，
    #  在检测到Preload阶段抛出的“怪物进攻”信息后（当前Preload还没有这个功能，应该在这里留好接口），Schedule调取当前动作对应的基础抗打断值，
    #  并且从buff系统中读取抗打断加成，最后返回bool值，表示当前动作是否能够被打断。

    # TODO：Preload与Schedule阶段在打断功能上的交互与后续设计：
    #  ①将打断模块放在Schedule的原因：
    #       在同一个tick中，理论上说，打断事件在Preload阶段处理或是Schedule阶段处理是一样的，
    #       在Schedule阶段处理的好处更多，因为当前tick触发的buff也会被纳入考量。
    #       这样可以避免诸多类似于“某添加抗打断buff、但自身不抗打断的技能，在start标签附近被打断”的特殊情况发生
    #  ②后续设计：
    #       Schedule阶段在完成判定后，应该第一时间更新一个全局的、或是Preload内部能够读取到的一个指定数据结构
    #    （该数据结构粗看下来，布尔值应该就能满足要求，但是后续如果还有精确到tick的要求，那可能会变成字典。）
    #      而在下一个Tick，Preload会根据这个数据结构中的内容来判断“刚刚那个tick的动作是否被打断了”，
    #      这将影响到Preload抛出的是正常主动动作，还是“被打断”的空动作。


if __name__ == "__main__":
    pass
