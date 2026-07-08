from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from collections.abc import Sequence
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from statistics import median
from typing import Any

from zsim.define import config
from zsim.models.session.session_run import CommonCfg
from zsim.simulator import Simulator
from zsim.utils.main_loop_consistency import (
    PROJECT_ROOT,
    RUNTIME_LABEL_CONTRACT,
    _build_session_id,
    _cleanup_result_artifacts,
    _prepare_common_cfg,
    _prepare_damage_data_for_consistency,
    _resolve_baseline_runtime_label,
    _runtime_selection_contract,
)
from zsim.utils.process_buff_result import prepare_buff_data_and_cache

REPEAT_BENCHMARK_SUMMARY_SCHEMA = "zsim-buff-runtime-repeat-benchmark.v1"
FUTURE_THRESHOLD_MIN_REPEAT_SAMPLES = 5
BENCHMARK_THRESHOLD_MIN_REPEAT_SAMPLES = 10
BENCHMARK_ELIGIBLE_MEDIAN_RELATIVE_DELTA = -0.05
BENCHMARK_NOISE_RELATIVE_DELTA = 0.05
NO_DEFAULT_ENABLEMENT_STATEMENT = (
    "No default enablement or speedup target is authorized by this PRD."
)


@dataclass(frozen=True)
class RuntimeBenchmarkSnapshot:
    runtime_label: str
    session_id: str
    total_runtime_ms: float
    hotspots: dict[str, float]
    rebuild_counts: dict[str, int] | None = None
    buff_load_loop_scan_metrics: dict[str, int] | None = None


def _run_single_runtime_benchmark_process(
    common_cfg_data: dict[str, Any],
    stop_tick: int,
    include_rebuild_counts: bool = False,
    use_indexed_buff_load_loop: bool = False,
) -> tuple[str, float, dict[str, int] | None, dict[str, int] | None]:
    os.chdir(PROJECT_ROOT)
    common_cfg = CommonCfg.model_validate(common_cfg_data)
    simulator = Simulator(use_indexed_buff_load_loop=use_indexed_buff_load_loop)
    if include_rebuild_counts:
        simulator.enable_buff_runtime_rebuild_counting()
    started_at = time.perf_counter()
    confirmation = simulator.api_run_simulator(
        common_cfg,
        sim_cfg=None,
        stop_tick=stop_tick,
        use_indexed_buff_load_loop=use_indexed_buff_load_loop,
    )
    simulator_runtime_ms = round((time.perf_counter() - started_at) * 1000, 4)
    rebuild_counts = simulator.get_buff_runtime_rebuild_counts() if include_rebuild_counts else None
    scan_metrics = (
        dict(getattr(simulator, "_buff_load_loop_scan_metrics", {}))
        if include_rebuild_counts
        else None
    )
    return confirmation.session_id, simulator_runtime_ms, rebuild_counts, scan_metrics


def _load_runtime_benchmark_snapshot(
    runtime_label: str,
    session_id: str,
    simulator_runtime_ms: float,
    rebuild_counts: dict[str, int] | None = None,
    buff_load_loop_scan_metrics: dict[str, int] | None = None,
) -> RuntimeBenchmarkSnapshot:
    damage_started_at = time.perf_counter()
    _prepare_damage_data_for_consistency(session_id)
    damage_report_ms = round((time.perf_counter() - damage_started_at) * 1000, 4)

    buff_started_at = time.perf_counter()
    asyncio.run(prepare_buff_data_and_cache(session_id))
    buff_report_ms = round((time.perf_counter() - buff_started_at) * 1000, 4)

    hotspots = {
        "simulator_run_ms": simulator_runtime_ms,
        "damage_report_ms": damage_report_ms,
        "buff_report_ms": buff_report_ms,
    }

    return RuntimeBenchmarkSnapshot(
        runtime_label=runtime_label,
        session_id=session_id,
        total_runtime_ms=round(sum(hotspots.values()), 4),
        hotspots=hotspots,
        rebuild_counts=rebuild_counts,
        buff_load_loop_scan_metrics=buff_load_loop_scan_metrics,
    )


def _sorted_hotspots(hotspots: dict[str, float]) -> list[dict[str, float | str]]:
    hotspot_names = sorted(hotspots, key=lambda name: (-hotspots[name], name))
    return [
        {
            "name": hotspot_name,
            "runtime_ms": hotspots[hotspot_name],
        }
        for hotspot_name in hotspot_names
    ]


