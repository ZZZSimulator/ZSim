from __future__ import annotations

import inspect
from types import SimpleNamespace
from typing import NoReturn

import pytest

from zsim.sim_progress.Dot.Dots.Shock import Shock
from zsim.sim_progress.Dot.initialization import (
    RINA_SHOCK_DURATION_EXTENSION_BUFF_INDEX,
    DotInitializationReadContext,
)


class _ForbiddenLayer:
    def __init__(self, label: str) -> None:
        self._label = label

    def _fail(self, action: str) -> NoReturn:
        raise AssertionError(
            f"Shock duration initialization should not touch {self._label}: {action}"
        )

    def __getattr__(self, name: str) -> object:
        self._fail(f"attribute {name}")

    def __call__(self, *args: object, **kwargs: object) -> object:
        self._fail("call")

    def __bool__(self) -> bool:
        self._fail("truthiness")

    def append(self, item: object) -> None:
        self._fail("append")


def _build_sim_instance(name_box, exist_buff_dict):
    return SimpleNamespace(
        init_data=SimpleNamespace(name_box=name_box),
        load_data=SimpleNamespace(exist_buff_dict=exist_buff_dict),
        schedule_data=_ForbiddenLayer("ScheduleDispatchPort / schedule_data"),
        listener_manager=SimpleNamespace(
            broadcast_event=_ForbiddenLayer("listener broadcast"),
        ),
        runtime_command_port=_ForbiddenLayer("RuntimeCommandPort"),
        dynamic_dot_list=_ForbiddenLayer("dynamic_dot_list"),
        calculator=_ForbiddenLayer("Calculator"),
        cal_anomaly=_ForbiddenLayer("CalAnomaly"),
    )


def test_shock_dot_feature_requires_sim_instance():
    with pytest.raises(ValueError, match="sim_instance is None"):
        Shock.DotFeature(sim_instance=None)


def test_shock_dot_duration_defaults_to_600_without_rina():
    sim_instance = _build_sim_instance(
        name_box=["安比", "妮可"],
        exist_buff_dict={},
    )

    feature = Shock.DotFeature(sim_instance=sim_instance)

    assert feature.max_duration == 600
    assert feature.char_name_box == ["安比", "妮可"]
    assert feature.exist_buff_dict == {}


def test_shock_dot_duration_defaults_to_600_when_rina_passive_is_absent():
    sim_instance = _build_sim_instance(
        name_box=["丽娜", "安比"],
        exist_buff_dict={"丽娜": {}},
    )

    feature = Shock.DotFeature(sim_instance=sim_instance)

    assert feature.max_duration == 600
    assert feature.char_name_box == ["丽娜", "安比"]
    assert feature.exist_buff_dict == {"丽娜": {}}


def test_shock_dot_duration_extends_to_780_when_rina_passive_exists():
    passive_marker = object()
    sim_instance = _build_sim_instance(
        name_box=["丽娜", "安比"],
        exist_buff_dict={
            "丽娜": {RINA_SHOCK_DURATION_EXTENSION_BUFF_INDEX: passive_marker},
        },
    )

    feature = Shock.DotFeature(sim_instance=sim_instance)

    assert feature.max_duration == 780
    assert feature.char_name_box == ["丽娜", "安比"]
    assert feature.exist_buff_dict == {
        "丽娜": {RINA_SHOCK_DURATION_EXTENSION_BUFF_INDEX: passive_marker},
    }


def test_dot_initialization_read_context_preserves_old_sim_instance_reads():
    passive_marker = object()
    name_box = ["丽娜", "安比"]
    exist_buff_dict = {"丽娜": {RINA_SHOCK_DURATION_EXTENSION_BUFF_INDEX: passive_marker}}
    sim_instance = _build_sim_instance(name_box=name_box, exist_buff_dict=exist_buff_dict)

    read_context = DotInitializationReadContext.from_sim_instance(sim_instance)

    assert read_context.name_box is name_box
    assert read_context.exist_buff_dict is exist_buff_dict
    assert read_context.has_rina_shock_duration_extension() is True


def test_dot_initialization_read_context_reports_absent_rina_passive():
    sim_instance = _build_sim_instance(
        name_box=["丽娜", "安比"],
        exist_buff_dict={"丽娜": {}},
    )

    read_context = DotInitializationReadContext.from_sim_instance(sim_instance)

    assert read_context.has_rina_shock_duration_extension() is False


def test_shock_dot_duration_initialization_stays_in_read_only_layer():
    source = "\n".join(
        [
            inspect.getsource(Shock.DotFeature.__post_init__),
            inspect.getsource(DotInitializationReadContext),
        ]
    )

    forbidden_terms = [
        "ScheduleDispatchPort",
        "publish_scheduled",
        "schedule_data",
        "dynamic_dot_list",
        "listener_manager",
        "broadcast_event",
        "RuntimeCommandPort",
        "runtime_command",
        "BuffRuntimeReadPort",
        "Calculator",
        "CalAnomaly",
    ]

    for term in forbidden_terms:
        assert term not in source
