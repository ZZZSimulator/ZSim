from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pandas as pd

from zsim.sim_progress.Buff import BuffLoad as bl
from zsim.sim_progress.Buff.buff_class import Buff
from zsim.sim_progress.Buff.BuffLoad import BuffLoadCandidateIndex, BuffLoadLoop
from zsim.sim_progress.Load import LoadingMission
from zsim.sim_progress.ScheduledEvent.buff_runtime import (
    BuffTemplateRegistry,
    PendingBuffQueue,
)


def _buff(
    index: str,
    *,
    operator: str = "alpha",
    add_buff_to: int = 1000,
    simple_judge_logic: bool = True,
    simple_effect_logic: bool = True,
    schedule_judge: bool = False,
    passively_updating: bool = False,
    backend_acitve: bool = True,
    alltime: bool = False,
) -> Buff:
    buff = Buff.__new__(Buff)
    buff.ft = SimpleNamespace(
        index=index,
        operator=operator,
        add_buff_to=add_buff_to,
        schedule_judge=schedule_judge,
        passively_updating=passively_updating,
        backend_acitve=backend_acitve,
        alltime=alltime,
        simple_judge_logic=simple_judge_logic,
        simple_start_logic=True,
        simple_hit_logic=True,
        simple_end_logic=True,
        simple_effect_logic=simple_effect_logic,
        simple_exit_logic=True,
    )
    buff.logic = SimpleNamespace(xjudge=None, xeffect=None)
    return buff


def _mission(
    actor: str,
    *,
    skill_type: str = "attack",
    element_type: int = 1,
    labels: dict[str, int] | None = None,
    trigger_buff_level: int = 0,
    skill_tag: str | None = None,
    mission_tag: str | None = None,
) -> LoadingMission:
    skill = SimpleNamespace(
        skill_type=skill_type,
        element_type=element_type,
        labels=labels or {},
        trigger_buff_level=trigger_buff_level,
        ticks=1,
        tick_list=[],
    )
    node = SimpleNamespace(
        preload_tick=0,
        end_tick=1,
        skill_tag=skill_tag or f"{actor}-skill",
        char_name=actor,
        skill=skill,
        element_type=element_type,
        hit_times=1,
    )
    mission = LoadingMission(node)
    mission.mission_dict = {1: "hit"}
    if mission_tag is not None:
        mission.mission_tag = mission_tag
    return mission


def _patch_judge_file(monkeypatch) -> None:
    judge_file = pd.DataFrame.from_dict(
        {
            "match-attack": {"SkillType": "attack", "ElementType": None},
            "mismatch-defense": {"SkillType": "defense", "ElementType": None},
            "match-fire": {"SkillType": None, "ElementType": 1},
            "empty-simple": {"SkillType": None, "ElementType": None},
            "fallback-complex": {"SkillType": "defense", "ElementType": None},
            "schedule": {"SkillType": "attack", "ElementType": None},
            "passive": {"SkillType": "attack", "ElementType": None},
            "backend-inactive": {"SkillType": "attack", "ElementType": None},
            "backend-active": {"SkillType": "attack", "ElementType": None},
        },
        orient="index",
    )
    monkeypatch.setattr(bl, "JUDGE_FILE", judge_file)
    monkeypatch.setattr(
        bl,
        "BUFF_LOADING_CONDITION_TRANSLATION_DICT",
        {
            "SkillType": "skill_type",
            "ElementType": "element_type",
        },
    )


def _records_like_buffjudge(buff: Buff, mission: LoadingMission) -> bool:
    if buff.ft.alltime:
        return True
    if not buff.ft.simple_judge_logic or not buff.ft.simple_effect_logic:
        return True
    judge_condition_dict = dict(bl.JUDGE_FILE.loc[buff.ft.index])
    if not any(value if value is None else True for value in judge_condition_dict.values()):
        return False
    return bl.simple_string_judge(judge_condition_dict, mission.mission_node.skill)


def test_simple_judge_mismatches_are_skipped(monkeypatch) -> None:
    _patch_judge_file(monkeypatch)
    registry = {
        "alpha": {
            "match-attack": _buff("match-attack"),
            "mismatch-defense": _buff("mismatch-defense"),
        },
        "enemy": {},
    }
    index = BuffLoadCandidateIndex(registry, ["alpha"])

    selection = index.select_candidates(
        processor="on_field",
        owner="alpha",
        mission=_mission("alpha", skill_type="attack"),
    )

    assert selection.candidate_keys == ("match-attack",)
    assert selection.full_scan_candidate_count == 2
    assert selection.selected_candidate_count == 1
    assert selection.skipped_candidate_count == 1
    assert selection.fallback_candidate_count == 0