def _hotspot_comparisons(
    baseline_hotspots: dict[str, float],
    new_buff_hotspots: dict[str, float],
) -> dict[str, float]:
    hotspot_names = sorted(set(baseline_hotspots) | set(new_buff_hotspots))
    return {
        hotspot_name: round(
            new_buff_hotspots.get(hotspot_name, 0.0) - baseline_hotspots.get(hotspot_name, 0.0),
            4,
        )
        for hotspot_name in hotspot_names
    }


def _rebuild_count_buckets(
    buff_runtime_rebuild_counts: dict[str, dict[str, int]] | None,
) -> dict[str, dict[str, int]]:
    source = buff_runtime_rebuild_counts or {}
    return {
        "baseline": dict(source.get("baseline", {})),
        "new_buff": dict(source.get("new_buff", {})),
    }


def _rebuild_count_comparisons(
    baseline_counts: dict[str, int],
    new_buff_counts: dict[str, int],
) -> dict[str, int]:
    counter_names = sorted(set(baseline_counts) | set(new_buff_counts))
    return {
        counter_name: int(new_buff_counts.get(counter_name, 0))
        - int(baseline_counts.get(counter_name, 0))
        for counter_name in counter_names
    }


def _scan_metric_buckets(
    buff_load_loop_scan_metrics: dict[str, dict[str, int]] | None,
) -> dict[str, dict[str, int]]:
    source = buff_load_loop_scan_metrics or {}
    return {
        "baseline": dict(source.get("baseline", {})),
        "new_buff": dict(source.get("new_buff", {})),
    }


def _scan_metric_comparisons(
    baseline_metrics: dict[str, int],
    new_buff_metrics: dict[str, int],
) -> dict[str, int]:
    metric_names = sorted(set(baseline_metrics) | set(new_buff_metrics))
    return {
        metric_name: int(new_buff_metrics.get(metric_name, 0))
        - int(baseline_metrics.get(metric_name, 0))
        for metric_name in metric_names
    }


def _numeric_summary(values: Sequence[float | int]) -> dict[str, float]:
    if not values:
        return {"median": 0.0, "min": 0.0, "max": 0.0, "range": 0.0}
    minimum = float(min(values))
    maximum = float(max(values))
    return {
        "median": round(float(median(values)), 4),
        "min": round(minimum, 4),
        "max": round(maximum, 4),
        "range": round(maximum - minimum, 4),
    }


def _summary_with_samples(values: list[float]) -> dict[str, Any]:
    return {
        **_numeric_summary(values),
        "samples": [round(float(value), 4) for value in values],
    }


def _simulator_runtime_ms(report: dict[str, Any], bucket: str) -> float:
    for hotspot in report.get("hotspots", {}).get(bucket, []):
        if hotspot.get("name") == "simulator_run_ms":
            return float(hotspot["runtime_ms"])
    raise KeyError(f"{bucket} 缺少 simulator_run_ms 热点数据")


def _report_rebuild_count_buckets(report: dict[str, Any]) -> dict[str, dict[str, int]]:
    buckets = report.get("buff_runtime_rebuild_counts") or {}
    return {
        "baseline": dict(buckets.get("baseline", {})),
        "new_buff": dict(buckets.get("new_buff", {})),
    }


def _report_scan_metric_buckets(report: dict[str, Any]) -> dict[str, dict[str, int]]:
    buckets = report.get("buff_load_loop_scan_metrics") or {}
    return {
        "baseline": dict(buckets.get("baseline", {})),
        "new_buff": dict(buckets.get("new_buff", {})),
    }


def _aggregate_rebuild_count_bucket(
    samples: list[dict[str, dict[str, int]]],
    bucket: str,
) -> dict[str, dict[str, Any]]:
    counter_names = sorted(
        {counter_name for sample in samples for counter_name in sample.get(bucket, {})}
    )
    return {
        counter_name: {
            **_numeric_summary(
                [int(sample.get(bucket, {}).get(counter_name, 0)) for sample in samples]
            ),
            "samples": [int(sample.get(bucket, {}).get(counter_name, 0)) for sample in samples],
        }
        for counter_name in counter_names
    }


