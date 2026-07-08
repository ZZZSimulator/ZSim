from __future__ import annotations

import pytest

from zsim.utils.simulation_phase_profiler import SimulationPhaseProfiler


def test_phase_profiler_records_samples_and_summarizes_median() -> None:
    profiler = SimulationPhaseProfiler()

    profiler.record("preload", 0.3)
    profiler.record("preload", 0.1)
    profiler.record("schedule", 0.2)

    summary = profiler.summary()

    assert summary["total_seconds"] == 0.6
    assert summary["phases"]["preload"] == {
        "count": 2,
        "total_seconds": 0.4,
        "median_seconds": 0.2,
        "max_seconds": 0.3,
    }
    assert summary["phases"]["schedule"]["count"] == 1


def test_phase_profiler_rejects_negative_duration() -> None:
    profiler = SimulationPhaseProfiler()

    with pytest.raises(ValueError, match="不能为负数"):
        profiler.record("bad", -0.1)
