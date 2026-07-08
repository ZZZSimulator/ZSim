from __future__ import annotations

from types import SimpleNamespace
from typing import Iterator, Sequence, cast

import numpy as np
import pytest

import zsim.sim_progress.calculation.calculator as calculator_module
import zsim.sim_progress.ScheduledEvent.event_handlers.handlers.skill as skill_handler_module
from zsim.sim_progress.calculation.calculator import Calculator, MultiplierData


class _FakeSkillNode(SimpleNamespace):
    pass


class _FakeCharacter(SimpleNamespace):
    pass


class _FakeEnemy(SimpleNamespace):
    def increase_stun_recovery_time(self, ticks: int) -> None:
        self.stun_recovery_calls.append(ticks)

    def hit_received(self, hit: object, tick: int) -> None:
        self.received_hits.append((hit, tick))


class _HashableProbe(SimpleNamespace):
    __hash__ = object.__hash__


def _reset_formula_oracle_caches() -> None:
    MultiplierData.mul_data_cache.clear()
    MultiplierData.StaticStatement._instance_cache.clear()
    Calculator.AnomalyMul.cal_ap.cache_clear()


@pytest.fixture(autouse=True)
def _reset_formula_fixture_state() -> Iterator[None]:
    _reset_formula_oracle_caches()
    yield
    _reset_formula_oracle_caches()