def _aggregate_scan_metric_bucket(
    samples: list[dict[str, dict[str, int]]],
    bucket: str,
) -> dict[str, dict[str, Any]]:
    metric_names = sorted(
        {metric_name for sample in samples for metric_name in sample.get(bucket, {})}
    )
    return {
        metric_name: {
            **_numeric_summary(
                [int(sample.get(bucket, {}).get(metric_name, 0)) for sample in samples]
            ),
            "samples": [int(sample.get(bucket, {}).get(metric_name, 0)) for sample in samples],
        }
        for metric_name in metric_names
    }


def _aggregate_scan_metric_value(
    samples: list[dict[str, dict[str, int]]],
    bucket: str,
    metric_name: str,
) -> dict[str, Any]:
    values = [int(sample.get(bucket, {}).get(metric_name, 0)) for sample in samples]
    return {
        **_numeric_summary(values),
        "samples": values,
    }


def _aggregate_scan_metric_prefix(
    samples: list[dict[str, dict[str, int]]],
    bucket: str,
    prefix: str,
) -> dict[str, dict[str, Any]]:
    metric_names = sorted(
        {
            metric_name
            for sample in samples
            for metric_name in sample.get(bucket, {})
            if metric_name.startswith(prefix)
        }
    )
    return {
        metric_name: _aggregate_scan_metric_value(samples, bucket, metric_name)
        for metric_name in metric_names
    }


def _build_runtime_relative_delta(
    baseline_summary: dict[str, Any],
    new_buff_summary: dict[str, Any],
) -> dict[str, Any]:
    baseline_median = float(baseline_summary["median"])
    new_buff_median = float(new_buff_summary["median"])
    if baseline_median == 0:
        ratio = None
        relative_delta = None
        percent = None
    else:
        relative_delta = round((new_buff_median - baseline_median) / baseline_median, 6)
        ratio = round(new_buff_median / baseline_median, 6)
        percent = round(relative_delta * 100, 4)
    return {
        "basis": "simulator_runtime_ms.median",
        "new_buff_minus_baseline_median_ms": round(new_buff_median - baseline_median, 4),
        "new_buff_vs_baseline_median_ratio": ratio,
        "new_buff_vs_baseline_median_relative_delta": relative_delta,
        "new_buff_vs_baseline_median_percent": percent,
    }


def _build_threshold_policy() -> dict[str, Any]:
    return {
        "minimum_repeat_samples": BENCHMARK_THRESHOLD_MIN_REPEAT_SAMPLES,
        "eligible_median_relative_delta_at_or_below": BENCHMARK_ELIGIBLE_MEDIAN_RELATIVE_DELTA,
        "noise_band_relative_delta": [
            BENCHMARK_ELIGIBLE_MEDIAN_RELATIVE_DELTA,
            BENCHMARK_NOISE_RELATIVE_DELTA,
        ],
        "blocked_if_candidate_plan_mismatch_count_above": 0,
        "blocked_if_required_metrics_missing": True,
        "default_enablement_authorized": False,
        "rule": (
            "需要 10 组样本、重建指标、扫描指标、候选计划指标，并且候选计划不匹配数为 0，"
            "benchmark 证据才可用于后续启用 PRD。相对中位数差异必须小于等于 -5%，"
            "否则需要补充更多样本。"
            + NO_DEFAULT_ENABLEMENT_STATEMENT
        ),
    }


def _build_threshold_verdict(
    *,
    sample_count: int,
    include_rebuild_counts: bool,
    relative_delta: dict[str, Any],
    candidate_plan_metrics: dict[str, Any],
    mismatch_counts: dict[str, Any],
) -> dict[str, Any]:
    reasons: list[str] = []
    candidate_plan_mismatch_count = mismatch_counts["candidate_plan_mismatch_count"]
    mismatch_max = max(
        float(candidate_plan_mismatch_count["baseline"]["max"]),
        float(candidate_plan_mismatch_count["new_buff"]["max"]),
    )
    if mismatch_max > 0:
        return {
            "status": "blocked",
            "reasons": [f"candidate_plan_mismatch_count max {mismatch_max:g} is above zero"],
        }

    if not include_rebuild_counts:
        return {
            "status": "blocked",
            "reasons": ["rebuild, scan, and candidate-plan metrics were not included"],
        }

    aggregate = candidate_plan_metrics.get("aggregate", {})
    if not aggregate.get("baseline") or not aggregate.get("new_buff"):
        return {
            "status": "blocked",
            "reasons": ["candidate-plan metrics are missing from one or both runtime buckets"],
        }

    if sample_count < BENCHMARK_THRESHOLD_MIN_REPEAT_SAMPLES:
        return {
            "status": "needs_more_samples",
            "reasons": [
                f"sample_count {sample_count} is below {BENCHMARK_THRESHOLD_MIN_REPEAT_SAMPLES}"
            ],
        }

    median_relative_delta = relative_delta.get(
        "new_buff_vs_baseline_median_relative_delta",
    )
    if median_relative_delta is None:
        return {
            "status": "blocked",
            "reasons": ["baseline median simulator runtime is zero"],
        }

    if median_relative_delta <= BENCHMARK_ELIGIBLE_MEDIAN_RELATIVE_DELTA:
        reasons.append("relative median delta is at or below the conservative -5% eligibility line")
        return {"status": "eligible_for_enablement_prd", "reasons": reasons}

    if median_relative_delta > BENCHMARK_NOISE_RELATIVE_DELTA:
        reasons.append(
            "relative median delta is slower than the +5% noise boundary and needs more samples"
        )
    else:
        reasons.append(
            "relative median delta is inside the conservative noise band and needs more samples"
        )
    return {"status": "needs_more_samples", "reasons": reasons}


