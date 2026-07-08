from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Literal

import polars as pl
import pytest

from zsim.utils import main_loop_consistency as mlc
from zsim.utils import runtime_benchmark as rb
from zsim.utils.runtime_benchmark import (
    RuntimeBenchmarkSnapshot,
    build_parser,
    build_repeat_runtime_benchmark_summary,
    build_runtime_benchmark_report,
    run_repeated_runtime_benchmark,
    run_runtime_benchmark,
)


def test_build_runtime_benchmark_report_keeps_required_json_fields():
    baseline_snapshot = RuntimeBenchmarkSnapshot(
        runtime_label="default-current",
        session_id="1",
        total_runtime_ms=120.5,
        hotspots={
            "simulator_run_ms": 100.0,
            "damage_report_ms": 15.0,
            "buff_report_ms": 5.5,
        },
    )
    new_buff_snapshot = RuntimeBenchmarkSnapshot(
        runtime_label="new-buff",
        session_id="2",
        total_runtime_ms=100.0,
        hotspots={
            "simulator_run_ms": 80.0,
            "damage_report_ms": 14.0,
            "buff_report_ms": 6.0,
        },
    )

    assert baseline_snapshot.rebuild_counts is None
    assert new_buff_snapshot.rebuild_counts is None
    assert baseline_snapshot.buff_load_loop_scan_metrics is None
    assert new_buff_snapshot.buff_load_loop_scan_metrics is None

    report = build_runtime_benchmark_report(
        team="team-a",
        apl="./zsim/data/APLData/example.toml",
        stop_tick=120,
        baseline_snapshot=baseline_snapshot,
        new_buff_snapshot=new_buff_snapshot,
    )

    assert report["team"] == "team-a"
    assert report["apl"] == "./zsim/data/APLData/example.toml"
    assert report["stop_tick"] == 120
    assert report["runtime_selection"]["mode"] == "label-only-current-runtime"
    assert report["baseline_runtime"] == "default-current"
    assert report["new_buff_runtime"] == "new-buff"
    assert "legacy_runtime" not in report
    assert "candidate_runtime" not in report
    assert "report_compatibility" not in report
    assert report["total_runtime_ms"] == {
        "baseline": 120.5,
        "new_buff": 100.0,
    }
    assert report["hotspots"]["baseline"][0]["name"] == "simulator_run_ms"
    assert report["hotspots"]["new_buff"][0]["runtime_ms"] == 80.0
    assert report["comparisons"]["total_runtime_ms"] == -20.5
    assert report["comparisons"]["hotspots"]["simulator_run_ms"] == -20.0
    assert report["comparisons"]["faster_runtime"] == "new-buff"
    assert report["comparisons"]["new_buff_vs_baseline_ratio"] == 0.8299
    assert "buff_runtime_rebuild_counts" not in report
    assert "buff_runtime_rebuild_counts" not in report["comparisons"]
    assert "buff_load_loop_scan_metrics" not in report
    assert "buff_load_loop_scan_metrics" not in report["comparisons"]


def test_build_runtime_benchmark_report_includes_rebuild_counts_when_opted_in():
    baseline_snapshot = RuntimeBenchmarkSnapshot(
        runtime_label="baseline",
        session_id="1",
        total_runtime_ms=120.5,
        hotspots={
            "simulator_run_ms": 100.0,
            "damage_report_ms": 15.0,
            "buff_report_ms": 5.5,
        },
    )
    new_buff_snapshot = RuntimeBenchmarkSnapshot(
        runtime_label="new-buff",
        session_id="2",
        total_runtime_ms=100.0,
        hotspots={
            "simulator_run_ms": 80.0,
            "damage_report_ms": 14.0,
            "buff_report_ms": 6.0,
        },
    )

    report = build_runtime_benchmark_report(
        team="team-a",
        apl="./zsim/data/APLData/example.toml",
        stop_tick=120,
        baseline_snapshot=baseline_snapshot,
        new_buff_snapshot=new_buff_snapshot,
        include_rebuild_counts=True,
        buff_runtime_rebuild_counts={
            "baseline": {
                "buff_load_loop": 5,
                "scheduled_event": 2,
            },
            "new_buff": {
                "scheduled_event": 4,
                "scheduled_event_runtime_ports": 7,
            },
        },
        buff_load_loop_scan_metrics={
            "baseline": {
                "processed_tick_count": 3,
                "mission_count": 9,
                "trigger_candidate_count": 30,
                "full_scan_candidate_count": 30,
                "selected_candidate_count": 30,
                "skipped_candidate_count": 0,
                "fallback_candidate_count": 0,
                "candidate_plan_count": 30,
                "candidate_plan_mismatch_count": 0,
            },
            "new_buff": {
                "processed_tick_count": 3,
                "mission_count": 9,
                "trigger_candidate_count": 42,
                "full_scan_candidate_count": 50,
                "selected_candidate_count": 42,
                "skipped_candidate_count": 8,
                "fallback_candidate_count": 6,
                "candidate_plan_count": 50,
                "candidate_plan_mismatch_count": 0,
            },
        },
    )

    assert report["buff_runtime_rebuild_counts"] == {
        "baseline": {
            "buff_load_loop": 5,
            "scheduled_event": 2,
        },
        "new_buff": {
            "scheduled_event": 4,
            "scheduled_event_runtime_ports": 7,
        },
    }
    assert report["comparisons"]["buff_runtime_rebuild_counts"] == {
        "buff_load_loop": -5,
        "scheduled_event": 2,
        "scheduled_event_runtime_ports": 7,
    }
    assert report["buff_load_loop_scan_metrics"] == {
        "baseline": {
            "candidate_plan_count": 30,
            "candidate_plan_mismatch_count": 0,
            "fallback_candidate_count": 0,
            "full_scan_candidate_count": 30,
            "processed_tick_count": 3,
            "mission_count": 9,
            "selected_candidate_count": 30,
            "skipped_candidate_count": 0,
            "trigger_candidate_count": 30,
        },
        "new_buff": {
            "candidate_plan_count": 50,
            "candidate_plan_mismatch_count": 0,
            "fallback_candidate_count": 6,
            "full_scan_candidate_count": 50,
            "processed_tick_count": 3,
            "mission_count": 9,
            "selected_candidate_count": 42,
            "skipped_candidate_count": 8,
            "trigger_candidate_count": 42,
        },
    }
    assert report["comparisons"]["buff_load_loop_scan_metrics"] == {
        "candidate_plan_count": 20,
        "candidate_plan_mismatch_count": 0,
        "fallback_candidate_count": 6,
        "full_scan_candidate_count": 20,
        "mission_count": 0,
        "processed_tick_count": 0,
        "selected_candidate_count": 12,
        "skipped_candidate_count": 8,
        "trigger_candidate_count": 12,
    }