def test_candidate_selection_reuses_static_mission_signature_cache(monkeypatch) -> None:
    _patch_judge_file(monkeypatch)
    registry = {
        "alpha": {
            "match-attack": _buff("match-attack"),
            "mismatch-defense": _buff("mismatch-defense"),
        },
        "enemy": {},
    }
    index = BuffLoadCandidateIndex(registry, ["alpha"])
    first_mission = _mission("alpha", skill_type="attack")
    second_mission = _mission("alpha", skill_type="attack")

    first_selection = index.select_candidates(
        processor="on_field",
        owner="alpha",
        mission=first_mission,
    )
    assert len(index._selection_cache) == 1

    second_selection = index.select_candidates(
        processor="on_field",
        owner="alpha",
        mission=second_mission,
    )

    assert second_selection.candidate_keys == first_selection.candidate_keys
    assert second_selection.skipped_candidate_count == first_selection.skipped_candidate_count
    assert second_selection.mission is second_mission
    assert len(index._selection_cache) == 1


def test_candidate_index_registry_match_fast_path_detects_shape_changes(monkeypatch) -> None:
    _patch_judge_file(monkeypatch)
    registry = {
        "alpha": {
            "match-attack": _buff("match-attack"),
        },
        "enemy": {},
    }
    index = BuffLoadCandidateIndex(registry, ["alpha"])

    assert index.matches_registry(registry, ["alpha"])
    assert not index.matches_registry(registry, ["beta"])

    registry["alpha"]["match-fire"] = _buff("match-fire")

    assert not index.matches_registry(registry, ["alpha"])


def test_uncertain_or_complex_candidates_remain_in_fallback(monkeypatch) -> None:
    _patch_judge_file(monkeypatch)
    registry = {
        "alpha": {
            "fallback-complex": _buff(
                "fallback-complex",
                simple_judge_logic=False,
                simple_effect_logic=False,
            ),
            "empty-simple": _buff("empty-simple"),
        },
        "enemy": {},
    }
    index = BuffLoadCandidateIndex(registry, ["alpha"])

    selection = index.select_candidates(
        processor="on_field",
        owner="alpha",
        mission=_mission("alpha", skill_type="attack"),
    )

    assert selection.candidate_keys == ("fallback-complex",)
    assert selection.fallback_candidate_count == 1
    assert selection.skipped_candidate_count == 1


def test_complex_prefilters_skip_only_failed_necessary_conditions(monkeypatch) -> None:
    _patch_judge_file(monkeypatch)
    registry = {
        "alpha": {
            "Buff-角色-扳机-核心被动-失衡易伤": _buff(
                "Buff-角色-扳机-核心被动-失衡易伤",
                simple_judge_logic=False,
                simple_effect_logic=False,
            ),
            "Buff-武器-精5索魂影眸-减防": _buff(
                "Buff-武器-精5索魂影眸-减防",
                simple_judge_logic=False,
                simple_effect_logic=False,
            ),
            "Buff-角色-仪玄-2画-失衡时间提升": _buff(
                "Buff-角色-仪玄-2画-失衡时间提升",
                simple_judge_logic=False,
                simple_effect_logic=False,
            ),
        },
        "enemy": {},
    }
    index = BuffLoadCandidateIndex(registry, ["alpha"])

    skipped_selection = index.select_candidates(
        processor="on_field",
        owner="alpha",
        mission=_mission("alpha", skill_tag="alpha-skill", element_type=1),
    )
    aftershock_selection = index.select_candidates(
        processor="on_field",
        owner="alpha",
        mission=_mission(
            "alpha",
            skill_tag="1361_CoAttack_A",
            element_type=3,
            labels={"aftershock_attack": 1},
        ),
    )
    yixuan_q_selection = index.select_candidates(
        processor="on_field",
        owner="alpha",
        mission=_mission("alpha", skill_tag="1371_Q", element_type=1),
    )

    assert skipped_selection.candidate_keys == ()
    assert skipped_selection.skipped_candidate_count == 3
    assert aftershock_selection.candidate_keys == (
        "Buff-角色-扳机-核心被动-失衡易伤",
        "Buff-武器-精5索魂影眸-减防",
    )
    assert aftershock_selection.fallback_candidate_count == 2
    assert yixuan_q_selection.candidate_keys == ("Buff-角色-仪玄-2画-失衡时间提升",)


