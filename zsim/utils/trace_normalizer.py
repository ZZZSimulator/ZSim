from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Sequence

_PRELOAD_RE = re.compile(
    r"\[PRELOAD\]:In tick:\s*(?P<tick>\d+),\s*(?P<label>.+?) has been preloaded"
)
_SKILL_LOAD_RE = re.compile(r"\[Skill LOAD\]:(?P<tick>\d+):(?P<label>.+?)开始并拆分子任务")
_SKILL_END_RE = re.compile(r"\[Skill LOAD\]:(?P<tick>\d+):(?P<label>.+?)已经结束")
_BUFF_END_RE = re.compile(r"\[Buff END\]:(?P<tick>\d+):(?P<label>.+?)结束")
_DOT_END_RE = re.compile(r"\[Dot END\]:(?P<tick>\d+):(?P<label>.+?)结束")
_ANOMALY_RE = re.compile(r"\[(?:Anomaly|ANOMALY|Disorder|DISORDER)\]:(?P<tick>\d+):(?P<label>.+)")


@dataclass(frozen=True, slots=True)
class TraceEvent:
    tick: int
    domain: str
    kind: str
    label: str
    action_domain: str | None = None

    def key(self) -> tuple[int, str, str, str, str | None]:
        return self.tick, self.domain, self.kind, self.label, self.action_domain


@dataclass(frozen=True, slots=True)
class TraceDiff:
    mismatch_count: int
    baseline_only: list[TraceEvent]
    candidate_only: list[TraceEvent]

    @property
    def matches(self) -> bool:
        return self.mismatch_count == 0

    def to_dict(self, *, sample_limit: int = 20) -> dict[str, object]:
        return {
            "matches": self.matches,
            "mismatch_count": self.mismatch_count,
            "baseline_only_count": len(self.baseline_only),
            "candidate_only_count": len(self.candidate_only),
            "baseline_only_sample": [asdict(event) for event in self.baseline_only[:sample_limit]],
            "candidate_only_sample": [
                asdict(event) for event in self.candidate_only[:sample_limit]
            ],
        }


def normalize_trace_text(text: str, *, preserve_order: bool = False) -> list[TraceEvent]:
    events: list[TraceEvent] = []
    for line in text.splitlines():
        event = _normalize_line(line)
        if event is not None:
            events.append(event)
    if not preserve_order:
        events.sort(key=TraceEvent.key)
    return events


def normalize_trace_file(path: str | Path, *, preserve_order: bool = False) -> list[TraceEvent]:
    trace_path = Path(path)
    return normalize_trace_text(
        trace_path.read_text(encoding="utf-8"), preserve_order=preserve_order
    )


def diff_traces(
    baseline: Sequence[TraceEvent],
    candidate: Sequence[TraceEvent],
) -> TraceDiff:
    baseline_counts = Counter(event.key() for event in baseline)
    candidate_counts = Counter(event.key() for event in candidate)
    baseline_only = _expand_diff_counter(baseline_counts - candidate_counts)
    candidate_only = _expand_diff_counter(candidate_counts - baseline_counts)
    return TraceDiff(
        mismatch_count=len(baseline_only) + len(candidate_only),
        baseline_only=baseline_only,
        candidate_only=candidate_only,
    )


def build_trace_summary(events: Sequence[TraceEvent]) -> dict[str, object]:
    by_domain = Counter(event.domain for event in events)
    by_kind = Counter(event.kind for event in events)
    by_action_domain = Counter(
        event.action_domain for event in events if event.action_domain is not None
    )
    ticks = [event.tick for event in events]
    return {
        "event_count": len(events),
        "tick_min": min(ticks) if ticks else None,
        "tick_max": max(ticks) if ticks else None,
        "by_domain": dict(sorted(by_domain.items())),
        "by_kind": dict(sorted(by_kind.items())),
        "by_action_domain": dict(sorted(by_action_domain.items())),
    }


def write_trace_report(
    *,
    baseline_path: str | Path,
    candidate_path: str | Path | None,
    output_path: str | Path,
) -> dict[str, object]:
    baseline_events = normalize_trace_file(baseline_path)
    if candidate_path is None:
        candidate_events = list(baseline_events)
        candidate_kind = "baseline-self-check"
    else:
        candidate_events = normalize_trace_file(candidate_path)
        candidate_kind = "candidate-log"
    diff = diff_traces(baseline_events, candidate_events)
    report = {
        "schema": "zsim-core-trace-normalizer.v1",
        "baseline_path": str(Path(baseline_path)),
        "candidate_path": str(Path(candidate_path)) if candidate_path is not None else None,
        "candidate_kind": candidate_kind,
        "baseline": build_trace_summary(baseline_events),
        "candidate": build_trace_summary(candidate_events),
        "diff": diff.to_dict(),
    }
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    return report


def _normalize_line(line: str) -> TraceEvent | None:
    for regex, domain, kind in (
        (_PRELOAD_RE, "preload", "preloaded"),
        (_SKILL_LOAD_RE, "load", "skill-load"),
        (_SKILL_END_RE, "load", "skill-end"),
        (_BUFF_END_RE, "buff", "end"),
        (_DOT_END_RE, "dot", "end"),
        (_ANOMALY_RE, "anomaly", "transition"),
    ):
        match = regex.search(line)
        if match is None:
            continue
        label = _normalize_label(match.group("label"))
        return TraceEvent(
            tick=int(match.group("tick")),
            domain=domain,
            kind=kind,
            label=label,
            action_domain=_classify_action_domain(label),
        )
    return None


def _normalize_label(label: str) -> str:
    return " ".join(label.strip().split())


def _classify_action_domain(label: str) -> str | None:
    lowered = label.lower()
    if "qte" in lowered:
        return "qte"
    if "parry" in lowered or "招架" in label or "弹刀" in label:
        return "parry"
    if "dodge" in lowered or "闪避" in label:
        return "dodge"
    if "bh_aid" in lowered or "quick_assist" in lowered or "支援" in label:
        return "assist"
    if "swap" in lowered or "切换" in label:
        return "swap"
    if "damage" in lowered or "伤害" in label or "hit" in lowered:
        return "damage"
    return None


def _expand_diff_counter(
    counter: Counter[tuple[int, str, str, str, str | None]],
) -> list[TraceEvent]:
    events: list[TraceEvent] = []
    for (tick, domain, kind, label, action_domain), count in sorted(counter.items()):
        events.extend(
            TraceEvent(
                tick=tick,
                domain=domain,
                kind=kind,
                label=label,
                action_domain=action_domain,
            )
            for _ in range(count)
        )
    return events


__all__ = [
    "TraceDiff",
    "TraceEvent",
    "build_trace_summary",
    "diff_traces",
    "normalize_trace_file",
    "normalize_trace_text",
    "write_trace_report",
]
