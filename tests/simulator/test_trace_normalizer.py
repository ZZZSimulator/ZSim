from __future__ import annotations

from zsim.utils.trace_normalizer import (
    TraceEvent,
    build_trace_summary,
    diff_traces,
    normalize_trace_text,
)


def test_trace_normalizer_extracts_core_tick_events() -> None:
    events = normalize_trace_text(
        "\n".join(
            [
                "[PRELOAD]:In tick: 3645, 1361_QTE has been preloaded",
                "[Skill LOAD]:3645:1361_QTE开始并拆分子任务。",
                "[Buff END]:3783:enemy 的 Buff-角色-扳机-核心被动-失衡易伤 结束，已从动态列表移除",
                "[Dot END]:4110:Shock结束，已从动态列表移除",
                "unrelated line",
            ]
        )
    )

    assert events == [
        TraceEvent(3645, "load", "skill-load", "1361_QTE", "qte"),
        TraceEvent(3645, "preload", "preloaded", "1361_QTE", "qte"),
        TraceEvent(3783, "buff", "end", "enemy 的 Buff-角色-扳机-核心被动-失衡易伤"),
        TraceEvent(4110, "dot", "end", "Shock"),
    ]


def test_trace_diff_reports_multiset_mismatches() -> None:
    baseline = [
        TraceEvent(10, "load", "skill-load", "A"),
        TraceEvent(10, "load", "skill-load", "A"),
    ]
    candidate = [TraceEvent(10, "load", "skill-load", "A")]

    diff = diff_traces(baseline, candidate)

    assert not diff.matches
    assert diff.mismatch_count == 1
    assert diff.baseline_only == [TraceEvent(10, "load", "skill-load", "A")]
    assert diff.candidate_only == []


def test_trace_summary_counts_domains_and_tick_bounds() -> None:
    summary = build_trace_summary(
        [
            TraceEvent(5, "preload", "preloaded", "A"),
            TraceEvent(8, "buff", "end", "B"),
        ]
    )

    assert summary["event_count"] == 2
    assert summary["tick_min"] == 5
    assert summary["tick_max"] == 8
    assert summary["by_domain"] == {"buff": 1, "preload": 1}


def test_trace_normalizer_extracts_extended_action_domains_and_ignores_noise() -> None:
    events = normalize_trace_text(
        "\n".join(
            [
                "[Skill INFO]:1361_QTE diagnostic table",
                "[CHAR STATUS]:扳机:{'noise': True}",
                "[PRELOAD]:In tick: 30, 1261_dodge has been preloaded",
                "[Skill LOAD]:31:1401_parry开始并拆分子任务。",
                "[Skill LOAD]:32:1311_BH_Aid已经结束,已从Load中移除",
                "[Skill LOAD]:33:swap_to_1401开始并拆分子任务。",
                "由【柳】的【1221_E_EX】技能触发了紊乱！【感电】属性的异常状态提前结束！",
                "[Dot END]:40:Shock结束，已从动态列表移除",
            ]
        )
    )

    assert events == [
        TraceEvent(30, "preload", "preloaded", "1261_dodge", "dodge"),
        TraceEvent(31, "load", "skill-load", "1401_parry", "parry"),
        TraceEvent(32, "load", "skill-end", "1311_BH_Aid", "assist"),
        TraceEvent(33, "load", "skill-load", "swap_to_1401", "swap"),
        TraceEvent(40, "dot", "end", "Shock"),
    ]

    summary = build_trace_summary(events)
    assert summary["by_action_domain"] == {
        "assist": 1,
        "dodge": 1,
        "parry": 1,
        "swap": 1,
    }