def test_build_parser_accepts_required_cli_flags():
    parser = build_parser()

    args = parser.parse_args(
        [
            "--team",
            "team-a",
            "--apl",
            "./zsim/data/APLData/example.toml",
            "--stop-tick",
            "240",
            "--baseline-runtime",
            "default-a",
            "--new-buff-runtime",
            "new-buff-b",
            "--json",
            "--include-rebuild-counts",
            "--new-buff-use-indexed-buff-load-loop",
            "--repeat-samples",
            "3",
            "--summary-json",
            "scripts/ralph/benchmarks/repeat-summary.json",
        ]
    )
    repeat_alias_args = parser.parse_args(
        [
            "--team",
            "team-a",
            "--repeat",
            "4",
        ]
    )
    with pytest.raises(SystemExit):
        parser.parse_args(["--team", "team-a", "--legacy-runtime", "legacy-a"])
    with pytest.raises(SystemExit):
        parser.parse_args(["--team", "team-a", "--candidate-runtime", "candidate-b"])

    assert args.team == "team-a"
    assert args.apl == "./zsim/data/APLData/example.toml"
    assert args.stop_tick == 240
    assert args.baseline_runtime == "default-a"
    assert args.new_buff_runtime == "new-buff-b"
    assert repeat_alias_args.repeat_samples == 4
    assert not hasattr(args, "legacy_runtime")
    assert not hasattr(args, "candidate_runtime")
    assert args.json is True
    assert args.include_rebuild_counts is True
    assert args.new_buff_use_indexed_buff_load_loop is True
    assert args.repeat_samples == 3
    assert args.summary_json == "scripts/ralph/benchmarks/repeat-summary.json"
    help_text = parser.format_help()
    assert "--baseline-runtime" in help_text
    assert "--new-buff-runtime" in help_text
    assert "--legacy-runtime" not in help_text
    assert "--candidate-runtime" not in help_text
    assert "Compatibility alias" not in help_text


def _repeat_sample_report(
    *,
    baseline_simulator_ms: float,
    new_buff_simulator_ms: float,
    baseline_counts: dict[str, int] | None = None,
    new_buff_counts: dict[str, int] | None = None,
    baseline_scan_metrics: dict[str, int] | None = None,
    new_buff_scan_metrics: dict[str, int] | None = None,
) -> dict[str, Any]:
    report: dict[str, Any] = {
        "team": "fake-team",
        "apl": "./fake.toml",
        "stop_tick": 120,
        "baseline_runtime": "default-label",
        "new_buff_runtime": "new-buff-label",
        "runtime_selection": {"mode": "label-only-current-runtime"},
        "total_runtime_ms": {
            "baseline": baseline_simulator_ms + 20.0,
            "new_buff": new_buff_simulator_ms + 20.0,
        },
        "hotspots": {
            "baseline": [
                {"name": "simulator_run_ms", "runtime_ms": baseline_simulator_ms},
                {"name": "damage_report_ms", "runtime_ms": 15.0},
                {"name": "buff_report_ms", "runtime_ms": 5.0},
            ],
            "new_buff": [
                {"name": "simulator_run_ms", "runtime_ms": new_buff_simulator_ms},
                {"name": "damage_report_ms", "runtime_ms": 15.0},
                {"name": "buff_report_ms", "runtime_ms": 5.0},
            ],
        },
        "comparisons": {
            "total_runtime_ms": new_buff_simulator_ms - baseline_simulator_ms,
            "hotspots": {
                "simulator_run_ms": new_buff_simulator_ms - baseline_simulator_ms,
            },
            "faster_runtime": "new-buff-label",
            "new_buff_vs_baseline_ratio": 1.0,
        },
    }
    if baseline_counts is not None or new_buff_counts is not None:
        report["buff_runtime_rebuild_counts"] = {
            "baseline": baseline_counts or {},
            "new_buff": new_buff_counts or {},
        }
        report["comparisons"]["buff_runtime_rebuild_counts"] = {}
    if baseline_scan_metrics is not None or new_buff_scan_metrics is not None:
        report["buff_load_loop_scan_metrics"] = {
            "baseline": baseline_scan_metrics or {},
            "new_buff": new_buff_scan_metrics or {},
        }
        report["comparisons"]["buff_load_loop_scan_metrics"] = {}
    return report