def _patch_calculator_type_gates(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(calculator_module, "SkillNode", _FakeSkillNode)
    monkeypatch.setattr(calculator_module, "Character", _FakeCharacter)
    monkeypatch.setattr(calculator_module, "Enemy", _FakeEnemy)


def _dynamic_statement_by_attr(**attrs: float) -> dict[str, float]:
    effect_by_attr = {
        cast(str, attr): cast(str, effect)
        for effect, attr in calculator_module.buff_effect_trans.items()
    }
    return {effect_by_attr[attr]: value for attr, value in attrs.items()}


def _make_statement(**values: float) -> SimpleNamespace:
    statement = SimpleNamespace(statement=dict(values))
    for key, value in values.items():
        setattr(statement, key, value)
    return statement


def _base_static_statement() -> SimpleNamespace:
    return _make_statement(
        ATK=1000.0,
        HP=2400.0,
        DEF=620.0,
        IMP=120.0,
        AP=150.0,
        AM=130.0,
        CRIT_rate=0.30,
        CRIT_damage=0.50,
        sp_regen=0.0,
        sp_get_ratio=0.0,
        sp_limit=0.0,
        PEN_ratio=0.10,
        PEN_numeric=20.0,
        PHY_DMG_bonus=0.01,
        FIRE_DMG_bonus=0.02,
        ICE_DMG_bonus=0.03,
        ELECTRIC_DMG_bonus=0.04,
        ETHER_DMG_bonus=0.05,
    )


def _make_character() -> _FakeCharacter:
    return _FakeCharacter(
        NAME="RegularFormulaOracle",
        CID=700001,
        UUID="regular-character-uuid",
        level=60,
        statement=_base_static_statement(),
        sheer_attack_conversion_rate={0: 0.50, 3: 0.25},
    )


def _make_enemy(*, stunned: bool = True) -> _FakeEnemy:
    return _FakeEnemy(
        dynamic=SimpleNamespace(
            dynamic_debuff_list=[_HashableProbe(name="enemy-debuff")],
            dynamic_dot_list=[],
            stun=stunned,
            get_status=lambda: {},
        ),
        sim_instance=_HashableProbe(name="formula-sim"),
        max_DEF=1000.0,
        stun_DMG_take_ratio=0.50,
        anomaly_resistance_dict={5: 0.06, 6: 0.07},
        stun_resistance_dict={5: 0.04, 6: 0.05},
        PHY_damage_resistance=0.21,
        FIRE_damage_resistance=0.22,
        ICE_damage_resistance=0.23,
        ELECTRIC_damage_resistance=0.24,
        ETHER_damage_resistance=0.25,
        stun_recovery_calls=[],
        received_hits=[],
    )


def _make_skill_node(
    *,
    element_type: int = 5,
    trigger_buff_level: int = 2,
    labels: dict[str, int] | None = None,
    diff_multiplier: int = 0,
) -> _FakeSkillNode:
    if labels is None:
        labels = {"aftershock_attack": 1}
    skill = SimpleNamespace(
        damage_ratio=4.80,
        diff_multiplier=diff_multiplier,
        trigger_buff_level=trigger_buff_level,
        labels=labels,
        anomaly_accumulation=45.0,
        element_damage_percent=0.80,
        stun_ratio=1.20,
        skill_text="regular oracle skill",
        char_name="RegularFormulaOracle",
        follow_by=False,
        heavy_attack=True,
    )
    return _FakeSkillNode(
        skill=skill,
        element_type=element_type,
        hit_times=3,
        skill_tag="700001_REGULAR_ORACLE",
        UUID="regular-skill-uuid",
        loading_mission=None,
        active_generation=True,
        effective_anomaly_buildup=True,
        force_qte_trigger=False,
    )


def _calculator_dynamic_attrs() -> dict[str, float]:
    return {
        "extra_damage_ratio": 0.10,
        "base_dmg_increase_percentage": 0.20,
        "base_dmg_increase": 30.0,
        "field_atk_percentage": 0.20,
        "atk": 50.0,
        "ice_dmg_bonus": 0.13,
        "ex_special_skill_dmg_bonus": 0.17,
        "aftershock_attack_dmg_bonus": 0.19,
        "all_dmg_bonus": 0.11,
        "crit_rate": 0.20,
        "field_crit_rate": 0.40,
        "crit_rate_received_increase": 0.25,
        "crit_dmg": 0.70,
        "field_crit_dmg": 0.40,
        "aftershock_attack_crit_dmg_bonus": 0.30,
        "received_crit_dmg_bonus": 0.20,
        "pen_ratio": 0.05,
        "pen_numeric": 15.0,
        "percentage_def_reduction": 0.10,
        "def_reduction": 40.0,
        "ice_dmg_res_decrease": 0.07,
        "ice_res_pen_increase": 0.03,
        "all_dmg_res_decrease": 0.02,
        "all_res_pen_increase": 0.01,
        "ice_vulnerability": 0.14,
        "all_vulnerability": 0.09,
        "stun_vulnerability_increase": 0.12,
        "stun_vulnerability_increase_all_time": 0.06,
        "special_multiplier_zone": 0.08,
        "field_anomaly_mastery": 0.10,
        "anomaly_mastery": 20.0,
        "frost_anomaly_buildup_bonus": 0.15,
        "all_anomaly_buildup_bonus": 0.05,
        "ice_anomaly_res_decrease": 0.04,
        "ex_special_skill_anomaly_buildup_bonus": 0.09,
        "anomaly_dmg_bonus": 0.07,
        "field_anomaly_proficiency": 0.20,
        "anomaly_proficiency": 30.0,
        "freeze_dmg_mul": 0.18,
        "all_anomaly_dmg_mul": 0.04,
        "field_imp_percentage": 0.25,
        "imp": 10.0,
        "ex_special_skill_stun_bonus": 0.16,
        "stun_bonus": 0.07,
        "aftershock_attack_stun_bonus": 0.05,
        "stun_res": 0.11,
        "received_stun_increase": 0.13,
        "stun_tick_increase": 4,
    }


def _patch_buff_aggregation(
    monkeypatch: pytest.MonkeyPatch,
    dynamic_attrs: dict[str, float],
) -> list[tuple[tuple[object, ...], object | None, object, str | None]]:
    aggregation_calls: list[tuple[tuple[object, ...], object | None, object, str | None]] = []
    dynamic_statement = _dynamic_statement_by_attr(**dynamic_attrs)

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


def _expected_level_coefficient(attacker_level: int) -> int:
    values = [
        0,
        50,
        54,
        58,
        62,
        66,
        71,
        76,
        82,
        88,
        94,
        100,
        107,
        114,
        121,
        129,
        137,
        145,
        153,
        162,
        172,
        181,
        191,
        201,
        211,
        222,
        233,
        245,
        258,
        268,
        281,
        293,
        306,
        319,
        333,
        347,
        362,
        377,
        393,
        409,
        421,
        436,
        452,
        469,
        485,
        502,
        519,
        537,
        556,
        573,
        592,
        612,
        629,
        649,
        669,
        689,
        709,
        730,
        751,
        772,
        794,
    ]
    return values[attacker_level]


def test_regular_private_base_attr_and_base_damage_helpers_lock_current_math() -> None:
    static = SimpleNamespace(
        atk=100.0,
        hp=200.0,
        defense=300.0,
        ap=400.0,
    )
    dynamic = SimpleNamespace(
        field_atk_percentage=0.10,
        atk=11.0,
        field_hp_percentage=0.20,
        hp=22.0,
        field_def_percentage=0.30,
        defense=33.0,
        field_anomaly_proficiency=0.40,
        anomaly_proficiency=44.0,
        extra_damage_ratio=0.50,
        base_dmg_increase_percentage=0.60,
        base_dmg_increase=70.0,
        sheer_atk=12.0,
        field_sheer_atk_percentage=0.0,
    )
    character = SimpleNamespace(
        NAME="SheerOracle",
        sheer_attack_conversion_rate={0: 0.25, 1: 0.10, 3: 0.05},
    )

    base_attrs = [
        calculator_module._calculate_non_sheer_base_attribute(index, static, dynamic)
        for index in range(4)
    ]
    assert base_attrs == pytest.approx([121.0, 262.0, 423.0, 604.0])
    assert calculator_module._calculate_sheer_base_attribute(
        character,
        dynamic,
        lambda index: base_attrs[index],
    ) == pytest.approx((121.0 * 0.25) + (262.0 * 0.10) + (604.0 * 0.05) + 12.0)
    assert calculator_module._calculate_base_damage(
        1.25,
        base_attrs[0],
        dynamic,
    ) == pytest.approx(((1.25 + 0.50) * 121.0) * 1.60 + 70.0)

    dynamic.field_sheer_atk_percentage = 0.01
    with pytest.raises(ValueError, match="局内贯穿力%Buff"):
        calculator_module._calculate_sheer_base_attribute(
            character,
            dynamic,
            lambda index: base_attrs[index],
        )


@pytest.mark.parametrize(
    ("trigger_buff_level", "dynamic_attr"),
    [
        (0, "normal_attack_dmg_bonus"),
        (1, "special_skill_dmg_bonus"),
        (2, "ex_special_skill_dmg_bonus"),
        (3, "dash_attack_dmg_bonus"),
        (4, "counter_attack_dmg_bonus"),
        (5, "qte_dmg_bonus"),
        (6, "ultimate_dmg_bonus"),
        (7, "quick_aid_dmg_bonus"),
        (8, "defensive_aid_dmg_bonus"),
        (9, "assault_aid_dmg_bonus"),
        (10, None),
    ],
)
def test_regular_damage_bonus_trigger_levels_and_aftershock_label(
    trigger_buff_level: int,
    dynamic_attr: str | None,
) -> None:
    static = SimpleNamespace(
        phy_dmg_bonus=0.01,
        fire_dmg_bonus=0.02,
        ice_dmg_bonus=0.03,
        electric_dmg_bonus=0.04,
        ether_dmg_bonus=0.05,
    )
    trigger_values = {
        "normal_attack_dmg_bonus": 0.10,
        "special_skill_dmg_bonus": 0.11,
        "ex_special_skill_dmg_bonus": 0.12,
        "dash_attack_dmg_bonus": 0.13,
        "counter_attack_dmg_bonus": 0.14,
        "qte_dmg_bonus": 0.15,
        "ultimate_dmg_bonus": 0.16,
        "quick_aid_dmg_bonus": 0.17,
        "defensive_aid_dmg_bonus": 0.18,
        "assault_aid_dmg_bonus": 0.19,
    }
    dynamic = SimpleNamespace(
        phy_dmg_bonus=0.20,
        fire_dmg_bonus=0.0,
        ice_dmg_bonus=0.0,
        electric_dmg_bonus=0.0,
        ether_dmg_bonus=0.0,
        all_dmg_bonus=0.30,
        aftershock_attack_dmg_bonus=0.40,
        **trigger_values,
    )
    node = _make_skill_node(
        element_type=0,
        trigger_buff_level=trigger_buff_level,
        labels={"aftershock_attack": 1},
    )

    expected_trigger = 0.0 if dynamic_attr is None else trigger_values[dynamic_attr]
    assert calculator_module._calculate_damage_bonus(static, dynamic, node) == pytest.approx(
        1 + 0.01 + 0.20 + expected_trigger + 0.40 + 0.30
    )


def test_regular_crit_helpers_split_received_and_personal_values_and_cap_crit_damage() -> None:
    static = SimpleNamespace(crit_rate=0.50, crit_damage=2.75)
    dynamic = SimpleNamespace(
        crit_rate=0.20,
        field_crit_rate=0.10,
        crit_rate_received_increase=0.30,
        crit_dmg=1.20,
        field_crit_dmg=0.90,
        received_crit_dmg_bonus=0.80,
        aftershock_attack_crit_dmg_bonus=0.70,
    )
    node = _make_skill_node(labels={"aftershock_attack": 1})

    assert calculator_module._calculate_full_crit_rate(static, dynamic) == pytest.approx(1.10)
    assert calculator_module._calculate_personal_crit_rate(static, dynamic) == pytest.approx(0.80)
    assert calculator_module._calculate_personal_crit_damage(static, dynamic) == pytest.approx(4.85)
    assert calculator_module._calculate_full_crit_damage(static, dynamic, node) == pytest.approx(
        5.0
    )
    assert calculator_module._calculate_crit_expectation(1.10, 5.0) == pytest.approx(6.0)


@pytest.mark.parametrize(
    (
        "element_type",
        "bonus_attr",
        "res_attr",
        "res_decrease_attr",
        "res_pen_attr",
        "vulnerability_attr",
    ),
    [
        (
            0,
            "phy_dmg_bonus",
            "PHY_damage_resistance",
            "physical_dmg_res_decrease",
            "physical_res_pen_increase",
            "physical_vulnerability",
        ),
        (
            1,
            "fire_dmg_bonus",
            "FIRE_damage_resistance",
            "fire_dmg_res_decrease",
            "fire_res_pen_increase",
            "fire_vulnerability",
        ),
        (
            2,
            "ice_dmg_bonus",
            "ICE_damage_resistance",
            "ice_dmg_res_decrease",
            "ice_res_pen_increase",
            "ice_vulnerability",
        ),
        (
            3,
            "electric_dmg_bonus",
            "ELECTRIC_damage_resistance",
            "electric_dmg_res_decrease",
            "electric_res_pen_increase",
            "electric_vulnerability",
        ),
        (
            4,
            "ether_dmg_bonus",
            "ETHER_damage_resistance",
            "ether_dmg_res_decrease",
            "ether_res_pen_increase",
            "ether_vulnerability",
        ),
        (
            5,
            "ice_dmg_bonus",
            "ICE_damage_resistance",
            "ice_dmg_res_decrease",
            "ice_res_pen_increase",
            "ice_vulnerability",
        ),
        (
            6,
            "ether_dmg_bonus",
            "ETHER_damage_resistance",
            "ether_dmg_res_decrease",
            "ether_res_pen_increase",
            "ether_vulnerability",
        ),
    ],
)
def test_regular_element_affinity_maps_damage_resistance_and_vulnerability(
    monkeypatch: pytest.MonkeyPatch,
    element_type: int,
    bonus_attr: str,
    res_attr: str,
    res_decrease_attr: str,
    res_pen_attr: str,
    vulnerability_attr: str,
) -> None:
    _patch_calculator_type_gates(monkeypatch)
    static = SimpleNamespace(
        phy_dmg_bonus=0.01,
        fire_dmg_bonus=0.02,
        ice_dmg_bonus=0.03,
        electric_dmg_bonus=0.04,
        ether_dmg_bonus=0.05,
    )
    dynamic = SimpleNamespace(
        phy_dmg_bonus=0.11,
        fire_dmg_bonus=0.12,
        ice_dmg_bonus=0.13,
        electric_dmg_bonus=0.14,
        ether_dmg_bonus=0.15,
        normal_attack_dmg_bonus=0.0,
        special_skill_dmg_bonus=0.0,
        ex_special_skill_dmg_bonus=0.0,
        dash_attack_dmg_bonus=0.0,
        counter_attack_dmg_bonus=0.0,
        qte_dmg_bonus=0.0,
        ultimate_dmg_bonus=0.0,
        quick_aid_dmg_bonus=0.0,
        defensive_aid_dmg_bonus=0.0,
        assault_aid_dmg_bonus=0.0,
        aftershock_attack_dmg_bonus=0.0,
        all_dmg_bonus=0.21,
        physical_dmg_res_decrease=0.31,
        fire_dmg_res_decrease=0.32,
        ice_dmg_res_decrease=0.33,
        electric_dmg_res_decrease=0.34,
        ether_dmg_res_decrease=0.35,
        physical_res_pen_increase=0.41,
        fire_res_pen_increase=0.42,
        ice_res_pen_increase=0.43,
        electric_res_pen_increase=0.44,
        ether_res_pen_increase=0.45,
        all_dmg_res_decrease=0.51,
        all_res_pen_increase=0.52,
        physical_vulnerability=0.61,
        fire_vulnerability=0.62,
        ice_vulnerability=0.63,
        electric_vulnerability=0.64,
        ether_vulnerability=0.65,
        all_vulnerability=0.71,
    )
    enemy = _make_enemy()
    node = _make_skill_node(
        element_type=element_type,
        trigger_buff_level=10,
        labels={},
    )
    data = SimpleNamespace(
        static=static,
        dynamic=dynamic,
        judge_node=node,
        enemy_obj=enemy,
    )

    assert Calculator.RegularMul.cal_dmg_bonus(data) == pytest.approx(
        1 + getattr(static, bonus_attr) + getattr(dynamic, bonus_attr) + 0.21
    )
    assert Calculator.RegularMul.cal_res_mul(
        data,
        snapshot_res_pen=0.05,
    ) == pytest.approx(
        1
        - (
            getattr(enemy, res_attr)
            - getattr(dynamic, res_decrease_attr)
            - getattr(dynamic, res_pen_attr)
        )
        + 0.51
        + 0.52
        + 0.05
    )
    assert Calculator.RegularMul.cal_dmg_vulnerability(data) == pytest.approx(
        1 + getattr(dynamic, vulnerability_attr) + 0.71
    )


def test_regular_defense_vulnerability_special_sheer_and_stun_helpers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_calculator_type_gates(monkeypatch)
    static = SimpleNamespace(
        pen_ratio=0.10,
        pen_numeric=20.0,
        imp=100.0,
    )
    dynamic = SimpleNamespace(
        pen_ratio=0.05,
        pen_numeric=10.0,
        percentage_def_reduction=0.20,
        def_reduction=50.0,
        stun_vulnerability_increase=0.30,
        stun_vulnerability_increase_all_time=0.10,
        special_multiplier_zone=0.25,
        field_imp_percentage=0.40,
        imp=15.0,
        sheer_dmg_bonus=0.35,
    )
    enemy = _make_enemy(stunned=True)
    node = _make_skill_node(diff_multiplier=4)
    data = SimpleNamespace(
        static=static,
        dynamic=dynamic,
        judge_node=node,
        enemy_obj=enemy,
        char_level=60,
    )

    pen_ratio = Calculator.RegularMul.cal_pen_ratio(data, addon_pen_ratio=0.02)
    recipient_def = Calculator.RegularMul.cal_recipient_def(
        data,
        pen_ratio,
        addon_pen_ratio=0.02,
        addon_pen_numeric=5.0,
    )
    assert pen_ratio == pytest.approx(0.17)
    assert recipient_def == pytest.approx(
        max(0.0, ((1000.0 * 0.80) - 50.0) * (1 - 0.17 - 0.02) - 35.0)
    )
    regular = Calculator.RegularMul.__new__(Calculator.RegularMul)
    assert regular.cal_defense_mul(data) == pytest.approx(1.0)
    assert Calculator.RegularMul.cal_stun_vulnerability(data) == pytest.approx(
        1 + 0.50 + 0.30 + 0.10
    )
    enemy.dynamic.stun = False
    assert Calculator.RegularMul.cal_stun_vulnerability(data) == pytest.approx(1.10)
    assert Calculator.RegularMul.cal_special_mul(data) == pytest.approx(1.25)
    assert Calculator.RegularMul.cal_sheer_dmg_bonus(data) == pytest.approx(1.35)
    assert Calculator.StunMul.cal_imp(data) == pytest.approx(155.0)
    np.testing.assert_allclose(
        calculator_module._build_stun_multiplier_array(155.0, 0.40, 0.80, 1.20, 1.10),
        np.array([155.0, 0.40, 0.80, 1.20, 1.10], dtype=np.float64),
    )


def test_regular_multiplier_vector_order_is_current_public_damage_contract() -> None:
    regular = Calculator.RegularMul.__new__(Calculator.RegularMul)
    regular.base_dmg = 100.0
    regular.dmg_bonus = 1.2
    regular.crit_rate = 0.75
    regular.crit_dmg = 0.80
    regular.crit_expect = 1.60
    regular.defense_mul = 0.70
    regular.res_mul = 1.10
    regular.dmg_vulnerability = 1.30
    regular.stun_vulnerability = 1.40
    regular.special_multiplier_zone = 1.50
    regular.sheer_dmg_bonus = 1.60

    np.testing.assert_allclose(
        regular.get_array_expect(),
        np.array([100.0, 1.2, 1.60, 0.70, 1.10, 1.30, 1.40, 1.50, 1.60]),
    )
    np.testing.assert_allclose(
        regular.get_array_crit(),
        np.array([100.0, 1.2, 1.80, 0.70, 1.10, 1.30, 1.40, 1.50, 1.60]),
    )
    np.testing.assert_allclose(
        regular.get_array_not_crit(),
        np.array([100.0, 1.2, 1.00, 0.70, 1.10, 1.30, 1.40, 1.50, 1.60]),
    )


def test_calculator_public_entrypoints_match_current_regular_stun_and_snapshot_formulas(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_calculator_type_gates(monkeypatch)
    character = _make_character()
    enemy = _make_enemy(stunned=True)
    skill_node = _make_skill_node(element_type=5, trigger_buff_level=2)
    char_buff = _HashableProbe(name="character-buff")
    dynamic_buff = {character.NAME: [char_buff]}
    aggregation_calls = _patch_buff_aggregation(
        monkeypatch,
        _calculator_dynamic_attrs(),
    )

    calculator = Calculator(
        skill_node=skill_node,
        character_obj=character,
        enemy_obj=enemy,
        dynamic_buff=dynamic_buff,
    )

    base_attr = 1000.0 * 1.20 + 50.0
    base_dmg = ((4.80 / 3 + 0.10) * base_attr) * 1.20 + 30.0
    dmg_bonus = 1 + 0.03 + 0.13 + 0.17 + 0.19 + 0.11
    crit_rate = 0.30 + 0.20 + 0.40 + 0.25
    crit_dmg = 0.50 + 0.70 + 0.40 + 0.30 + 0.20
    crit_expect = 1 + min(1, crit_rate) * crit_dmg
    k_attacker = _expected_level_coefficient(60)
    effective_def = max(0.0, ((1000.0 * 0.90) - 40.0) * (1 - 0.15) - 35.0)
    defense_mul = k_attacker / (effective_def + k_attacker)
    res_mul = 1 - (0.23 - 0.07 - 0.03) + 0.02 + 0.01
    dmg_vulnerability = 1 + 0.14 + 0.09
    stun_vulnerability = 1 + 0.50 + 0.12 + 0.06
    special_mul = 1 + 0.08
    expected_regular_expect = np.array(
        [
            base_dmg,
            dmg_bonus,
            crit_expect,
            defense_mul,
            res_mul,
            dmg_vulnerability,
            stun_vulnerability,
            special_mul,
            1.0,
        ],
        dtype=np.float64,
    )
    expected_regular_crit = expected_regular_expect.copy()
    expected_regular_crit[2] = 1 + crit_dmg
    expected_regular_not_crit = expected_regular_expect.copy()
    expected_regular_not_crit[2] = 1.0

    am = 130.0 * 1.10 + 20.0
    buildup = 45.0 * (am / 100) * (1 + 0.15 + 0.05 + 0.09) * (1 - 0.04 - 0.06) * 0.80 / 3
    ap = 150.0 * 1.20 + 30.0
    anomaly_snapshot = np.array(
        [
            5 * base_attr,
            1 + 0.03 + 0.13 + 0.11 + 0.07,
            ap / 100,
            60.0,
            1 + 0.18 + 0.04,
            1.0,
            0.15,
            35.0,
            0.03,
        ],
        dtype=np.float64,
    )
    imp = 120.0 * 1.25 + 10.0
    stun_bonus = 1 + 0.16 + 0.07 + 0.05
    expected_snapshot_vector = np.concatenate(
        (anomaly_snapshot, np.array([imp, stun_bonus], dtype=np.float64))
    )
    expected_stun_array = np.array(
        [
            imp,
            1.20 / 3,
            1 - 0.11 - 0.04,
            stun_bonus,
            1 + 0.13,
        ],
        dtype=np.float64,
    )

    assert aggregation_calls == [
        (
            (char_buff, enemy.dynamic.dynamic_debuff_list[0]),
            skill_node,
            enemy.sim_instance,
            character.NAME,
        )
    ]
    assert enemy.stun_recovery_calls == [4]
    np.testing.assert_allclose(
        calculator.regular_multipliers.get_array_expect(),
        expected_regular_expect,
    )
    np.testing.assert_allclose(
        calculator.regular_multipliers.get_array_crit(),
        expected_regular_crit,
    )
    np.testing.assert_allclose(
        calculator.regular_multipliers.get_array_not_crit(),
        expected_regular_not_crit,
    )
    assert calculator.cal_dmg_expect() == pytest.approx(np.prod(expected_regular_expect))
    assert calculator.cal_dmg_crit() == pytest.approx(np.prod(expected_regular_crit))
    assert calculator.cal_dmg_not_crit() == pytest.approx(np.prod(expected_regular_not_crit))
    assert calculator.cal_stun() == pytest.approx(np.prod(expected_stun_array))
    assert calculator.cal_snapshot()[0] == 5
    assert calculator.cal_snapshot()[1] == pytest.approx(np.float64(buildup))
    np.testing.assert_allclose(calculator.cal_snapshot()[2], expected_snapshot_vector)


def test_skill_handler_damage_path_preserves_calculator_outputs_in_single_hit_and_report(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    handler = skill_handler_module.SkillEventHandler()
    skill_node = _make_skill_node(element_type=6)
    character = _make_character()
    enemy = _make_enemy(stunned=True)
    snapshot = (
        6,
        np.float64(12.25),
        np.array([1.0, 2.0, 3.0], dtype=np.float64),
    )
    report_calls: list[dict[str, object]] = []

    class FakeCalculator:
        def __init__(
            self,
            *,
            skill_node: object,
            character_obj: object,
            enemy_obj: object,
            dynamic_buff: dict[str, Sequence[object]],
        ) -> None:
            self.skill_node = skill_node
            self.character_obj = character_obj
            self.enemy_obj = enemy_obj
            self.dynamic_buff = dynamic_buff
            self.regular_multipliers = SimpleNamespace(crit_rate=0.88, crit_dmg=1.66)

        def cal_snapshot(self) -> tuple[int, np.float64, np.ndarray]:
            return snapshot

        def cal_stun(self) -> np.float64:
            return np.float64(22.5)

        def cal_dmg_expect(self) -> np.float64:
            return np.float64(1234.567)

        def cal_dmg_crit(self) -> np.float64:
            return np.float64(2345.678)

    monkeypatch.setattr(skill_handler_module, "Calculator", FakeCalculator)
    monkeypatch.setattr(skill_handler_module, "SkillNode", _FakeSkillNode)
    monkeypatch.setattr(
        skill_handler_module.Report,
        "report_dmg_result",
        lambda **kwargs: report_calls.append(kwargs),
    )

    handler._calculate_damage(
        skill_node=skill_node,
        char_obj=character,
        enemy=enemy,
        dynamic_buff={character.NAME: []},
        hit_count=3,
        event=skill_node,
        tick=240,
    )

    assert len(enemy.received_hits) == 1
    hit, tick = enemy.received_hits[0]
    assert tick == 240
    assert hit.skill_tag == skill_node.skill_tag
    assert hit.snapshot is snapshot
    assert hit.stun == pytest.approx(22.5)
    assert hit.dmg_expect == pytest.approx(1234.567)
    assert hit.dmg_crit == pytest.approx(2345.678)
    assert hit.hitted_count == 3
    assert hit.proactive is True
    assert hit.heavy_hit is True
    assert hit.skill_node is skill_node
    assert report_calls == [
        {
            "tick": 240,
            "element_type": 6,
            "skill_tag": skill_node.skill_tag,
            "dmg_expect": 1234.57,
            "dmg_crit": 2345.68,
            "stun": 22.5,
            "buildup": 12.25,
            "UUID": "regular-skill-uuid",
            "crit_rate": 0.88,
            "crit_dmg": 1.66,
        }
    ]
