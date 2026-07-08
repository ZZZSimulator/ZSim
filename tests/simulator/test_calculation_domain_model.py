from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from zsim.sim_progress import calculation
from zsim.sim_progress.calculation import (
    ASSAULT_STATE,
    AURIC_INK_DAMAGE,
    CORRUPTION_STATE,
    ETHER_AFFINITY,
    FROST_DAMAGE,
    FROST_STATE,
    HONED_EDGE_DAMAGE,
    ICE_AFFINITY,
    PHYSICAL_AFFINITY,
    PHYSICAL_DAMAGE,
    AnomalyIdentityProfile,
    AnomalyScalarResult,
    DamageIdentity,
    DamageIdentityProfile,
    DamageScalarResult,
    FormulaLevelContext,
    FormulaSourceContext,
    MultiplierAffinity,
    MultiplierVector,
)

CALCULATION_ROOT = Path("zsim/sim_progress/calculation")
RUNTIME_ADAPTER_MODULES = {
    CALCULATION_ROOT / "calculator.py",
    CALCULATION_ROOT / "anomaly_calculator.py",
}
FORBIDDEN_IMPORT_FRAGMENTS = (
    "Enemy",
    "Buff",
    "AnomalyBar",
    "Simulator",
    "listener",
    "schedule",
    "RuntimeCommand",
    "ScheduleDispatch",
)


def test_identity_values_are_separate_hashable_domain_concepts() -> None:
    frost_damage_profile = AnomalyIdentityProfile(
        damage_identity=FROST_DAMAGE,
        multiplier_affinity=ICE_AFFINITY,
        anomaly_state_identity=FROST_STATE,
    )
    auric_ink_profile = AnomalyIdentityProfile(
        damage_identity=AURIC_INK_DAMAGE,
        multiplier_affinity=ETHER_AFFINITY,
        anomaly_state_identity=CORRUPTION_STATE,
    )
    honed_edge_profile = DamageIdentityProfile(
        damage_identity=HONED_EDGE_DAMAGE,
        multiplier_affinity=PHYSICAL_AFFINITY,
    )

    assert frost_damage_profile.damage_identity != frost_damage_profile.multiplier_affinity
    assert frost_damage_profile.damage_identity != frost_damage_profile.anomaly_state_identity
    assert frost_damage_profile.multiplier_affinity != frost_damage_profile.anomaly_state_identity
    assert frost_damage_profile.damage_identity == DamageIdentity("frost", "烈霜")
    assert frost_damage_profile.multiplier_affinity == MultiplierAffinity("ice", "冰")
    assert auric_ink_profile.damage_identity == AURIC_INK_DAMAGE
    assert auric_ink_profile.multiplier_affinity == ETHER_AFFINITY
    assert honed_edge_profile.damage_identity == HONED_EDGE_DAMAGE
    assert honed_edge_profile.multiplier_affinity == PHYSICAL_AFFINITY
    assert {
        frost_damage_profile,
        auric_ink_profile,
        honed_edge_profile,
    } == {
        AnomalyIdentityProfile(FROST_DAMAGE, ICE_AFFINITY, FROST_STATE),
        AnomalyIdentityProfile(AURIC_INK_DAMAGE, ETHER_AFFINITY, CORRUPTION_STATE),
        DamageIdentityProfile(HONED_EDGE_DAMAGE, PHYSICAL_AFFINITY),
    }


def test_common_input_snapshots_are_frozen_value_objects() -> None:
    levels = FormulaLevelContext(source_level=60, target_level=70)
    source = FormulaSourceContext(source_name="Alice", skill_tag="1361_Q")
    profile = DamageIdentityProfile(
        damage_identity=PHYSICAL_DAMAGE,
        multiplier_affinity=PHYSICAL_AFFINITY,
    )

    with pytest.raises(FrozenInstanceError):
        levels.source_level = 1
    with pytest.raises(FrozenInstanceError):
        source.skill_tag = "mutated"
    with pytest.raises(FrozenInstanceError):
        profile.damage_identity = HONED_EDGE_DAMAGE

    assert levels == FormulaLevelContext(source_level=60, target_level=70)
    assert source == FormulaSourceContext(source_name="Alice", skill_tag="1361_Q")
    assert hash(profile) == hash(DamageIdentityProfile(PHYSICAL_DAMAGE, PHYSICAL_AFFINITY))


def test_common_result_snapshots_are_frozen_and_tuple_backed() -> None:
    identity = DamageIdentityProfile(
        damage_identity=PHYSICAL_DAMAGE,
        multiplier_affinity=PHYSICAL_AFFINITY,
    )
    multipliers = MultiplierVector(values=[1.0, 1.2], labels=["base", "bonus"])
    result = DamageScalarResult(value=120.0, identity=identity, multipliers=multipliers)
    anomaly_result = AnomalyScalarResult(
        value=500.0,
        identity=AnomalyIdentityProfile(PHYSICAL_DAMAGE, PHYSICAL_AFFINITY, ASSAULT_STATE),
        multipliers=MultiplierVector((2.0,)),
    )

    assert multipliers.values == (1.0, 1.2)
    assert multipliers.labels == ("base", "bonus")
    assert anomaly_result.multipliers.values == (2.0,)
    with pytest.raises(FrozenInstanceError):
        result.value = 1.0
    with pytest.raises(FrozenInstanceError):
        multipliers.values += (1.5,)
    with pytest.raises(ValueError, match="labels must match"):
        MultiplierVector(values=(1.0, 2.0), labels=("only-one-label",))


def test_public_exports_cover_identity_input_and_result_interfaces() -> None:
    expected_names = {
        "DamageIdentity",
        "MultiplierAffinity",
        "DamageIdentityProfile",
        "AnomalyIdentityProfile",
        "FormulaLevelContext",
        "FormulaSourceContext",
        "MultiplierVector",
        "DamageScalarResult",
        "AnomalyScalarResult",
    }

    assert expected_names <= set(calculation.__all__)
    for name in expected_names:
        assert getattr(calculation, name) is not None


def test_calculation_domain_model_imports_no_runtime_objects() -> None:
    imports: dict[Path, list[str]] = {}
    for path in CALCULATION_ROOT.rglob("*.py"):
        if path in RUNTIME_ADAPTER_MODULES:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        names: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    names.append(node.module)
                names.extend(alias.name for alias in node.names)
        imports[path] = names

    forbidden_hits = {
        path.as_posix(): name
        for path, names in imports.items()
        for name in names
        for fragment in FORBIDDEN_IMPORT_FRAGMENTS
        if fragment.lower() in name.lower()
    }
    assert forbidden_hits == {}