def test_build_repeat_runtime_benchmark_summary_records_shape_policy_and_counts():
    reports = [
        _repeat_sample_report(
            baseline_simulator_ms=100.0,
            new_buff_simulator_ms=94.0,
            baseline_counts={"buff_load_loop": 1},
            new_buff_counts={"buff_load_loop": 2, "scheduled_event": 2},
            baseline_scan_metrics={
                "processed_tick_count": 1,
                "trigger_candidate_count": 10,
                "full_scan_candidate_count": 10,
                "selected_candidate_count": 10,
                "skipped_candidate_count": 0,
                "fallback_candidate_count": 0,
                "candidate_plan_count": 10,
                "candidate_plan_mismatch_count": 0,
            },
            new_buff_scan_metrics={
                "processed_tick_count": 1,
                "trigger_candidate_count": 12,
                "full_scan_candidate_count": 15,
                "selected_candidate_count": 12,
                "skipped_candidate_count": 3,
                "fallback_candidate_count": 2,
                "candidate_plan_count": 15,
                "candidate_plan_mismatch_count": 0,
            },
        ),
        _repeat_sample_report(
            baseline_simulator_ms=104.0,
            new_buff_simulator_ms=98.0,
            baseline_counts={"buff_load_loop": 3},
            new_buff_counts={"buff_load_loop": 3},
            baseline_scan_metrics={
                "processed_tick_count": 1,
                "trigger_candidate_count": 14,
                "full_scan_candidate_count": 14,
                "selected_candidate_count": 14,
                "skipped_candidate_count": 0,
                "fallback_candidate_count": 0,
                "candidate_plan_count": 14,
                "candidate_plan_mismatch_count": 0,
            },
            new_buff_scan_metrics={
                "processed_tick_count": 1,
                "trigger_candidate_count": 18,
                "full_scan_candidate_count": 21,
                "selected_candidate_count": 18,
                "skipped_candidate_count": 3,
                "fallback_candidate_count": 1,
                "candidate_plan_count": 21,
                "candidate_plan_mismatch_count": 0,
            },
        ),
        _repeat_sample_report(
            baseline_simulator_ms=102.0,
            new_buff_simulator_ms=96.0,
            baseline_counts={"buff_load_loop": 2},
            new_buff_counts={"buff_load_loop": 4, "scheduled_event": 4},
            baseline_scan_metrics={
                "processed_tick_count": 1,
                "trigger_candidate_count": 12,
                "full_scan_candidate_count": 12,
                "selected_candidate_count": 12,
                "skipped_candidate_count": 0,
                "fallback_candidate_count": 0,
                "candidate_plan_count": 12,
                "candidate_plan_mismatch_count": 0,
            },
            new_buff_scan_metrics={
                "processed_tick_count": 1,
                "trigger_candidate_count": 16,
                "full_scan_candidate_count": 20,
                "selected_candidate_count": 16,
                "skipped_candidate_count": 4,
                "fallback_candidate_count": 1,
                "candidate_plan_count": 20,
                "candidate_plan_mismatch_count": 0,
            },
        ),
    ]

    summary = build_repeat_runtime_benchmark_summary(
        reports=reports,
        include_rebuild_counts=True,
    )

    assert summary["schema"] == "zsim-buff-runtime-repeat-benchmark.v1"
    assert summary["sample_count"] == 3
    assert summary["repeat_samples"] == 3
    assert summary["team"] == "fake-team"
    assert summary["apl"] == "./fake.toml"
    assert summary["stop_tick"] == 120
    assert summary["runtime_labels"] == {
        "baseline": "default-label",
        "new_buff": "new-buff-label",
    }
    assert summary["runtime_selection"]["mode"] == "label-only-current-runtime"
    assert summary["opt_in_flag_status"] == {
        "new_buff_use_indexed_buff_load_loop": False,
        "default_off": True,
        "default_indexed_execution": "blocked",
    }
    assert summary["simulator_runtime_ms"]["baseline"] == {
        "median": 102.0,
        "min": 100.0,
        "max": 104.0,
        "range": 4.0,
        "samples": [100.0, 104.0, 102.0],
    }
    assert summary["simulator_runtime_ms"]["new_buff"] == {
        "median": 96.0,
        "min": 94.0,
        "max": 98.0,
        "range": 4.0,
        "samples": [94.0, 98.0, 96.0],
    }
    assert summary["relative_delta"] == {
        "basis": "simulator_runtime_ms.median",
        "new_buff_minus_baseline_median_ms": -6.0,
        "new_buff_vs_baseline_median_ratio": 0.941176,
        "new_buff_vs_baseline_median_relative_delta": -0.058824,
        "new_buff_vs_baseline_median_percent": -5.8824,
    }
    assert summary["rebuild_count_buckets"]["included"] is True
    assert summary["rebuild_count_buckets"]["aggregate"]["baseline"]["buff_load_loop"] == {
        "median": 2.0,
        "min": 1.0,
        "max": 3.0,
        "range": 2.0,
        "samples": [1, 3, 2],
    }
    assert summary["rebuild_count_buckets"]["aggregate"]["new_buff"]["scheduled_event"] == {
        "median": 2.0,
        "min": 0.0,
        "max": 4.0,
        "range": 4.0,
        "samples": [2, 0, 4],
    }
    assert summary["samples"][0]["scan_metric_buckets"] == {
        "baseline": {
            "candidate_plan_count": 10,
            "candidate_plan_mismatch_count": 0,
            "fallback_candidate_count": 0,
            "full_scan_candidate_count": 10,
            "processed_tick_count": 1,
            "selected_candidate_count": 10,
            "skipped_candidate_count": 0,
            "trigger_candidate_count": 10,
        },
        "new_buff": {
            "candidate_plan_count": 15,
            "candidate_plan_mismatch_count": 0,
            "fallback_candidate_count": 2,
            "full_scan_candidate_count": 15,
            "processed_tick_count": 1,
            "selected_candidate_count": 12,
            "skipped_candidate_count": 3,
            "trigger_candidate_count": 12,
        },
    }
    assert summary["scan_metric_buckets"]["included"] is True
    assert summary["scan_metric_buckets"]["aggregate"]["baseline"]["trigger_candidate_count"] == {
        "median": 12.0,
        "min": 10.0,
        "max": 14.0,
        "range": 4.0,
        "samples": [10, 14, 12],
    }
    assert summary["scan_metric_buckets"]["aggregate"]["new_buff"]["processed_tick_count"] == {
        "median": 1.0,
        "min": 1.0,
        "max": 1.0,
        "range": 0.0,
        "samples": [1, 1, 1],
    }
    assert summary["scan_metric_buckets"]["aggregate"]["new_buff"]["skipped_candidate_count"] == {
        "median": 3.0,
        "min": 3.0,
        "max": 4.0,
        "range": 1.0,
        "samples": [3, 3, 4],
    }
    assert summary["candidate_plan_metrics"] == {
        "included": True,
        "aggregate": {
            "baseline": {
                "candidate_plan_count": {
                    "median": 12.0,
                    "min": 10.0,
                    "max": 14.0,
                    "range": 4.0,
                    "samples": [10, 14, 12],
                },
                "candidate_plan_mismatch_count": {
                    "median": 0.0,
                    "min": 0.0,
                    "max": 0.0,
                    "range": 0.0,
                    "samples": [0, 0, 0],
                },
            },
            "new_buff": {
                "candidate_plan_count": {
                    "median": 20.0,
                    "min": 15.0,
                    "max": 21.0,
                    "range": 6.0,
                    "samples": [15, 21, 20],
                },
                "candidate_plan_mismatch_count": {
                    "median": 0.0,
                    "min": 0.0,
                    "max": 0.0,
                    "range": 0.0,
                    "samples": [0, 0, 0],
                },
            },
        },
    }
    assert summary["future_threshold_use"]["speedup_target_defined"] is False
    assert summary["future_threshold_use"]["minimum_repeat_samples"] == 5
    assert "does not claim a speedup target" in summary["future_threshold_use"]["rule"]
    assert summary["threshold_policy"]["minimum_repeat_samples"] == 10
    assert summary["threshold_policy"]["eligible_median_relative_delta_at_or_below"] == -0.05
    assert summary["threshold_policy"]["blocked_if_candidate_plan_mismatch_count_above"] == 0
    assert summary["threshold_policy"]["default_enablement_authorized"] is False
    assert summary["threshold_verdict"]["status"] == "needs_more_samples"
    assert (
        summary["enablement_policy"]["statement"]
        == "No default enablement or speedup target is authorized by this PRD."
    )
    assert summary["enablement_policy"]["default_enablement_authorized"] is False
    assert summary["enablement_policy"]["speedup_target_authorized"] is False
    assert summary["mismatch_counts"]["candidate_plan_mismatch_count"] == {
        "included": True,
        "baseline": {
            "median": 0.0,
            "min": 0.0,
            "max": 0.0,
            "range": 0.0,
            "samples": [0, 0, 0],
        },
        "new_buff": {
            "median": 0.0,
            "min": 0.0,
            "max": 0.0,
            "range": 0.0,
            "samples": [0, 0, 0],
        },
    }


