from __future__ import annotations

import contextlib
import statistics
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Iterator


@dataclass(slots=True)
class SimulationPhaseProfiler:
    _samples: dict[str, list[float]] = field(default_factory=lambda: defaultdict(list))

    @contextlib.contextmanager
    def measure(self, phase: str) -> Iterator[None]:
        started = time.perf_counter()
        try:
            yield
        finally:
            self.record(phase, time.perf_counter() - started)

    def record(self, phase: str, seconds: float) -> None:
        if seconds < 0:
            raise ValueError("阶段耗时不能为负数")
        self._samples[phase].append(seconds)

    def phase_summary(self, phase: str) -> dict[str, float | int]:
        samples = self._samples.get(phase, [])
        if not samples:
            return {
                "count": 0,
                "total_seconds": 0.0,
                "median_seconds": 0.0,
                "max_seconds": 0.0,
            }
        return {
            "count": len(samples),
            "total_seconds": round(sum(samples), 6),
            "median_seconds": round(statistics.median(samples), 6),
            "max_seconds": round(max(samples), 6),
        }

    def summary(self) -> dict[str, object]:
        phases = {phase: self.phase_summary(phase) for phase in sorted(self._samples)}
        total_seconds = round(
            sum(float(item["total_seconds"]) for item in phases.values()),
            6,
        )
        return {
            "schema": "zsim-simulation-phase-profiler.v1",
            "total_seconds": total_seconds,
            "phases": phases,
        }


__all__ = ["SimulationPhaseProfiler"]
