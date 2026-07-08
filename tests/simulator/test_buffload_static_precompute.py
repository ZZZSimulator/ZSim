from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from tests.simulator.test_buff_load_candidate_index import (
    _buff,
    _mission,
    _patch_judge_file,
)
from zsim.sim_progress.Buff import BuffLoad as bl
from zsim.sim_progress.Buff.buff_class import Buff
from zsim.sim_progress.Buff.BuffLoad import BuffLoadCandidateIndex, BuffLoadLoop
from zsim.sim_progress.Load import LoadingMission
from zsim.sim_progress.ScheduledEvent.buff_runtime import (
    BuffTemplateRegistry,
    PendingBuffQueue,
)


def test_candidate_index_precomputes_beneficiaries_matching_buff_go_to(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_judge_file(monkeypatch)
    registry = {
        "alpha": {
            "self": _buff("match-attack", operator="alpha", add_buff_to=1000),
            "self-next": _buff("match-fire", operator="alpha", add_buff_to=1100),
            "previous-enemy": _buff("backend-active", operator="alpha", add_buff_to=101),
        },
        "beta": {
            "beta-team": _buff("match-attack", operator="beta", add_buff_to=1110),
        },
        "enemy": {},
    }
    all_name_order_box = {
        "alpha": ["alpha", "beta", "gamma", "enemy"],
        "beta": ["beta", "gamma", "alpha", "enemy"],
    }
    index = BuffLoadCandidateIndex(
        registry,
        ["alpha", "beta"],
        all_name_order_box,
    )

    alpha_selection = index.select_candidates(
        processor="on_field",
        owner="alpha",
        mission=_mission("alpha", skill_type="attack"),
    )
    beta_selection = index.select_candidates(
        processor="backend",
        owner="beta",
        mission=_mission("alpha", skill_type="attack"),
    )

    assert alpha_selection.beneficiaries_by_key == {
        key: tuple(bl.buff_go_to(buff, all_name_order_box["alpha"]))
        for key, buff in registry["alpha"].items()
    }
    assert beta_selection.beneficiaries_by_key == {
        "beta-team": tuple(bl.buff_go_to(registry["beta"]["beta-team"], all_name_order_box["beta"]))
    }


def test_indexed_loop_uses_precomputed_beneficiaries_and_keeps_plan_match(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_judge_file(monkeypatch)
    registry = {
        "alpha": {
            "match-attack": _buff("match-attack", operator="alpha", add_buff_to=1100),
            "fallback-complex": _buff(
                "fallback-complex",
                operator="alpha",
                add_buff_to=1001,
                simple_judge_logic=False,
                simple_effect_logic=False,
            ),
        },
        "beta": {
            "backend-active": _buff("backend-active", operator="beta", add_buff_to=1010),
        },
        "enemy": {},
    }
    all_name_order_box = {
        "alpha": ["alpha", "beta", "gamma", "enemy"],
        "beta": ["beta", "gamma", "alpha", "enemy"],
    }
    recorded: list[tuple[str, tuple[str, ...]]] = []

    def fake_process_buff(
        buff_0: Buff,
        _sub_exist_buff_dict: dict[str, Buff],
        _mission: LoadingMission,
        _time_now: int,
        selected_characters: Any,
        *_args: Any,
        **_kwargs: Any,
    ) -> None:
        recorded.append((buff_0.ft.index, tuple(selected_characters)))

    def fail_buff_go_to(*_args: Any, **_kwargs: Any) -> None:
        raise AssertionError("indexed execution should use precomputed beneficiaries")

    monkeypatch.setattr(bl, "process_buff", fake_process_buff)

    sim = SimpleNamespace(
        use_indexed_buff_load_loop=True,
        _buff_runtime_rebuild_counts={},
    )
    sim._buff_load_candidate_index = BuffLoadCandidateIndex(
        registry,
        ["alpha", "beta"],
        all_name_order_box,
    )
    monkeypatch.setattr(bl, "buff_go_to", fail_buff_go_to)

    BuffLoadLoop(
        1,
        {"alpha-1": _mission("alpha", skill_type="attack")},
        BuffTemplateRegistry(registry),
        ["alpha", "beta"],
        PendingBuffQueue({"alpha": [], "beta": [], "gamma": [], "enemy": []}),
        all_name_order_box,
        sim_instance=sim,
    )

    assert recorded == [
        ("match-attack", ("alpha", "beta")),
        ("fallback-complex", ("alpha", "enemy")),
        ("backend-active", ("beta", "alpha")),
    ]
    assert sim._buff_load_loop_scan_metrics["candidate_plan_mismatch_count"] == 0
    assert sim._buff_load_loop_scan_metrics["fallback_candidate_count"] == 1