def test_build_repeat_runtime_benchmark_summary_threshold_verdicts():
    eligible_reports = [
        _repeat_sample_report(
            baseline_simulator_ms=100.0,
            new_buff_simulator_ms=94.0,
            baseline_counts={"buff_load_loop": 1},
            new_buff_counts={"buff_load_loop": 1},
            baseline_scan_metrics={
                "candidate_plan_count": 10,
                "full_scan_candidate_count": 10,
                "trigger_candidate_count": 10,
                "selected_candidate_count": 10,
                "skipped_candidate_count": 0,
                "candidate_plan_mismatch_count": 0,
            },
            new_buff_scan_metrics={
                "candidate_plan_count": 20,
                "full_scan_candidate_count": 20,
                "trigger_candidate_count": 12,
                "selected_candidate_count": 12,
                "skipped_candidate_count": 8,
                "candidate_plan_mismatch_count": 0,
            },
        )
        for _ in range(10)
    ]

    eligible_summary = build_repeat_runtime_benchmark_summary(
        reports=eligible_reports,
        include_rebuild_counts=True,
    )

    assert eligible_summary["threshold_verdict"]["status"] == "eligible_for_enablement_prd"

    mismatched_reports = [
        _repeat_sample_report(
            baseline_simulator_ms=100.0,
            new_buff_simulator_ms=94.0,
            baseline_counts={"buff_load_loop": 1},
            new_buff_counts={"buff_load_loop": 1},
            baseline_scan_metrics={
                "candidate_plan_count": 10,
                "full_scan_candidate_count": 10,
                "trigger_candidate_count": 10,
                "selected_candidate_count": 10,
                "skipped_candidate_count": 0,
                "candidate_plan_mismatch_count": 0,
            },
            new_buff_scan_metrics={
                "candidate_plan_count": 20,
                "full_scan_candidate_count": 20,
                "trigger_candidate_count": 12,
                "selected_candidate_count": 12,
                "skipped_candidate_count": 8,
                "candidate_plan_mismatch_count": 1,
            },
        )
        for _ in range(10)
    ]

    mismatched_summary = build_repeat_runtime_benchmark_summary(
        reports=mismatched_reports,
        include_rebuild_counts=True,
    )

    assert mismatched_summary["threshold_verdict"]["status"] == "blocked"


def test_run_repeated_runtime_benchmark_preserves_contract_and_opt_in_counts(
    monkeypatch: pytest.MonkeyPatch,
):
    captured_calls: list[dict[str, Any]] = []

    def fake_run_runtime_benchmark(**kwargs: Any) -> dict[str, Any]:
        captured_calls.append(kwargs)
        sample_index = len(captured_calls)
        report = _repeat_sample_report(
            baseline_simulator_ms=100.0 + sample_index,
            new_buff_simulator_ms=90.0 + sample_index,
            baseline_counts=(
                {"buff_load_loop": sample_index} if kwargs["include_rebuild_counts"] else None
            ),
            new_buff_counts=(
                {"buff_load_loop": sample_index + 1} if kwargs["include_rebuild_counts"] else None
            ),
            baseline_scan_metrics=(
                {"processed_tick_count": sample_index} if kwargs["include_rebuild_counts"] else None
            ),
            new_buff_scan_metrics=(
                {"processed_tick_count": sample_index + 1}
                if kwargs["include_rebuild_counts"]
                else None
            ),
        )
        if kwargs["new_buff_use_indexed_buff_load_loop"]:
            report["runtime_selection"] = {
                "mode": "new-buff-explicit-opt-in-indexed-buff-load-loop",
                "new_buff_use_indexed_buff_load_loop": True,
                "default_off": True,
                "default_indexed_execution": "blocked",
            }
        return report

    monkeypatch.setattr(rb, "run_runtime_benchmark", fake_run_runtime_benchmark)

    default_summary = run_repeated_runtime_benchmark(
        team="fake-team",
        apl="./fake.toml",
        stop_tick=120,
        baseline_runtime="baseline-label",
        new_buff_runtime="new-buff-label",
        repeat_samples=2,
        include_rebuild_counts=False,
    )

    assert [call["include_rebuild_counts"] for call in captured_calls] == [False, False]
    assert [call["new_buff_use_indexed_buff_load_loop"] for call in captured_calls] == [
        False,
        False,
    ]
    assert default_summary["runtime_selection"]["mode"] == "label-only-current-runtime"
    assert default_summary["opt_in_flag_status"] == {
        "new_buff_use_indexed_buff_load_loop": False,
        "default_off": True,
        "default_indexed_execution": "blocked",
    }
    assert default_summary["repeat_samples"] == 2
    assert default_summary["rebuild_count_buckets"] == {
        "included": False,
        "samples": [],
        "aggregate": {"baseline": {}, "new_buff": {}},
    }
    assert default_summary["mismatch_counts"]["candidate_plan_mismatch_count"] == {
        "included": False,
        "baseline": {"median": 0.0, "min": 0.0, "max": 0.0, "range": 0.0, "samples": []},
        "new_buff": {"median": 0.0, "min": 0.0, "max": 0.0, "range": 0.0, "samples": []},
    }
    assert "scan_metric_buckets" not in default_summary
    assert "scan_metric_buckets" not in default_summary["samples"][0]

    captured_calls.clear()
    counted_summary = run_repeated_runtime_benchmark(
        team="fake-team",
        apl="./fake.toml",
        stop_tick=120,
        baseline_runtime="baseline-label",
        new_buff_runtime="new-buff-label",
        repeat_samples=2,
        include_rebuild_counts=True,
        new_buff_use_indexed_buff_load_loop=True,
    )

    assert [call["include_rebuild_counts"] for call in captured_calls] == [True, True]
    assert [call["new_buff_use_indexed_buff_load_loop"] for call in captured_calls] == [
        True,
        True,
    ]
    assert (
        counted_summary["runtime_selection"]["mode"]
        == "new-buff-explicit-opt-in-indexed-buff-load-loop"
    )
    assert counted_summary["opt_in_flag_status"] == {
        "new_buff_use_indexed_buff_load_loop": True,
        "default_off": True,
        "default_indexed_execution": "blocked",
    }
    assert counted_summary["rebuild_count_buckets"]["included"] is True
    assert counted_summary["rebuild_count_buckets"]["samples"] == [
        {
            "baseline": {"buff_load_loop": 1},
            "new_buff": {"buff_load_loop": 2},
        },
        {
            "baseline": {"buff_load_loop": 2},
            "new_buff": {"buff_load_loop": 3},
        },
    ]
    assert counted_summary["scan_metric_buckets"]["included"] is True
    assert counted_summary["scan_metric_buckets"]["samples"] == [
        {
            "baseline": {"processed_tick_count": 1},
            "new_buff": {"processed_tick_count": 2},
        },
        {
            "baseline": {"processed_tick_count": 2},
            "new_buff": {"processed_tick_count": 3},
        },
    ]