def build_repeat_runtime_benchmark_summary(
    *,
    reports: list[dict[str, Any]],
    include_rebuild_counts: bool = False,
) -> dict[str, Any]:
    if not reports:
        raise ValueError("重复 benchmark 摘要至少需要一份报告")

    first_report = reports[0]
    baseline_simulator_runtime_ms = [
        _simulator_runtime_ms(report, "baseline") for report in reports
    ]
    new_buff_simulator_runtime_ms = [
        _simulator_runtime_ms(report, "new_buff") for report in reports
    ]
    rebuild_count_samples = (
        [_report_rebuild_count_buckets(report) for report in reports]
        if include_rebuild_counts
        else []
    )
    scan_metric_samples = (
        [_report_scan_metric_buckets(report) for report in reports]
        if include_rebuild_counts
        else []
    )
    runtime_selection = dict(first_report.get("runtime_selection", RUNTIME_LABEL_CONTRACT))
    simulator_runtime_summary = {
        "baseline": _summary_with_samples(baseline_simulator_runtime_ms),
        "new_buff": _summary_with_samples(new_buff_simulator_runtime_ms),
    }
    relative_delta = _build_runtime_relative_delta(
        simulator_runtime_summary["baseline"],
        simulator_runtime_summary["new_buff"],
    )
    candidate_plan_metrics = {
        "included": include_rebuild_counts,
        "aggregate": {
            "baseline": (
                _aggregate_scan_metric_prefix(scan_metric_samples, "baseline", "candidate_plan")
                if include_rebuild_counts
                else {}
            ),
            "new_buff": (
                _aggregate_scan_metric_prefix(scan_metric_samples, "new_buff", "candidate_plan")
                if include_rebuild_counts
                else {}
            ),
        },
    }
    mismatch_counts = {
        "candidate_plan_mismatch_count": {
            "included": include_rebuild_counts,
            "baseline": (
                _aggregate_scan_metric_value(
                    scan_metric_samples,
                    "baseline",
                    "candidate_plan_mismatch_count",
                )
                if include_rebuild_counts
                else _summary_with_samples([])
            ),
            "new_buff": (
                _aggregate_scan_metric_value(
                    scan_metric_samples,
                    "new_buff",
                    "candidate_plan_mismatch_count",
                )
                if include_rebuild_counts
                else _summary_with_samples([])
            ),
        },
    }

    samples = []
    for index, report in enumerate(reports, start=1):
        sample = {
            "sample_index": index,
            "total_runtime_ms": dict(report["total_runtime_ms"]),
            "simulator_runtime_ms": {
                "baseline": baseline_simulator_runtime_ms[index - 1],
                "new_buff": new_buff_simulator_runtime_ms[index - 1],
            },
            "rebuild_count_buckets": (
                rebuild_count_samples[index - 1] if include_rebuild_counts else None
            ),
        }
        if include_rebuild_counts:
            sample["scan_metric_buckets"] = scan_metric_samples[index - 1]
        samples.append(sample)

    summary = {
        "schema": REPEAT_BENCHMARK_SUMMARY_SCHEMA,
        "team": first_report["team"],
        "apl": first_report["apl"],
        "stop_tick": int(first_report["stop_tick"]),
        "sample_count": len(reports),
        "repeat_samples": len(reports),
        "runtime_labels": {
            "baseline": first_report["baseline_runtime"],
            "new_buff": first_report["new_buff_runtime"],
        },
        "runtime_selection": runtime_selection,
        "opt_in_flag_status": {
            "new_buff_use_indexed_buff_load_loop": bool(
                runtime_selection.get("new_buff_use_indexed_buff_load_loop", False)
            ),
            "default_off": bool(runtime_selection.get("default_off", True)),
            "default_indexed_execution": runtime_selection.get(
                "default_indexed_execution",
                "blocked",
            ),
        },
        "simulator_runtime_ms": simulator_runtime_summary,
        "relative_delta": relative_delta,
        "rebuild_count_buckets": {
            "included": include_rebuild_counts,
            "samples": rebuild_count_samples,
            "aggregate": {
                "baseline": _aggregate_rebuild_count_bucket(rebuild_count_samples, "baseline"),
                "new_buff": _aggregate_rebuild_count_bucket(rebuild_count_samples, "new_buff"),
            },
        },
        "future_threshold_use": {
            "speedup_target_defined": False,
            "minimum_repeat_samples": FUTURE_THRESHOLD_MIN_REPEAT_SAMPLES,
            "noise_reporting": (
                "Report sample_count plus median/min/max/range simulator runtime "
                "for each runtime label before any later threshold is evaluated."
            ),
            "rule": (
                "A later PRD may define numeric thresholds only after at least "
                f"{FUTURE_THRESHOLD_MIN_REPEAT_SAMPLES} repeats and explicit noise "
                "reporting; this baseline does not claim a speedup target. "
                + NO_DEFAULT_ENABLEMENT_STATEMENT
            ),
        },
        "threshold_policy": _build_threshold_policy(),
        "enablement_policy": {
            "default_enablement_authorized": False,
            "speedup_target_authorized": False,
            "statement": NO_DEFAULT_ENABLEMENT_STATEMENT,
        },
        "candidate_plan_metrics": candidate_plan_metrics,
        "mismatch_counts": mismatch_counts,
        "threshold_verdict": _build_threshold_verdict(
            sample_count=len(reports),
            include_rebuild_counts=include_rebuild_counts,
            relative_delta=relative_delta,
            candidate_plan_metrics=candidate_plan_metrics,
            mismatch_counts=mismatch_counts,
        ),
        "samples": samples,
    }
    if include_rebuild_counts:
        summary["scan_metric_buckets"] = {
            "included": True,
            "samples": scan_metric_samples,
            "aggregate": {
                "baseline": _aggregate_scan_metric_bucket(scan_metric_samples, "baseline"),
                "new_buff": _aggregate_scan_metric_bucket(scan_metric_samples, "new_buff"),
            },
        }
    return summary