def test_named_complex_prefilters_keep_only_required_mission_shapes(monkeypatch) -> None:
    _patch_judge_file(monkeypatch)
    registry = {
        "仪玄": {
            "Buff-角色-仪玄-1画-落雷触发器": _buff(
                "Buff-角色-仪玄-1画-落雷触发器",
                operator="仪玄",
                simple_judge_logic=False,
                simple_effect_logic=False,
            ),
            "Buff-角色-仪玄-4画-静心": _buff(
                "Buff-角色-仪玄-4画-静心",
                operator="仪玄",
                simple_judge_logic=False,
                simple_effect_logic=False,
            ),
        },
        "耀嘉音": {
            "Buff-角色-耀佳音-震音管理器-触发器": _buff(
                "Buff-角色-耀佳音-震音管理器-触发器",
                operator="耀嘉音",
                simple_judge_logic=False,
                simple_effect_logic=False,
            ),
        },
        "扳机": {
            "Buff-角色-扳机-1画-失衡易伤提升": _buff(
                "Buff-角色-扳机-1画-失衡易伤提升",
                operator="扳机",
                simple_judge_logic=False,
                simple_effect_logic=False,
            ),
        },
        "enemy": {},
    }
    index = BuffLoadCandidateIndex(registry, ["仪玄", "耀嘉音", "扳机"])

    yixuan_self_selection = index.select_candidates(
        processor="on_field",
        owner="仪玄",
        mission=_mission("仪玄", skill_tag="1371_NA"),
    )
    yixuan_c4_selection = index.select_candidates(
        processor="on_field",
        owner="仪玄",
        mission=_mission("仪玄", skill_tag="1371_Q", trigger_buff_level=6),
    )
    yixuan_teammate_selection = index.select_candidates(
        processor="backend",
        owner="仪玄",
        mission=_mission("扳机", skill_tag="1361_CoAttack_A"),
    )
    astra_selection = index.select_candidates(
        processor="on_field",
        owner="耀嘉音",
        mission=_mission("耀嘉音", skill_tag="1311_QTE", trigger_buff_level=5),
    )
    trigger_aftershock_selection = index.select_candidates(
        processor="on_field",
        owner="扳机",
        mission=_mission(
            "扳机",
            skill_tag="1361_CoAttack_A",
            labels={"aftershock_attack": 1},
        ),
    )

    assert yixuan_self_selection.candidate_keys == ()
    assert yixuan_self_selection.skipped_candidate_count == 2
    assert yixuan_c4_selection.candidate_keys == ("Buff-角色-仪玄-4画-静心",)
    assert yixuan_teammate_selection.candidate_keys == ("Buff-角色-仪玄-1画-落雷触发器",)
    assert astra_selection.candidate_keys == ("Buff-角色-耀佳音-震音管理器-触发器",)
    assert trigger_aftershock_selection.candidate_keys == ("Buff-角色-扳机-1画-失衡易伤提升",)


def test_complex_effect_with_simple_judge_can_still_be_statically_skipped(
    monkeypatch,
) -> None:
    _patch_judge_file(monkeypatch)
    registry = {
        "alpha": {
            "mismatch-defense": _buff(
                "mismatch-defense",
                simple_judge_logic=True,
                simple_effect_logic=False,
            ),
            "match-attack": _buff(
                "match-attack",
                simple_judge_logic=True,
                simple_effect_logic=False,
            ),
        },
        "enemy": {},
    }
    index = BuffLoadCandidateIndex(registry, ["alpha"])

    selection = index.select_candidates(
        processor="on_field",
        owner="alpha",
        mission=_mission("alpha", skill_type="attack"),
    )

    assert selection.candidate_keys == ("match-attack",)
    assert selection.skipped_candidate_count == 1
    assert selection.fallback_candidate_count == 0


def test_schedule_passive_and_backend_rules_are_preserved(monkeypatch) -> None:
    _patch_judge_file(monkeypatch)
    registry = {
        "alpha": {
            "schedule": _buff("schedule", schedule_judge=True),
            "passive": _buff("passive", passively_updating=True),
            "backend-inactive": _buff("backend-inactive", backend_acitve=False),
            "backend-active": _buff("backend-active", backend_acitve=True),
        },
        "enemy": {},
    }
    index = BuffLoadCandidateIndex(registry, ["alpha"])
    mission = _mission("beta", skill_type="attack")

    backend_selection = index.select_candidates(
        processor="backend",
        owner="alpha",
        mission=mission,
    )
    on_field_selection = index.select_candidates(
        processor="on_field",
        owner="alpha",
        mission=_mission("alpha", skill_type="attack"),
    )

    assert backend_selection.candidate_keys == ("backend-active",)
    assert backend_selection.skipped_candidate_count == 3
    assert on_field_selection.candidate_keys == ("backend-inactive", "backend-active")
    assert on_field_selection.skipped_candidate_count == 2