def test_run_runtime_benchmark_uses_runtime_labels_and_cleanup(monkeypatch: pytest.MonkeyPatch):
    snapshots_by_session: dict[str, RuntimeBenchmarkSnapshot] = {
        "101": RuntimeBenchmarkSnapshot(
            runtime_label="default-label",
            session_id="101",
            total_runtime_ms=100.0,
            hotspots={
                "simulator_run_ms": 80.0,
                "damage_report_ms": 15.0,
                "buff_report_ms": 5.0,
            },
        ),
        "102": RuntimeBenchmarkSnapshot(
            runtime_label="new-buff-label",
            session_id="102",
            total_runtime_ms=99.0,
            hotspots={
                "simulator_run_ms": 78.0,
                "damage_report_ms": 16.0,
                "buff_report_ms": 5.0,
            },
        ),
    }
    rebuild_counts_by_session = {
        "101": {"buff_load_loop": 1},
        "102": {"buff_load_loop": 3, "scheduled_event": 2},
    }
    scan_metrics_by_session = {
        "101": {
            "processed_tick_count": 2,
            "trigger_candidate_count": 10,
            "full_scan_candidate_count": 10,
            "selected_candidate_count": 10,
            "skipped_candidate_count": 0,
            "fallback_candidate_count": 0,
            "candidate_plan_count": 10,
            "candidate_plan_mismatch_count": 0,
        },
        "102": {
            "processed_tick_count": 2,
            "trigger_candidate_count": 15,
            "full_scan_candidate_count": 20,
            "selected_candidate_count": 15,
            "skipped_candidate_count": 5,
            "fallback_candidate_count": 2,
            "candidate_plan_count": 20,
            "candidate_plan_mismatch_count": 0,
        },
    }
    created_session_ids: list[str] = []
    submitted_payloads: list[tuple[dict[str, Any], int, bool, bool]] = []
    snapshot_loads: list[tuple[str, str, float, dict[str, int] | None, dict[str, int] | None]] = []
    cleaned_sessions: list[str] = []

    monkeypatch.setattr(
        rb,
        "_prepare_common_cfg",
        lambda team, apl: rb.CommonCfg.model_validate(
            {
                "session_id": "base",
                "char_config": [
                    {"name": "a"},
                    {"name": "b"},
                    {"name": "c"},
                ],
                "enemy_config": {"index_id": 11412, "adjustment_id": 22412, "difficulty": 8.74},
                "apl_path": apl or "./default.toml",
            }
        ),
    )

    session_id_iter = iter(["101", "102"])

    def fake_build_session_id() -> str:
        session_id = next(session_id_iter)
        created_session_ids.append(session_id)
        return session_id

    monkeypatch.setattr(rb, "_build_session_id", fake_build_session_id)

    class FakeFuture:
        def __init__(self, session_id: str, include_rebuild_counts: bool):
            self._session_id = session_id
            self._include_rebuild_counts = include_rebuild_counts

        def result(
            self,
        ) -> tuple[str, float, dict[str, int] | None, dict[str, int] | None]:
            rebuild_counts = None
            scan_metrics = None
            if self._include_rebuild_counts:
                rebuild_counts = dict(rebuild_counts_by_session[self._session_id])
                scan_metrics = dict(scan_metrics_by_session[self._session_id])
            return self._session_id, 88.8, rebuild_counts, scan_metrics

    class FakeExecutor:
        def __init__(self, max_workers: int):
            self.max_workers = max_workers

        def __enter__(self) -> "FakeExecutor":
            return self

        def __exit__(self, exc_type, exc, tb) -> Literal[False]:
            return False

        def submit(
            self,
            func,
            common_cfg_data,
            stop_tick,
            include_rebuild_counts=False,
            use_indexed_buff_load_loop=False,
        ):
            submitted_payloads.append(
                (
                    common_cfg_data,
                    stop_tick,
                    include_rebuild_counts,
                    use_indexed_buff_load_loop,
                )
            )
            return FakeFuture(common_cfg_data["session_id"], include_rebuild_counts)

    monkeypatch.setattr(rb, "ProcessPoolExecutor", FakeExecutor)

    def fake_load_runtime_benchmark_snapshot(
        label: str,
        sid: str,
        simulator_runtime_ms: float,
        rebuild_counts: dict[str, int] | None = None,
        scan_metrics: dict[str, int] | None = None,
    ) -> RuntimeBenchmarkSnapshot:
        snapshot_loads.append((label, sid, simulator_runtime_ms, rebuild_counts, scan_metrics))
        base_snapshot = snapshots_by_session[sid]
        return RuntimeBenchmarkSnapshot(
            runtime_label=label,
            session_id=sid,
            total_runtime_ms=base_snapshot.total_runtime_ms,
            hotspots=base_snapshot.hotspots,
            rebuild_counts=rebuild_counts,
            buff_load_loop_scan_metrics=scan_metrics,
        )

    monkeypatch.setattr(
        rb, "_load_runtime_benchmark_snapshot", fake_load_runtime_benchmark_snapshot
    )
    monkeypatch.setattr(rb, "_cleanup_result_artifacts", cleaned_sessions.append)

    report = run_runtime_benchmark(
        team="fake-team",
        apl="./override.toml",
        stop_tick=77,
        baseline_runtime="default-label",
        new_buff_runtime="new-buff-label",
        cleanup=True,
        include_rebuild_counts=True,
        new_buff_use_indexed_buff_load_loop=True,
    )

    assert created_session_ids == ["101", "102"]
    assert [payload["session_id"] for payload, _, _, _ in submitted_payloads] == ["101", "102"]
    assert all(stop_tick == 77 for _, stop_tick, _, _ in submitted_payloads)
    assert [include_counts for _, _, include_counts, _ in submitted_payloads] == [True, True]
    assert [flag for _, _, _, flag in submitted_payloads] == [False, True]
    assert snapshot_loads == [
        (
            "default-label",
            "101",
            88.8,
            {"buff_load_loop": 1},
            {
                "processed_tick_count": 2,
                "trigger_candidate_count": 10,
                "full_scan_candidate_count": 10,
                "selected_candidate_count": 10,
                "skipped_candidate_count": 0,
                "fallback_candidate_count": 0,
                "candidate_plan_count": 10,
                "candidate_plan_mismatch_count": 0,
            },
        ),
        (
            "new-buff-label",
            "102",
            88.8,
            {"buff_load_loop": 3, "scheduled_event": 2},
            {
                "processed_tick_count": 2,
                "trigger_candidate_count": 15,
                "full_scan_candidate_count": 20,
                "selected_candidate_count": 15,
                "skipped_candidate_count": 5,
                "fallback_candidate_count": 2,
                "candidate_plan_count": 20,
                "candidate_plan_mismatch_count": 0,
            },
        ),
    ]
    assert report["baseline_runtime"] == "default-label"
    assert report["new_buff_runtime"] == "new-buff-label"
    assert report["runtime_selection"]["mode"] == "new-buff-explicit-opt-in-indexed-buff-load-loop"
    assert report["runtime_selection"]["default_off"] is True
    assert report["apl"] == "./override.toml"
    assert report["buff_runtime_rebuild_counts"] == {
        "baseline": {"buff_load_loop": 1},
        "new_buff": {"buff_load_loop": 3, "scheduled_event": 2},
    }
    assert report["comparisons"]["buff_runtime_rebuild_counts"] == {
        "buff_load_loop": 2,
        "scheduled_event": 2,
    }
    assert report["buff_load_loop_scan_metrics"] == {
        "baseline": {
            "processed_tick_count": 2,
            "trigger_candidate_count": 10,
            "full_scan_candidate_count": 10,
            "selected_candidate_count": 10,
            "skipped_candidate_count": 0,
            "fallback_candidate_count": 0,
            "candidate_plan_count": 10,
            "candidate_plan_mismatch_count": 0,
        },
        "new_buff": {
            "processed_tick_count": 2,
            "trigger_candidate_count": 15,
            "full_scan_candidate_count": 20,
            "selected_candidate_count": 15,
            "skipped_candidate_count": 5,
            "fallback_candidate_count": 2,
            "candidate_plan_count": 20,
            "candidate_plan_mismatch_count": 0,
        },
    }
    assert report["comparisons"]["buff_load_loop_scan_metrics"] == {
        "candidate_plan_count": 10,
        "candidate_plan_mismatch_count": 0,
        "fallback_candidate_count": 2,
        "full_scan_candidate_count": 10,
        "processed_tick_count": 0,
        "selected_candidate_count": 5,
        "skipped_candidate_count": 5,
        "trigger_candidate_count": 5,
    }
    assert cleaned_sessions == ["101", "102"]