def build_runtime_benchmark_report(
    *,
    team: str,
    apl: str,
    stop_tick: int,
    baseline_snapshot: RuntimeBenchmarkSnapshot,
    new_buff_snapshot: RuntimeBenchmarkSnapshot,
    include_rebuild_counts: bool = False,
    new_buff_use_indexed_buff_load_loop: bool = False,
    buff_runtime_rebuild_counts: dict[str, dict[str, int]] | None = None,
    buff_load_loop_scan_metrics: dict[str, dict[str, int]] | None = None,
) -> dict[str, Any]:
    total_runtime_delta = round(
        new_buff_snapshot.total_runtime_ms - baseline_snapshot.total_runtime_ms,
        4,
    )
    faster_runtime = "tie"
    if baseline_snapshot.total_runtime_ms < new_buff_snapshot.total_runtime_ms:
        faster_runtime = baseline_snapshot.runtime_label
    elif new_buff_snapshot.total_runtime_ms < baseline_snapshot.total_runtime_ms:
        faster_runtime = new_buff_snapshot.runtime_label

    speedup_ratio = 1.0
    if baseline_snapshot.total_runtime_ms != 0:
        speedup_ratio = round(
            new_buff_snapshot.total_runtime_ms / baseline_snapshot.total_runtime_ms,
            4,
        )

    comparisons: dict[str, Any] = {
        "total_runtime_ms": total_runtime_delta,
        "hotspots": _hotspot_comparisons(
            baseline_snapshot.hotspots,
            new_buff_snapshot.hotspots,
        ),
        "faster_runtime": faster_runtime,
        "new_buff_vs_baseline_ratio": speedup_ratio,
    }
    baseline_label = baseline_snapshot.runtime_label
    report: dict[str, Any] = {
        "team": team,
        "apl": apl,
        "stop_tick": stop_tick,
        "baseline_runtime": baseline_label,
        "new_buff_runtime": new_buff_snapshot.runtime_label,
        "runtime_selection": _runtime_selection_contract(
            new_buff_use_indexed_buff_load_loop=new_buff_use_indexed_buff_load_loop,
        ),
        "total_runtime_ms": {
            "baseline": baseline_snapshot.total_runtime_ms,
            "new_buff": new_buff_snapshot.total_runtime_ms,
        },
        "hotspots": {
            "baseline": _sorted_hotspots(baseline_snapshot.hotspots),
            "new_buff": _sorted_hotspots(new_buff_snapshot.hotspots),
        },
        "comparisons": comparisons,
    }
    if include_rebuild_counts:
        count_source = buff_runtime_rebuild_counts
        if count_source is None:
            count_source = {
                "baseline": baseline_snapshot.rebuild_counts or {},
                "new_buff": new_buff_snapshot.rebuild_counts or {},
            }
        rebuild_counts = _rebuild_count_buckets(count_source)
        report["buff_runtime_rebuild_counts"] = rebuild_counts
        comparisons["buff_runtime_rebuild_counts"] = _rebuild_count_comparisons(
            rebuild_counts["baseline"],
            rebuild_counts["new_buff"],
        )
        scan_source = buff_load_loop_scan_metrics
        if scan_source is None:
            scan_source = {
                "baseline": baseline_snapshot.buff_load_loop_scan_metrics or {},
                "new_buff": new_buff_snapshot.buff_load_loop_scan_metrics or {},
            }
        scan_metrics = _scan_metric_buckets(scan_source)
        report["buff_load_loop_scan_metrics"] = scan_metrics
        comparisons["buff_load_loop_scan_metrics"] = _scan_metric_comparisons(
            scan_metrics["baseline"],
            scan_metrics["new_buff"],
        )
    return report