def test_indexed_loop_matches_full_scan_fixture_and_records_skip_metrics(
    monkeypatch,
) -> None:
    _patch_judge_file(monkeypatch)
    registry = {
        "alpha": {
            "match-attack": _buff("match-attack", operator="alpha"),
            "mismatch-defense": _buff("mismatch-defense", operator="alpha"),
            "fallback-complex": _buff(
                "fallback-complex",
                operator="alpha",
                simple_judge_logic=False,
                simple_effect_logic=False,
            ),
            "schedule": _buff("schedule", operator="alpha", schedule_judge=True),
            "passive": _buff("passive", operator="alpha", passively_updating=True),
        },
        "beta": {
            "backend-active": _buff("backend-active", operator="beta", backend_acitve=True),
            "backend-inactive": _buff(
                "backend-inactive",
                operator="beta",
                backend_acitve=False,
            ),
        },
        "enemy": {},
    }
    all_name_order_box = {
        "alpha": ["alpha", "beta", "enemy"],
        "beta": ["beta", "alpha", "enemy"],
    }
    load_mission_dict = {"alpha-1": _mission("alpha", skill_type="attack")}
    recorded: list[tuple[str, str]] = []

    def fake_process_buff(
        buff_0: Buff,
        sub_exist_buff_dict: dict[str, Buff],
        mission: LoadingMission,
        *_args: Any,
        **_kwargs: Any,
    ) -> None:
        assert buff_0.ft.index in sub_exist_buff_dict
        if _records_like_buffjudge(buff_0, mission):
            recorded.append((mission.mission_character, buff_0.ft.index))

    monkeypatch.setattr(bl, "process_buff", fake_process_buff)

    full_scan_sim = SimpleNamespace(use_indexed_buff_load_loop=False)
    BuffLoadLoop(
        1,
        load_mission_dict,
        BuffTemplateRegistry(registry),
        ["alpha", "beta"],
        PendingBuffQueue({"alpha": [], "beta": [], "enemy": []}),
        all_name_order_box,
        sim_instance=full_scan_sim,
    )
    full_scan_records = list(recorded)

    recorded.clear()
    indexed_sim = SimpleNamespace(
        use_indexed_buff_load_loop=True,
        _buff_runtime_rebuild_counts={},
    )
    BuffLoadLoop(
        1,
        load_mission_dict,
        BuffTemplateRegistry(registry),
        ["alpha", "beta"],
        PendingBuffQueue({"alpha": [], "beta": [], "enemy": []}),
        all_name_order_box,
        sim_instance=indexed_sim,
    )

    assert recorded == full_scan_records
    assert indexed_sim._buff_load_loop_scan_metrics["full_scan_candidate_count"] == 7
    assert indexed_sim._buff_load_loop_scan_metrics["trigger_candidate_count"] == 3
    assert indexed_sim._buff_load_loop_scan_metrics["selected_candidate_count"] == 3
    assert indexed_sim._buff_load_loop_scan_metrics["skipped_candidate_count"] == 4
    assert indexed_sim._buff_load_loop_scan_metrics["fallback_candidate_count"] == 1
    assert indexed_sim._buff_load_loop_scan_metrics["candidate_plan_count"] == 7
    assert indexed_sim._buff_load_loop_scan_metrics["candidate_plan_mismatch_count"] == 0


def test_simple_effect_buff_skips_judge_when_no_sub_mission_is_due(monkeypatch) -> None:
    buff = _buff("match-attack")
    mission = _mission("alpha", skill_type="attack")
    mission.mission_dict = {5: "hit"}
    pending_queue = PendingBuffQueue({"alpha": [], "enemy": []})

    def fail_buff_initialize(*_args: Any, **_kwargs: Any) -> None:
        raise AssertionError("simple-effect buff without due mission should not judge")

    monkeypatch.setattr(bl, "BuffInitialize", fail_buff_initialize)

    bl.process_buff(
        buff,
        {"match-attack": buff},
        mission,
        1,
        ["alpha"],
        pending_queue,
        {"alpha": {"match-attack": buff}, "enemy": {}},
        sim_instance=SimpleNamespace(),
    )

    assert pending_queue.count() == 0