def test_single_runtime_benchmark_process_collects_opt_in_rebuild_counts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeCommonCfg:
        @classmethod
        def model_validate(cls, data: dict[str, Any]) -> Any:
            return SimpleNamespace(session_id=data["session_id"])

    class FakeSimulator:
        instances: list["FakeSimulator"] = []

        def __init__(self, *, use_indexed_buff_load_loop: bool = False) -> None:
            self.use_indexed_buff_load_loop = use_indexed_buff_load_loop
            self.rebuild_counts: dict[str, int] | None = None
            FakeSimulator.instances.append(self)

        def enable_buff_runtime_rebuild_counting(self) -> None:
            self.rebuild_counts = {}
            self._buff_load_loop_scan_metrics = {
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

        def api_run_simulator(
            self,
            common_cfg: Any,
            sim_cfg: Any,
            stop_tick: int,
            *,
            use_indexed_buff_load_loop: bool | None = None,
        ) -> Any:
            if use_indexed_buff_load_loop is not None:
                self.use_indexed_buff_load_loop = use_indexed_buff_load_loop
            if self.rebuild_counts is not None:
                self.rebuild_counts["legacy_buff_runtime_facade"] = 1
                self.rebuild_counts["buff_load_loop"] = stop_tick
            scan_metrics = getattr(self, "_buff_load_loop_scan_metrics", None)
            if scan_metrics is not None:
                scan_metrics.update(
                    {
                        "processed_tick_count": stop_tick,
                        "mission_count": stop_tick * 2,
                        "character_count": stop_tick * 3,
                        "registered_buff_count": stop_tick * 4,
                        "trigger_candidate_count": stop_tick * 5,
                        "on_field_candidate_count": stop_tick * 2,
                        "backend_candidate_count": stop_tick * 3,
                        "full_scan_candidate_count": stop_tick * 8,
                        "full_scan_on_field_candidate_count": stop_tick * 3,
                        "full_scan_backend_candidate_count": stop_tick * 5,
                        "selected_candidate_count": stop_tick * 5,
                        "selected_on_field_candidate_count": stop_tick * 2,
                        "selected_backend_candidate_count": stop_tick * 3,
                        "skipped_candidate_count": stop_tick * 3,
                        "skipped_on_field_candidate_count": stop_tick,
                        "skipped_backend_candidate_count": stop_tick * 2,
                        "fallback_candidate_count": stop_tick,
                        "fallback_on_field_candidate_count": 0,
                        "fallback_backend_candidate_count": stop_tick,
                        "pending_queue_count": stop_tick * 8,
                        "candidate_plan_count": stop_tick * 8,
                        "candidate_plan_on_field_candidate_count": stop_tick * 3,
                        "candidate_plan_backend_candidate_count": stop_tick * 5,
                        "candidate_plan_mission_count": stop_tick * 2,
                        "candidate_plan_character_count": stop_tick * 3,
                        "candidate_plan_mismatch_count": 0,
                    }
                )
            return SimpleNamespace(session_id=common_cfg.session_id)

        def get_buff_runtime_rebuild_counts(self) -> dict[str, int] | None:
            if self.rebuild_counts is None:
                return None
            return dict(self.rebuild_counts)

    perf_counter_values = iter([1.0, 1.125, 2.0, 2.25, 3.0, 3.5])
    monkeypatch.setattr(rb.os, "chdir", lambda _: None)
    monkeypatch.setattr(rb.time, "perf_counter", lambda: next(perf_counter_values))
    monkeypatch.setattr(rb, "CommonCfg", FakeCommonCfg)
    monkeypatch.setattr(rb, "Simulator", FakeSimulator)

    default_result = rb._run_single_runtime_benchmark_process(
        {"session_id": "default-session"},
        stop_tick=3,
    )
    opt_in_result = rb._run_single_runtime_benchmark_process(
        {"session_id": "counted-session"},
        stop_tick=4,
        include_rebuild_counts=True,
    )
    indexed_result = rb._run_single_runtime_benchmark_process(
        {"session_id": "indexed-session"},
        stop_tick=5,
        use_indexed_buff_load_loop=True,
    )

    assert default_result == ("default-session", 125.0, None, None)
    assert opt_in_result == (
        "counted-session",
        250.0,
        {
            "legacy_buff_runtime_facade": 1,
            "buff_load_loop": 4,
        },
        {
            "processed_tick_count": 4,
            "mission_count": 8,
            "character_count": 12,
            "registered_buff_count": 16,
            "trigger_candidate_count": 20,
            "on_field_candidate_count": 8,
            "backend_candidate_count": 12,
            "full_scan_candidate_count": 32,
            "full_scan_on_field_candidate_count": 12,
            "full_scan_backend_candidate_count": 20,
            "selected_candidate_count": 20,
            "selected_on_field_candidate_count": 8,
            "selected_backend_candidate_count": 12,
            "skipped_candidate_count": 12,
            "skipped_on_field_candidate_count": 4,
            "skipped_backend_candidate_count": 8,
            "fallback_candidate_count": 4,
            "fallback_on_field_candidate_count": 0,
            "fallback_backend_candidate_count": 4,
            "pending_queue_count": 32,
            "candidate_plan_count": 32,
            "candidate_plan_on_field_candidate_count": 12,
            "candidate_plan_backend_candidate_count": 20,
            "candidate_plan_mission_count": 8,
            "candidate_plan_character_count": 12,
            "candidate_plan_mismatch_count": 0,
        },
    )
    assert indexed_result == ("indexed-session", 500.0, None, None)
    assert FakeSimulator.instances[0].rebuild_counts is None
    assert FakeSimulator.instances[0].use_indexed_buff_load_loop is False
    assert FakeSimulator.instances[1].use_indexed_buff_load_loop is False
    assert FakeSimulator.instances[2].use_indexed_buff_load_loop is True
    assert not hasattr(FakeSimulator.instances[0], "_buff_load_loop_scan_metrics")


def test_format_human_report_only_prints_rebuild_counts_when_present():
    base_report = {
        "team": "fake-team",
        "apl": "./fake.toml",
        "stop_tick": 20,
        "baseline_runtime": "default-current",
        "new_buff_runtime": "new-buff",
        "total_runtime_ms": {"baseline": 1.0, "new_buff": 1.0},
        "hotspots": {"baseline": [], "new_buff": []},
        "comparisons": {
            "total_runtime_ms": 0.0,
            "hotspots": {},
            "faster_runtime": "tie",
            "new_buff_vs_baseline_ratio": 1.0,
        },
    }

    default_output = rb._format_human_report(base_report)

    assert "buff_runtime_rebuild_counts" not in default_output
    assert "buff_load_loop_scan_metrics" not in default_output

    opt_in_report = dict(base_report)
    opt_in_report["buff_runtime_rebuild_counts"] = {
        "baseline": {"scheduled_event": 1},
        "new_buff": {"scheduled_event": 3},
    }
    opt_in_report["buff_load_loop_scan_metrics"] = {
        "baseline": {"processed_tick_count": 1},
        "new_buff": {"processed_tick_count": 2},
    }
    opt_in_report["comparisons"] = dict(base_report["comparisons"])
    opt_in_report["comparisons"]["buff_runtime_rebuild_counts"] = {"scheduled_event": 2}
    opt_in_report["comparisons"]["buff_load_loop_scan_metrics"] = {"processed_tick_count": 1}

    opt_in_output = rb._format_human_report(opt_in_report)

    assert "buff_runtime_rebuild_counts:" in opt_in_output
    assert "buff_runtime_rebuild_count_deltas:" in opt_in_output
    assert "buff_load_loop_scan_metrics:" in opt_in_output
    assert "buff_load_loop_scan_metric_deltas:" in opt_in_output


def test_load_runtime_benchmark_snapshot_falls_back_for_blank_anomaly_column(
    monkeypatch: pytest.MonkeyPatch,
):
    raw_damage_df = pl.DataFrame(
        {
            "tick": [13],
            "skill_tag": ["alpha"],
            "element_type": [0],
            "dmg_expect": [10.0],
            "dmg_crit": [11.0],
            "stun": [1.0],
            "buildup": [0.0],
            "is_anomaly": [None],
            "is_disorder": [None],
            "UUID": ["uuid-1"],
        }
    )

    def raise_blank_anomaly(_: str):
        raise ValueError("DataFrame 中缺少有效的列: is_anomaly")

    async def fake_prepare_buff_data_and_cache(_: str):
        return {}

    monkeypatch.setattr(mlc, "prepare_dmg_data_and_cache", raise_blank_anomaly)
    monkeypatch.setattr(mlc, "_load_damage_result_df", lambda _: raw_damage_df)
    monkeypatch.setattr(rb, "prepare_buff_data_and_cache", fake_prepare_buff_data_and_cache)

    snapshot = rb._load_runtime_benchmark_snapshot("facade", "101", 12.5)

    assert snapshot.runtime_label == "facade"
    assert snapshot.hotspots["simulator_run_ms"] == 12.5
    assert snapshot.hotspots["damage_report_ms"] >= 0
    assert snapshot.hotspots["buff_report_ms"] >= 0


def test_main_repeat_summary_writes_json_artifact(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
):
    captured_kwargs: dict[str, Any] = {}

    def fake_run_repeated_runtime_benchmark(**kwargs: Any) -> dict[str, Any]:
        captured_kwargs.update(kwargs)
        reports = [
            _repeat_sample_report(
                baseline_simulator_ms=100.0 + index,
                new_buff_simulator_ms=95.0 + index,
                baseline_counts={"buff_load_loop": index + 1},
                new_buff_counts={"buff_load_loop": index + 2},
                baseline_scan_metrics={"processed_tick_count": index + 1},
                new_buff_scan_metrics={"processed_tick_count": index + 2},
            )
            for index in range(kwargs["repeat_samples"])
        ]
        if kwargs["new_buff_use_indexed_buff_load_loop"]:
            for report in reports:
                report["runtime_selection"] = {
                    "mode": "new-buff-explicit-opt-in-indexed-buff-load-loop",
                    "new_buff_use_indexed_buff_load_loop": True,
                    "default_off": True,
                    "default_indexed_execution": "blocked",
                }
        return build_repeat_runtime_benchmark_summary(
            reports=reports,
            include_rebuild_counts=kwargs["include_rebuild_counts"],
        )

    monkeypatch.setattr(
        rb,
        "run_repeated_runtime_benchmark",
        fake_run_repeated_runtime_benchmark,
    )
    output_path = tmp_path / "repeat-summary.json"

    exit_code = rb.main(
        [
            "--team",
            "fake-team",
            "--apl",
            "./fake.toml",
            "--repeat-samples",
            "3",
            "--summary-json",
            str(output_path),
            "--include-rebuild-counts",
            "--new-buff-use-indexed-buff-load-loop",
        ]
    )

    assert exit_code == 0
    assert captured_kwargs["repeat_samples"] == 3
    assert captured_kwargs["include_rebuild_counts"] is True
    assert captured_kwargs["new_buff_use_indexed_buff_load_loop"] is True
    summary = json.loads(output_path.read_text(encoding="utf-8"))
    assert summary["sample_count"] == 3
    assert summary["runtime_selection"]["mode"] == "new-buff-explicit-opt-in-indexed-buff-load-loop"
    assert summary["rebuild_count_buckets"]["included"] is True
    assert summary["scan_metric_buckets"]["included"] is True
    output = capsys.readouterr().out
    assert "sample_count: 3" in output
    assert "scan_metric_buckets:" in output


def test_script_entrypoint_runs_with_json_output(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
):
    script_path = Path("scripts/run_buff_runtime_benchmark.py").resolve()
    if not script_path.exists():
        pytest.skip("root scripts are not included in this release tree")
    captured_kwargs: dict[str, Any] = {}

    def fake_run_runtime_benchmark(**kwargs: Any) -> dict[str, Any]:
        captured_kwargs.update(kwargs)
        report: dict[str, Any] = {
            "team": "fake-team",
            "apl": "./fake.toml",
            "stop_tick": 20,
            "baseline_runtime": "default-current",
            "new_buff_runtime": "new-buff",
            "total_runtime_ms": {"baseline": 1.0, "new_buff": 1.0},
            "hotspots": {"baseline": [], "new_buff": []},
            "comparisons": {
                "total_runtime_ms": 0.0,
                "hotspots": {},
                "faster_runtime": "tie",
                "new_buff_vs_baseline_ratio": 1.0,
            },
        }
        if kwargs["include_rebuild_counts"]:
            report["buff_runtime_rebuild_counts"] = {"baseline": {}, "new_buff": {}}
            report["comparisons"]["buff_runtime_rebuild_counts"] = {}
            report["buff_load_loop_scan_metrics"] = {
                "baseline": {"processed_tick_count": 1},
                "new_buff": {"processed_tick_count": 1},
            }
            report["comparisons"]["buff_load_loop_scan_metrics"] = {"processed_tick_count": 0}
        return report

    monkeypatch.setattr(rb, "run_runtime_benchmark", fake_run_runtime_benchmark)

    namespace: dict[str, Any] = {"__name__": "__main__", "__file__": str(script_path)}
    argv_before = list(rb.sys.argv)
    try:
        rb.sys.argv = [
            str(script_path),
            "--team",
            "fake-team",
            "--json",
            "--include-rebuild-counts",
            "--new-buff-use-indexed-buff-load-loop",
        ]
        with pytest.raises(SystemExit) as excinfo:
            exec(script_path.read_text(encoding="utf-8"), namespace)
        assert excinfo.value.code == 0
        output = capsys.readouterr().out
        assert '"team": "fake-team"' in output
        assert '"faster_runtime": "tie"' in output
        assert '"buff_runtime_rebuild_counts"' in output
        assert '"buff_load_loop_scan_metrics"' in output
        assert captured_kwargs["baseline_runtime"] == "default-current"
        assert captured_kwargs["include_rebuild_counts"] is True
        assert captured_kwargs["new_buff_use_indexed_buff_load_loop"] is True
    finally:
        rb.sys.argv = argv_before


def test_script_entrypoint_importable_from_scripts_directory():
    script_path = Path("scripts/run_buff_runtime_benchmark.py").resolve()
    if not script_path.exists():
        pytest.skip("root scripts are not included in this release tree")
    content = script_path.read_text(encoding="utf-8")

    assert "sys.path.insert(0, str(PROJECT_ROOT))" in content
    assert "from zsim.utils.runtime_benchmark import main" in content