def run_runtime_benchmark(
    *,
    team: str,
    apl: str | None,
    stop_tick: int,
    baseline_runtime: str | None = None,
    new_buff_runtime: str = "new-buff-current",
    cleanup: bool = True,
    include_rebuild_counts: bool = False,
    new_buff_use_indexed_buff_load_loop: bool = False,
) -> dict[str, Any]:
    os.chdir(PROJECT_ROOT)
    base_cfg = _prepare_common_cfg(team, apl)
    apl_path = base_cfg.apl_path
    snapshots: list[RuntimeBenchmarkSnapshot] = []
    baseline_label = _resolve_baseline_runtime_label(
        baseline_runtime=baseline_runtime,
        default="default-current",
    )

    runtime_flags = (False, new_buff_use_indexed_buff_load_loop)
    for runtime_label, use_indexed_buff_load_loop in zip(
        (baseline_label, new_buff_runtime),
        runtime_flags,
        strict=True,
    ):
        session_id = _build_session_id()
        runtime_cfg = base_cfg.model_copy(update={"session_id": session_id}, deep=True)
        runtime_cfg_data = runtime_cfg.model_dump(mode="json")

        with ProcessPoolExecutor(max_workers=1) as executor:
            future = executor.submit(
                _run_single_runtime_benchmark_process,
                runtime_cfg_data,
                stop_tick,
                include_rebuild_counts,
                use_indexed_buff_load_loop,
            )
            (
                finished_session_id,
                simulator_runtime_ms,
                rebuild_counts,
                scan_metrics,
            ) = future.result()

        try:
            snapshots.append(
                _load_runtime_benchmark_snapshot(
                    runtime_label,
                    finished_session_id,
                    simulator_runtime_ms,
                    rebuild_counts,
                    scan_metrics,
                )
            )
        finally:
            if cleanup:
                _cleanup_result_artifacts(finished_session_id)

    return build_runtime_benchmark_report(
        team=team,
        apl=apl_path,
        stop_tick=stop_tick,
        baseline_snapshot=snapshots[0],
        new_buff_snapshot=snapshots[1],
        include_rebuild_counts=include_rebuild_counts,
        new_buff_use_indexed_buff_load_loop=new_buff_use_indexed_buff_load_loop,
    )


