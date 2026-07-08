from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest

import zsim.sim_progress.calculation.anomaly_calculator as cal_anomaly_module
from zsim.sim_progress.calculation.inputs.anomaly import (
    AnomalyDamageMultipliers,
    AnomalyDamageSnapshot,
)
from zsim.sim_progress.calculation.results.common import MultiplierVector


def _damage_snapshot() -> np.ndarray:
    return np.array(
        [[120.0, 1.15, 2.25, 60.0, 1.35, 999.0, 0.07, 12.0, 0.09, 1.2, 1.4]],
        dtype=np.float64,
    )


def test_legacy_anomaly_multiplier_vector_helper_delegates_to_formula_module(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = cal_anomaly_module.anomaly_damage_formulas.assemble_anomaly_damage_multiplier_vector
    calls: list[tuple[AnomalyDamageSnapshot, AnomalyDamageMultipliers]] = []

    def recording_assemble(
        snapshot: AnomalyDamageSnapshot,
        multipliers: AnomalyDamageMultipliers,
    ) -> MultiplierVector:
        calls.append((snapshot, multipliers))
        return original(snapshot, multipliers)

    monkeypatch.setattr(
        cal_anomaly_module.anomaly_damage_formulas,
        "assemble_anomaly_damage_multiplier_vector",
        recording_assemble,
    )

    actual = cal_anomaly_module._assemble_final_multiplier_vector(
        _damage_snapshot(),
        k_level=np.float64(2.0),
        active_crit=np.float64(1.15),
        def_mul=np.float64(0.71),
        res_mul=np.float64(1.06),
        vulnerability_mul=np.float64(1.25),
        snapshot_impact=np.float64(1.2),
        snapshot_stun_bonus=np.float64(1.4),
        stun_vulnerability=np.float64(1.7),
        special_mul=np.float64(1.07),
    )

    expected = original(
        AnomalyDamageSnapshot(
            base_damage=120.0,
            damage_bonus=1.15,
            anomaly_mastery_multiplier=2.25,
            anomaly_damage_bonus=1.35,
            snapshot_impact=1.2,
            snapshot_stun_bonus=1.4,
        ),
        AnomalyDamageMultipliers(
            level_multiplier=2.0,
            active_crit_multiplier=1.15,
            defense_multiplier=0.71,
            resistance_multiplier=1.06,
            vulnerability_multiplier=1.25,
            stun_vulnerability_multiplier=1.7,
            special_multiplier=1.07,
        ),
    )
    assert len(calls) == 1
    np.testing.assert_allclose(actual, np.array(expected.values, dtype=np.float64))


def test_legacy_anomaly_damage_helper_and_public_method_delegate_to_formula_module(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = cal_anomaly_module.anomaly_damage_formulas.calculate_anomaly_damage_expectation
    calls: list[tuple[tuple[float, ...], float, float, float]] = []

    def recording_damage(
        final_multipliers: tuple[float, ...] | np.ndarray,
        *,
        snapshot_impact: float,
        snapshot_stun_bonus: float,
        scaling_factor: float,
    ) -> np.float64:
        calls.append(
            (
                tuple(final_multipliers),
                snapshot_impact,
                snapshot_stun_bonus,
                scaling_factor,
            )
        )
        return original(
            final_multipliers,
            snapshot_impact=snapshot_impact,
            snapshot_stun_bonus=snapshot_stun_bonus,
            scaling_factor=scaling_factor,
        )

    monkeypatch.setattr(
        cal_anomaly_module.anomaly_damage_formulas,
        "calculate_anomaly_damage_expectation",
        recording_damage,
    )
    final_multipliers = np.array(
        [120.0, 1.15, 2.25, 2.0, 1.35, 1.0, 0.71, 1.06, 1.25, 1.2, 1.4, 1.7, 1.07]
    )

    helper_result = cal_anomaly_module._calculate_anomaly_damage_expectation(
        final_multipliers,
        snapshot_impact=np.float64(1.2),
        snapshot_stun_bonus=np.float64(1.4),
        scaling_factor=np.float64(1.75),
    )
    calculator = cal_anomaly_module.CalAnomaly.__new__(cal_anomaly_module.CalAnomaly)
    calculator.final_multipliers = final_multipliers
    calculator.dmg_sp = _damage_snapshot()
    calculator.anomaly_obj = SimpleNamespace(scaling_factor=np.float64(1.75))

    assert calculator.cal_anomaly_dmg() == pytest.approx(helper_result)
    assert len(calls) == 2
    assert calls[-1] == (
        tuple(final_multipliers),
        1.2,
        1.4,
        1.75,
    )


def test_legacy_abloom_ratio_helper_and_public_constructor_delegate_to_formula_module(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = cal_anomaly_module.anomaly_damage_formulas.apply_anomaly_damage_ratio
    calls: list[tuple[tuple[float, ...], float]] = []

    def recording_ratio(
        final_multipliers: MultiplierVector,
        *,
        anomaly_damage_ratio: float,
    ) -> MultiplierVector:
        calls.append((final_multipliers.values, anomaly_damage_ratio))
        return original(
            final_multipliers,
            anomaly_damage_ratio=anomaly_damage_ratio,
        )

    monkeypatch.setattr(
        cal_anomaly_module.anomaly_damage_formulas,
        "apply_anomaly_damage_ratio",
        recording_ratio,
    )
    final_multipliers = np.array([10.0, 2.0, 3.0], dtype=np.float64)
    returned = cal_anomaly_module._apply_abloom_anomaly_damage_ratio(
        final_multipliers,
        anomaly_dmg_ratio=np.float64(1.4),
    )

    assert returned is final_multipliers
    np.testing.assert_allclose(final_multipliers, [14.0, 2.0, 3.0])

    def fake_base_init(self, anomaly_obj, enemy_obj, dynamic_buff, sim_instance) -> None:
        self.final_multipliers = np.array([20.0, 2.0, 3.0], dtype=np.float64)

    monkeypatch.setattr(cal_anomaly_module.CalAnomaly, "__init__", fake_base_init)
    calculator = cal_anomaly_module.CalAbloom(
        SimpleNamespace(anomaly_dmg_ratio=np.float64(1.5)),
        enemy_obj=SimpleNamespace(),
        dynamic_buff={},
        sim_instance=SimpleNamespace(),
    )

    assert calls == [((10.0, 2.0, 3.0), 1.4), ((20.0, 2.0, 3.0), 1.5)]
    np.testing.assert_allclose(calculator.final_multipliers, [30.0, 2.0, 3.0])


def test_legacy_disorder_public_methods_delegate_to_formula_module(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_base = cal_anomaly_module.disorder_formulas.calculate_disorder_base_damage
    original_extra = cal_anomaly_module.disorder_formulas.calculate_disorder_extra_multiplier
    original_stun = cal_anomaly_module.disorder_formulas.calculate_disorder_stun_multiplier
    calls: list[str] = []

    def recording_base(**kwargs) -> np.float64:
        calls.append("base")
        return original_base(**kwargs)

    def recording_extra(ano_extra_bonus) -> np.float64:
        calls.append("extra")
        return original_extra(ano_extra_bonus)

    def recording_stun(**kwargs) -> np.float64:
        calls.append("stun")
        return original_stun(**kwargs)

    monkeypatch.setattr(
        cal_anomaly_module.disorder_formulas,
        "calculate_disorder_base_damage",
        recording_base,
    )
    monkeypatch.setattr(
        cal_anomaly_module.disorder_formulas,
        "calculate_disorder_extra_multiplier",
        recording_extra,
    )
    monkeypatch.setattr(
        cal_anomaly_module.disorder_formulas,
        "calculate_disorder_stun_multiplier",
        recording_stun,
    )
    monkeypatch.setattr(
        cal_anomaly_module.Cal.StunMul,
        "cal_stun_res",
        lambda data, element_type: np.float64(1.18),
    )
    monkeypatch.setattr(
        cal_anomaly_module.Cal.StunMul,
        "cal_stun_received",
        lambda data: np.float64(1.16),
    )

    calculator = cal_anomaly_module.CalDisorder.__new__(cal_anomaly_module.CalDisorder)
    calculator.element_type = 3
    calculator.anomaly_obj = SimpleNamespace(remaining_tick=lambda: np.float64(315))
    calculator.data = SimpleNamespace(
        dynamic=SimpleNamespace(
            disorder_basic_mul_map={3: 0.20, "all": 0.10},
            ano_extra_bonus={-1: 0.45},
        )
    )
    calculator.final_multipliers = np.array(
        [1105.0, 1, 1, 1, 1.45, 1, 1, 1, 1, 1.25, 1.35, 1, 1],
        dtype=np.float64,
    )
    calculator.v_char_level = 60

    assert calculator.cal_disorder_base_dmg(np.float64(125.0)) == pytest.approx(
        original_base(
            element_type=3,
            base_multiplier=125.0,
            remaining_tick=315.0,
            disorder_basic_multiplier_map={3: 0.20, "all": 0.10},
        )
    )
    assert calculator.cal_disorder_extra_mul() == pytest.approx(1.45)
    assert calculator.cal_disorder_stun() == pytest.approx(
        original_stun(
            impact=1.25,
            snapshot_stun_bonus=1.35,
            stun_resistance_multiplier=1.18,
            received_stun_increase_multiplier=1.16,
            virtual_character_level=60,
        )
    )
    assert calls == ["base", "extra", "stun"]


def test_legacy_polarity_disorder_public_method_delegates_to_formula_module(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = cal_anomaly_module.polarity_disorder_formulas.calculate_polarity_disorder_base_damage
    calls: list[dict[str, float]] = []

    def recording_polarity(**kwargs) -> np.float64:
        calls.append(dict(kwargs))
        return original(**kwargs)

    monkeypatch.setattr(
        cal_anomaly_module.polarity_disorder_formulas,
        "calculate_polarity_disorder_base_damage",
        recording_polarity,
    )
    calculator = cal_anomaly_module.CalPolarityDisorder.__new__(
        cal_anomaly_module.CalPolarityDisorder
    )

    actual = calculator.cal_polarity_disorder_base_dmg(
        np.float64(1105.0),
        np.float64(560.0),
        polarity_disorder_ratio=np.float64(0.13),
        additional_dmg_ap_ratio=np.float64(17.5),
    )

    assert actual == pytest.approx(
        original(
            base_disorder_damage=1105.0,
            yanagi_ap=560.0,
            polarity_disorder_ratio=0.13,
            additional_dmg_ap_ratio=17.5,
        )
    )
    assert calls == [
        {
            "base_disorder_damage": 1105.0,
            "yanagi_ap": 560.0,
            "polarity_disorder_ratio": 0.13,
            "additional_dmg_ap_ratio": 17.5,
        }
    ]