def run_repeated_runtime_benchmark(
    *,
    team: str,
    apl: str | None,
    stop_tick: int,
    repeat_samples: int,
    baseline_runtime: str | None = None,
    new_buff_runtime: str = "new-buff-current",
    cleanup: bool = True,
    include_rebuild_counts: bool = False,
    new_buff_use_indexed_buff_load_loop: bool = False,
) -> dict[str, Any]:
    if repeat_samples < 1:
        raise ValueError("repeat_samples 必须至少为 1")
    reports = [
        run_runtime_benchmark(
            team=team,
            apl=apl,
            stop_tick=stop_tick,
            baseline_runtime=baseline_runtime,
            new_buff_runtime=new_buff_runtime,
            cleanup=cleanup,
            include_rebuild_counts=include_rebuild_counts,
            new_buff_use_indexed_buff_load_loop=new_buff_use_indexed_buff_load_loop,
        )
        for _ in range(repeat_samples)
    ]
    return build_repeat_runtime_benchmark_summary(
        reports=reports,
        include_rebuild_counts=include_rebuild_counts,
    )


def write_repeat_runtime_benchmark_summary(
    path: str | Path,
    summary: dict[str, Any],
) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(summary, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _positive_int(value: str) -> int:
    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError("数值必须至少为 1")
    return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="运行 Buff 运行时 benchmark 对比")
    parser.add_argument("--team", required=True, help="要模拟的已注册队伍名称")
    parser.add_argument(
        "--apl",
        default=None,
        help="可选：覆盖 APL 路径。默认使用所选队伍配置。",
    )
    parser.add_argument(
        "--stop-tick",
        type=int,
        default=config.stop_tick,
        help="每次 benchmark 运行的停止 tick。",
    )
    parser.add_argument(
        "--baseline-runtime",
        dest="baseline_runtime",
        default="default-current",
        help="报告中记录的第一组/默认当前运行标签；该参数不选择实际运行时。",
    )
    parser.add_argument(
        "--new-buff-runtime",
        default="new-buff-current",
        help="报告中记录的第二组运行标签；该参数不选择实际运行时。",
    )
    parser.add_argument(
        "--keep-artifacts",
        action="store_true",
        help="报告生成后保留原始 results/<session_id> 产物。",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="将完整 JSON 报告打印到标准输出。",
    )
    parser.add_argument(
        "--repeat-samples",
        "--repeat",
        dest="repeat_samples",
        type=_positive_int,
        default=1,
        help="汇总前运行指定次数的仅标签 benchmark 样本。",
    )
    parser.add_argument(
        "--summary-json",
        default=None,
        help="将重复 benchmark 的 JSON 摘要产物写入该路径。",
    )
    parser.add_argument(
        "--include-rebuild-counts",
        action="store_true",
        help="在报告中包含 Buff runtime 重建次数与 BuffLoadLoop 扫描指标分桶。",
    )
    parser.add_argument(
        "--new-buff-use-indexed-buff-load-loop",
        action="store_true",
        help=(
            "仅为 new Buff 运行显式启用带索引的 BuffLoadLoop；"
            "省略时两组运行都使用默认当前路径。"
        ),
    )
    return parser


def _format_human_report(report: dict[str, Any]) -> str:
    lines = [
        f"team: {report['team']}",
        f"apl: {report['apl']}",
        f"stop_tick: {report['stop_tick']}",
        "runtime_selection: "
        + report.get("runtime_selection", {}).get("mode", "label-only-current-runtime"),
        (
            "total_runtime_ms: "
            f"{report['baseline_runtime']}={report['total_runtime_ms']['baseline']}, "
            f"{report['new_buff_runtime']}={report['total_runtime_ms']['new_buff']}"
        ),
        f"faster_runtime: {report['comparisons']['faster_runtime']}",
        "hotspot_deltas: "
        + json.dumps(report["comparisons"]["hotspots"], ensure_ascii=False, sort_keys=True),
    ]
    if "buff_runtime_rebuild_counts" in report:
        lines.append(
            "buff_runtime_rebuild_counts: "
            + json.dumps(report["buff_runtime_rebuild_counts"], ensure_ascii=False, sort_keys=True)
        )
        if "buff_runtime_rebuild_counts" in report["comparisons"]:
            lines.append(
                "buff_runtime_rebuild_count_deltas: "
                + json.dumps(
                    report["comparisons"]["buff_runtime_rebuild_counts"],
                    ensure_ascii=False,
                    sort_keys=True,
                )
            )
    if "buff_load_loop_scan_metrics" in report:
        lines.append(
            "buff_load_loop_scan_metrics: "
            + json.dumps(report["buff_load_loop_scan_metrics"], ensure_ascii=False, sort_keys=True)
        )
        if "buff_load_loop_scan_metrics" in report["comparisons"]:
            lines.append(
                "buff_load_loop_scan_metric_deltas: "
                + json.dumps(
                    report["comparisons"]["buff_load_loop_scan_metrics"],
                    ensure_ascii=False,
                    sort_keys=True,
                )
            )
    return "\n".join(lines)


def _format_repeat_summary(summary: dict[str, Any]) -> str:
    labels = summary["runtime_labels"]
    runtimes = summary["simulator_runtime_ms"]
    policy = summary["future_threshold_use"]
    threshold_verdict = summary.get("threshold_verdict", {})
    lines = [
        f"team: {summary['team']}",
        f"apl: {summary['apl']}",
        f"stop_tick: {summary['stop_tick']}",
        f"sample_count: {summary['sample_count']}",
        "runtime_selection: "
        + summary.get("runtime_selection", {}).get("mode", "label-only-current-runtime"),
        (
            "simulator_runtime_ms: "
            f"{labels['baseline']} median={runtimes['baseline']['median']} "
            f"min={runtimes['baseline']['min']} max={runtimes['baseline']['max']}; "
            f"{labels['new_buff']} median={runtimes['new_buff']['median']} "
            f"min={runtimes['new_buff']['min']} max={runtimes['new_buff']['max']}"
        ),
    ]
    rebuild_counts = summary.get("rebuild_count_buckets", {})
    if rebuild_counts.get("included"):
        lines.append(
            "rebuild_count_buckets: "
            + json.dumps(rebuild_counts["aggregate"], ensure_ascii=False, sort_keys=True)
        )
    scan_metrics = summary.get("scan_metric_buckets", {})
    if scan_metrics.get("included"):
        lines.append(
            "scan_metric_buckets: "
            + json.dumps(scan_metrics["aggregate"], ensure_ascii=False, sort_keys=True)
        )
    lines.append(
        "future_threshold_use: "
        f"speedup_target_defined={policy['speedup_target_defined']}; "
        f"minimum_repeat_samples={policy['minimum_repeat_samples']}; " + policy["noise_reporting"]
    )
    lines.append("threshold_verdict: " + threshold_verdict.get("status", "needs_more_samples"))
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    repeat_mode = args.repeat_samples > 1 or args.summary_json is not None
    if repeat_mode:
        summary = run_repeated_runtime_benchmark(
            team=args.team,
            apl=args.apl,
            stop_tick=args.stop_tick,
            baseline_runtime=args.baseline_runtime,
            new_buff_runtime=args.new_buff_runtime,
            repeat_samples=args.repeat_samples,
            cleanup=not args.keep_artifacts,
            include_rebuild_counts=args.include_rebuild_counts,
            new_buff_use_indexed_buff_load_loop=args.new_buff_use_indexed_buff_load_loop,
        )
        if args.summary_json:
            write_repeat_runtime_benchmark_summary(args.summary_json, summary)
        if args.json:
            print(json.dumps(summary, ensure_ascii=False, sort_keys=True, indent=2))
        else:
            print(_format_repeat_summary(summary))
        return 0

    report = run_runtime_benchmark(
        team=args.team,
        apl=args.apl,
        stop_tick=args.stop_tick,
        baseline_runtime=args.baseline_runtime,
        new_buff_runtime=args.new_buff_runtime,
        cleanup=not args.keep_artifacts,
        include_rebuild_counts=args.include_rebuild_counts,
        new_buff_use_indexed_buff_load_loop=args.new_buff_use_indexed_buff_load_loop,
    )
    if args.json:
        print(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2))
    else:
        print(_format_human_report(report))
    return 0


__all__ = [
    "PROJECT_ROOT",
    "RuntimeBenchmarkSnapshot",
    "build_parser",
    "build_repeat_runtime_benchmark_summary",
    "build_runtime_benchmark_report",
    "main",
    "run_repeated_runtime_benchmark",
    "run_runtime_benchmark",
    "write_repeat_runtime_benchmark_summary",
]


if __name__ == "__main__":
    sys.exit(main())
