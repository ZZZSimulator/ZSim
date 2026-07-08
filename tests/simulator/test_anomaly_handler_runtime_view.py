from __future__ import annotations

import inspect
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any, cast

import pytest

from zsim.models.event_enums import ListenerBroadcastSignal as LBS
from zsim.sim_progress.anomaly_bar import AnomalyBar
from zsim.sim_progress.anomaly_bar.CopyAnomalyForOutput import (
    DirgeOfDestinyAnomaly,
    Disorder,
    NewAnomaly,
    PolarityDisorder,
)
from zsim.sim_progress.ScheduledEvent.buff_runtime import BuffRuntimeReadPort
from zsim.sim_progress.ScheduledEvent.event_handlers.context import EventContext
from zsim.sim_progress.ScheduledEvent.event_handlers.handlers import abloom as abloom_module
from zsim.sim_progress.ScheduledEvent.event_handlers.handlers import anomaly as anomaly_module
from zsim.sim_progress.ScheduledEvent.event_handlers.handlers import disorder as disorder_module
from zsim.sim_progress.ScheduledEvent.event_handlers.handlers import (
    polarity_disorder as polarity_disorder_module,
)
from zsim.sim_progress.ScheduledEvent.event_handlers.handlers.abloom import AbloomEventHandler
from zsim.sim_progress.ScheduledEvent.event_handlers.handlers.anomaly import AnomalyEventHandler
from zsim.sim_progress.ScheduledEvent.event_handlers.handlers.disorder import (
    DisorderEventHandler,
)
from zsim.sim_progress.ScheduledEvent.event_handlers.handlers.polarity_disorder import (
    PolarityDisorderEventHandler,
)

if TYPE_CHECKING:
    from zsim.sim_progress.ScheduledEvent.runtime_command import RuntimeCommandPort
    from zsim.simulator.simulator_class import Simulator


class _RuntimeViewProbe(BuffRuntimeReadPort):
    def __init__(
        self,
        dynamic_buff,
        exist_buff_dict,
        *,
        allow_legacy: bool,
        allow_active_view: bool = True,
    ) -> None:
        self.active_buff_view = {
            beneficiary: tuple(buffs) for beneficiary, buffs in dynamic_buff.items()
        }
        self.exist_buff_snapshot_view = {
            beneficiary: dict(buff_dict) for beneficiary, buff_dict in exist_buff_dict.items()
        }
        self.legacy_dynamic_buff = dynamic_buff
        self.legacy_exist_buff_dict = exist_buff_dict
        self.allow_legacy = allow_legacy
        self.allow_active_view = allow_active_view
        self.active_buff_calls = 0
        self.active_buff_beneficiaries: list[str] = []
        self.active_view_calls = 0
        self.snapshot_view_calls = 0
        self.legacy_dynamic_calls = 0
        self.legacy_exist_calls = 0

    def get_active_buffs(self, beneficiary: str):
        self.active_buff_calls += 1
        self.active_buff_beneficiaries.append(beneficiary)
        return self.active_buff_view.get(beneficiary, ())

    def get_active_buff_view(self):
        self.active_view_calls += 1
        if not self.allow_active_view:
            raise AssertionError("duration read should use get_active_buffs('enemy')")
        return self.active_buff_view

    def get_exist_buff_snapshot(self, beneficiary: str):
        return self.exist_buff_snapshot_view.get(beneficiary, {})

    def get_exist_buff_snapshot_view(self):
        self.snapshot_view_calls += 1
        return self.exist_buff_snapshot_view

    def get_legacy_dynamic_buff_dict(self):
        self.legacy_dynamic_calls += 1
        if not self.allow_legacy:
            raise AssertionError("legacy dynamic buff access should not happen on read-only path")
        return self.legacy_dynamic_buff

    def get_legacy_exist_buff_dict(self):
        self.legacy_exist_calls += 1
        if not self.allow_legacy:
            raise AssertionError("legacy exist buff access should not happen on read-only path")
        return self.legacy_exist_buff_dict


def _build_context(
    runtime_view: BuffRuntimeReadPort,
    runtime_command_port: Any = None,
) -> tuple[EventContext, list[dict]]:
    broadcasts: list[dict] = []
    enemy = SimpleNamespace(
        dynamic=SimpleNamespace(get_status=lambda: {}),
        update_stun=lambda stun: broadcasts.append({"stun": stun}),
    )
    sim_instance = SimpleNamespace(
        listener_manager=SimpleNamespace(
            broadcast_event=lambda **kwargs: broadcasts.append(kwargs),
        ),
    )
    context = EventContext(
        data=SimpleNamespace(),
        tick=10,
        enemy=enemy,
        buff_runtime_view=runtime_view,
        runtime_command_port=cast("RuntimeCommandPort", runtime_command_port or SimpleNamespace()),
        action_stack=SimpleNamespace(),
        sim_instance=cast("Simulator", sim_instance),
    )
    return context, broadcasts


def _build_copied_output_source(
    sim_instance: Any,
    *,
    element_type: int,
    rename_tag: str | None = None,
) -> AnomalyBar:
    bar = AnomalyBar(sim_instance=sim_instance, element_type=element_type)
    bar.rename_tag = rename_tag
    bar.max_duration = 600
    bar.last_active = 100
    bar.active = True
    return bar


def _build_activation(skill_tag: str = "1001_HANDLER_PAYLOAD"):
    return SimpleNamespace(
        char_name="handler-copied-output",
        skill_tag=skill_tag,
        skill=SimpleNamespace(char_obj=SimpleNamespace(CID=1001)),
    )


_HANDLER_REPORT_PARITY_CASES: tuple[dict[str, Any], ...] = (
    {
        "case_id": "anomaly",
        "module": anomaly_module,
        "handler_cls": AnomalyEventHandler,
        "event_kind": "anomaly",
        "calculator_name": "CalAnomaly",
        "calculator_event_kw": "anomaly_obj",
        "element_type": 4,
        "rename_tag": "copied-anomaly-report",
        "accompany_dot": "Shock",
        "anomaly_dmg_ratio": 2.15,
        "uuid": "new-anomaly-report-uuid",
        "damage": 12.346,
        "report_has_skill_tag": True,
        "report_skill_tag": "copied-anomaly-report",
        "report_has_is_disorder": False,
        "report_stun": 0,
        "broadcast_signal": None,
        "stun_update": None,
        "settles_buffs": True,
        "copied_payload_fields": (
            "element_type",
            "rename_tag",
            "accompany_dot",
            "anomaly_dmg_ratio",
            "max_duration",
            "last_active",
            "UUID",
        ),
    },
    {
        "case_id": "disorder",
        "module": disorder_module,
        "handler_cls": DisorderEventHandler,
        "event_kind": "disorder",
        "calculator_name": "CalDisorder",
        "calculator_event_kw": "disorder_obj",
        "element_type": 3,
        "rename_tag": "copied-disorder-report",
        "accompany_dot": "Shock",
        "anomaly_dmg_ratio": 2.25,
        "uuid": "disorder-report-uuid",
        "damage": 23.456,
        "report_has_skill_tag": True,
        "report_skill_tag": "感电",
        "report_has_is_disorder": True,
        "report_stun": 6.79,
        "broadcast_signal": LBS.DISORDER_SETTLED,
        "stun_update": 6.789,
        "settles_buffs": False,
        "copied_payload_fields": (
            "element_type",
            "rename_tag",
            "accompany_dot",
            "anomaly_dmg_ratio",
            "max_duration",
            "last_active",
            "UUID",
        ),
    },
    {
        "case_id": "polarity-disorder",
        "module": polarity_disorder_module,
        "handler_cls": PolarityDisorderEventHandler,
        "event_kind": "polarity_disorder",
        "calculator_name": "CalPolarityDisorder",
        "calculator_event_kw": "disorder_obj",
        "element_type": 6,
        "rename_tag": "copied-polarity-report",
        "accompany_dot": "AuricInk",
        "anomaly_dmg_ratio": 2.35,
        "uuid": "polarity-report-uuid",
        "damage": 34.567,
        "report_has_skill_tag": True,
        "report_skill_tag": "极性紊乱",
        "report_has_is_disorder": True,
        "report_stun": 0,
        "broadcast_signal": LBS.DISORDER_SETTLED,
        "stun_update": None,
        "settles_buffs": False,
        "polarity_disorder_ratio": 1.6,
        "additional_dmg_ap_ratio": 32,
        "copied_payload_fields": (
            "element_type",
            "rename_tag",
            "accompany_dot",
            "anomaly_dmg_ratio",
            "max_duration",
            "last_active",
            "UUID",
            "polarity_disorder_ratio",
            "additional_dmg_ap_ratio",
        ),
    },
    {
        "case_id": "abloom",
        "module": abloom_module,
        "handler_cls": AbloomEventHandler,
        "event_kind": "abloom",
        "calculator_name": "CalAbloom",
        "calculator_event_kw": "abloom_obj",
        "element_type": 1,
        "rename_tag": "copied-abloom-report",
        "accompany_dot": "Corruption",
        "anomaly_dmg_ratio": 1.3,
        "uuid": "abloom-report-uuid",
        "damage": 45.678,
        "report_has_skill_tag": True,
        "report_skill_tag": "异放",
        "report_has_is_disorder": False,
        "report_stun": 0,
        "broadcast_signal": None,
        "stun_update": None,
        "settles_buffs": False,
        "copied_payload_fields": (
            "element_type",
            "rename_tag",
            "accompany_dot",
            "anomaly_dmg_ratio",
            "max_duration",
            "last_active",
            "UUID",
        ),
    },
)


def _build_handler_report_event(case: dict[str, Any], sim_instance: Any):
    source = _build_copied_output_source(
        sim_instance,
        element_type=case["element_type"],
        rename_tag=case["rename_tag"],
    )
    source.accompany_dot = case["accompany_dot"]
    source.anomaly_dmg_ratio = case["anomaly_dmg_ratio"]
    source.max_duration = 620
    source.last_active = 140
    activation = _build_activation(f"1001_{case['case_id'].upper()}")
    event_kind = case["event_kind"]
    if event_kind == "anomaly":
        event = NewAnomaly(source, active_by=activation, sim_instance=sim_instance)
    elif event_kind == "disorder":
        event = Disorder(source, active_by=activation, sim_instance=sim_instance)
    elif event_kind == "polarity_disorder":
        event = PolarityDisorder(
            source,
            case["polarity_disorder_ratio"],
            active_by=activation,
            sim_instance=sim_instance,
        )
    elif event_kind == "abloom":
        event = DirgeOfDestinyAnomaly(
            source,
            active_by=activation,
            sim_instance=sim_instance,
        )
    else:
        raise AssertionError(f"Unknown handler report event kind: {event_kind}")
    event.UUID = case["uuid"]
    event.rename_tag = case["rename_tag"]
    event.accompany_dot = case["accompany_dot"]
    event.anomaly_dmg_ratio = case["anomaly_dmg_ratio"]
    return event


class _DurationBuffProbe:
    def __init__(
        self,
        *,
        index: str,
        active: bool,
        count: int,
        effect_dct: dict[str, float],
    ) -> None:
        self.ft = SimpleNamespace(index=index)
        self.dy = SimpleNamespace(active=active, count=count)
        self.effect_dct = effect_dct


class _FailFastLegacyDynamicBuff(dict):
    def get(self, *args, **kwargs):
        raise AssertionError("runtime view path should not read legacy dynamic_buff_dict")


_DURATION_TARGET_INDEX = "Buff-角色-丽娜-组队被动-延长感电"


def _build_duration_enemy_buffs() -> list[_DurationBuffProbe]:
    return [
        _DurationBuffProbe(
            index=_DURATION_TARGET_INDEX,
            active=True,
            count=2,
            effect_dct={
                "感电时间延长": 30,
                "所有异常时间延长百分比": 0.1,
            },
        ),
        _DurationBuffProbe(
            index=_DURATION_TARGET_INDEX,
            active=False,
            count=99,
            effect_dct={
                "感电时间延长": 999,
                "所有异常时间延长百分比": 9.9,
            },
        ),
        _DurationBuffProbe(
            index="Buff-其他",
            active=True,
            count=99,
            effect_dct={
                "感电时间延长": 999,
                "所有异常时间延长百分比": 9.9,
            },
        ),
    ]


def _build_duration_bar() -> AnomalyBar:
    bar = AnomalyBar(sim_instance=SimpleNamespace(), element_type=3)
    bar.basic_max_duration = 600
    bar.duration_buff_list = [_DURATION_TARGET_INDEX]
    bar.duration_buff_key_list = [
        "感电时间延长",
        "所有异常时间延长百分比",
    ]
    return bar


def _activate_duration_bar_with_runtime_view(
    bar: AnomalyBar,
    enemy_buffs: list[_DurationBuffProbe],
) -> _RuntimeViewProbe:
    runtime_view = _RuntimeViewProbe(
        {"enemy": enemy_buffs},
        {},
        allow_legacy=False,
        allow_active_view=False,
    )
    bar.change_info_cause_active(
        10,
        skill_node=SimpleNamespace(skill_tag="1001_TEST"),
        dynamic_buff_dict=_FailFastLegacyDynamicBuff(),
        buff_runtime_view=runtime_view,
    )
    return runtime_view


def test_anomaly_bar_duration_without_duration_buff_metadata_preserves_basic_duration():
    bar = _build_duration_bar()
    bar.duration_buff_list = None

    runtime_view = _activate_duration_bar_with_runtime_view(
        bar,
        _build_duration_enemy_buffs(),
    )

    assert bar.max_duration == 600
    assert runtime_view.active_buff_calls == 0
    assert runtime_view.active_view_calls == 0
    assert runtime_view.legacy_dynamic_calls == 0
    assert runtime_view.legacy_exist_calls == 0


def test_anomaly_bar_duration_empty_enemy_sequence_preserves_basic_duration():
    bar = _build_duration_bar()

    runtime_view = _activate_duration_bar_with_runtime_view(bar, [])

    assert bar.max_duration == 600
    assert runtime_view.active_buff_calls == 1
    assert runtime_view.active_buff_beneficiaries == ["enemy"]
    assert runtime_view.legacy_dynamic_calls == 0


def test_anomaly_bar_duration_ignores_inactive_matching_and_active_unrelated_buffs():
    bar = _build_duration_bar()
    enemy_buffs = [
        _DurationBuffProbe(
            index=_DURATION_TARGET_INDEX,
            active=False,
            count=99,
            effect_dct={
                "感电时间延长": 999,
                "所有异常时间延长百分比": 9.9,
            },
        ),
        _DurationBuffProbe(
            index="Buff-其他",
            active=True,
            count=99,
            effect_dct={
                "感电时间延长": 999,
                "所有异常时间延长百分比": 9.9,
            },
        ),
    ]

    runtime_view = _activate_duration_bar_with_runtime_view(bar, enemy_buffs)

    assert bar.max_duration == 600
    assert runtime_view.active_buff_calls == 1
    assert runtime_view.active_buff_beneficiaries == ["enemy"]


def test_anomaly_bar_duration_ignores_unknown_effect_keys():
    bar = _build_duration_bar()
    enemy_buffs = [
        _DurationBuffProbe(
            index=_DURATION_TARGET_INDEX,
            active=True,
            count=99,
            effect_dct={
                "未知持续时间延长": 999,
                "未知持续时间延长百分比": 9.9,
            },
        )
    ]

    runtime_view = _activate_duration_bar_with_runtime_view(bar, enemy_buffs)

    assert bar.max_duration == 600
    assert runtime_view.active_buff_calls == 1
    assert runtime_view.active_buff_beneficiaries == ["enemy"]


def test_anomaly_bar_duration_applies_fixed_duration_delta_from_key_list():
    bar = _build_duration_bar()
    enemy_buffs = [
        _DurationBuffProbe(
            index=_DURATION_TARGET_INDEX,
            active=True,
            count=1,
            effect_dct={"感电时间延长": 45},
        )
    ]

    runtime_view = _activate_duration_bar_with_runtime_view(bar, enemy_buffs)

    assert bar.max_duration == 645
    assert runtime_view.active_buff_calls == 1
    assert runtime_view.active_buff_beneficiaries == ["enemy"]


def test_anomaly_bar_duration_applies_percentage_duration_delta_from_key_list():
    bar = _build_duration_bar()
    enemy_buffs = [
        _DurationBuffProbe(
            index=_DURATION_TARGET_INDEX,
            active=True,
            count=1,
            effect_dct={"所有异常时间延长百分比": 0.25},
        )
    ]

    runtime_view = _activate_duration_bar_with_runtime_view(bar, enemy_buffs)

    assert bar.max_duration == pytest.approx(750)
    assert runtime_view.active_buff_calls == 1
    assert runtime_view.active_buff_beneficiaries == ["enemy"]


def test_anomaly_bar_duration_scales_fixed_and_percentage_effects_by_count():
    bar = _build_duration_bar()
    enemy_buffs = [
        _DurationBuffProbe(
            index=_DURATION_TARGET_INDEX,
            active=True,
            count=3,
            effect_dct={
                "感电时间延长": 10,
                "所有异常时间延长百分比": 0.05,
            },
        )
    ]

    runtime_view = _activate_duration_bar_with_runtime_view(bar, enemy_buffs)

    assert bar.max_duration == pytest.approx(720)
    assert runtime_view.active_buff_calls == 1
    assert runtime_view.active_buff_beneficiaries == ["enemy"]


def test_anomaly_bar_duration_accumulates_multiple_matching_buffs_order_independently():
    enemy_buffs = [
        _DurationBuffProbe(
            index=_DURATION_TARGET_INDEX,
            active=True,
            count=1,
            effect_dct={
                "感电时间延长": 15,
                "所有异常时间延长百分比": 0.1,
            },
        ),
        _DurationBuffProbe(
            index=_DURATION_TARGET_INDEX,
            active=True,
            count=2,
            effect_dct={
                "感电时间延长": -5,
                "所有异常时间延长百分比": 0.05,
            },
        ),
    ]

    first_bar = _build_duration_bar()
    second_bar = _build_duration_bar()
    first_runtime_view = _activate_duration_bar_with_runtime_view(first_bar, enemy_buffs)
    second_runtime_view = _activate_duration_bar_with_runtime_view(
        second_bar,
        list(reversed(enemy_buffs)),
    )

    assert first_bar.max_duration == pytest.approx(725)
    assert second_bar.max_duration == pytest.approx(first_bar.max_duration)
    assert first_runtime_view.active_buff_calls == 1
    assert second_runtime_view.active_buff_calls == 1
    assert first_runtime_view.active_buff_beneficiaries == ["enemy"]
    assert second_runtime_view.active_buff_beneficiaries == ["enemy"]


def test_anomaly_bar_duration_clamps_negative_effects_at_zero():
    bar = _build_duration_bar()
    enemy_buffs = [
        _DurationBuffProbe(
            index=_DURATION_TARGET_INDEX,
            active=True,
            count=1,
            effect_dct={
                "感电时间延长": -100,
                "所有异常时间延长百分比": -1.0,
            },
        )
    ]

    runtime_view = _activate_duration_bar_with_runtime_view(bar, enemy_buffs)

    assert bar.max_duration == 0
    assert runtime_view.active_buff_calls == 1
    assert runtime_view.active_buff_beneficiaries == ["enemy"]


def test_anomaly_bar_duration_read_accepts_legacy_enemy_fallback_without_runtime_view():
    enemy_buffs = _build_duration_enemy_buffs()
    bar = _build_duration_bar()

    bar.change_info_cause_active(
        10,
        skill_node=SimpleNamespace(skill_tag="1001_TEST"),
        dynamic_buff_dict={"enemy": enemy_buffs},
    )

    assert bar.max_duration == 780


def test_anomaly_bar_duration_read_missing_legacy_enemy_raises_type_error():
    bar = _build_duration_bar()

    with pytest.raises(TypeError, match="旧 dynamic_buff_dict 缺少 enemy Buff 列表"):
        bar.change_info_cause_active(
            10,
            skill_node=SimpleNamespace(skill_tag="1001_TEST"),
            dynamic_buff_dict={},
        )


def test_anomaly_bar_duration_read_none_dynamic_buff_dict_returns_empty_enemy_sequence():
    bar = _build_duration_bar()

    bar.change_info_cause_active(
        10,
        skill_node=SimpleNamespace(skill_tag="1001_TEST"),
        dynamic_buff_dict=cast(Any, None),
    )

    assert bar.max_duration == 600


def test_anomaly_bar_duration_read_uses_runtime_view_without_legacy_dynamic_container():
    enemy_buffs = _build_duration_enemy_buffs()
    skill_node = SimpleNamespace(skill_tag="1001_TEST")

    legacy_bar = _build_duration_bar()
    legacy_bar.change_info_cause_active(
        10,
        skill_node=skill_node,
        dynamic_buff_dict={"enemy": enemy_buffs},
    )

    runtime_view = _RuntimeViewProbe(
        {"enemy": enemy_buffs},
        {},
        allow_legacy=False,
        allow_active_view=False,
    )
    runtime_bar = _build_duration_bar()
    runtime_bar.change_info_cause_active(
        10,
        skill_node=skill_node,
        dynamic_buff_dict=_FailFastLegacyDynamicBuff(),
        buff_runtime_view=runtime_view,
    )

    assert runtime_bar.max_duration == legacy_bar.max_duration == 780
    assert runtime_view.active_buff_calls == 1
    assert runtime_view.active_buff_beneficiaries == ["enemy"]
    assert runtime_view.active_view_calls == 0
    assert runtime_view.legacy_dynamic_calls == 0
    assert runtime_view.legacy_exist_calls == 0


def test_abloom_handler_reads_active_buff_view_without_legacy_dynamic_container(
    monkeypatch: pytest.MonkeyPatch,
):
    runtime_view = _RuntimeViewProbe(
        {"alpha": [object()], "enemy": [object()]}, {}, allow_legacy=False
    )
    context, _ = _build_context(runtime_view)
    captured: dict[str, object] = {}

    class _FakeCalculator:
        def __init__(self, *, dynamic_buff, **kwargs) -> None:
            captured["dynamic_buff"] = dynamic_buff

        def cal_anomaly_dmg(self):
            return 12.34

    monkeypatch.setattr(abloom_module, "CalAbloom", _FakeCalculator)
    monkeypatch.setattr(abloom_module.Report, "report_dmg_result", lambda **kwargs: None)

    event = SimpleNamespace(element_type=1, UUID="abloom")
    AbloomEventHandler().handle(event, context)

    assert captured["dynamic_buff"] is runtime_view.active_buff_view
    assert runtime_view.active_view_calls == 1
    assert runtime_view.legacy_dynamic_calls == 0
    assert runtime_view.legacy_exist_calls == 0


@pytest.mark.parametrize(
    ("module", "handler_cls", "calculator_name"),
    [
        (disorder_module, DisorderEventHandler, "CalDisorder"),
        (polarity_disorder_module, PolarityDisorderEventHandler, "CalPolarityDisorder"),
    ],
)
def test_disorder_family_handlers_read_runtime_view_without_legacy_dynamic_container(
    monkeypatch: pytest.MonkeyPatch,
    module,
    handler_cls,
    calculator_name: str,
):
    runtime_view = _RuntimeViewProbe(
        {"alpha": [object()], "enemy": [object()]}, {}, allow_legacy=False
    )
    context, broadcasts = _build_context(runtime_view)
    captured: dict[str, object] = {}

    class _FakeCalculator:
        def __init__(self, *, dynamic_buff, **kwargs) -> None:
            captured["dynamic_buff"] = dynamic_buff

        def cal_anomaly_dmg(self):
            return 23.45

        def cal_disorder_stun(self):
            return 6.78

    monkeypatch.setattr(module, calculator_name, _FakeCalculator)
    monkeypatch.setattr(module.Report, "report_dmg_result", lambda **kwargs: None)

    event = SimpleNamespace(element_type=1, UUID="disorder")
    handler_cls().handle(event, context)

    assert captured["dynamic_buff"] is runtime_view.active_buff_view
    assert runtime_view.active_view_calls == 1
    assert runtime_view.legacy_dynamic_calls == 0
    assert runtime_view.legacy_exist_calls == 0
    assert broadcasts


def test_copied_anomaly_handler_reports_payload_fields_separate_from_settle_port(
    monkeypatch: pytest.MonkeyPatch,
):
    runtime_view = _RuntimeViewProbe(
        {"alpha": [object()], "enemy": [object()]}, {}, allow_legacy=False
    )
    captured: dict[str, object] = {}
    reports: list[dict[str, object]] = []

    class _RuntimeCommandPortProbe:
        def update_anomaly(self, **kwargs) -> None:
            raise AssertionError("report payload path should not issue update_anomaly")

        def settle_buffs(self, *, tick, enemy, skill_node=None, anomaly_bar=None) -> None:
            captured["settle_tick"] = tick
            captured["settle_enemy"] = enemy
            captured["settle_skill_node"] = skill_node
            captured["settle_anomaly_bar"] = anomaly_bar

    context, broadcasts = _build_context(
        runtime_view,
        runtime_command_port=_RuntimeCommandPortProbe(),
    )
    context.enemy.dynamic.get_status = lambda: {"enemy_status": "runtime"}

    class _FakeCalculator:
        def __init__(self, *, anomaly_obj, dynamic_buff, **kwargs) -> None:
            captured["calculator_event"] = anomaly_obj
            captured["dynamic_buff"] = dynamic_buff

        def cal_anomaly_dmg(self):
            return 12.346

    monkeypatch.setattr(anomaly_module, "CalAnomaly", _FakeCalculator)
    monkeypatch.setattr(
        anomaly_module.Report,
        "report_dmg_result",
        lambda **kwargs: reports.append(kwargs),
    )

    source = _build_copied_output_source(
        context.sim_instance,
        element_type=4,
        rename_tag="copied-anomaly-report",
    )
    event = NewAnomaly(
        source,
        active_by=_build_activation(),
        sim_instance=context.sim_instance,
    )
    event.UUID = "new-anomaly-report-uuid"

    AnomalyEventHandler().handle(event, context)

    assert reports == [
        {
            "tick": 10,
            "skill_tag": "copied-anomaly-report",
            "element_type": 4,
            "dmg_expect": 12.35,
            "is_anomaly": True,
            "dmg_crit": 12.35,
            "stun": 0,
            "buildup": 0,
            "enemy_status": "runtime",
            "UUID": "new-anomaly-report-uuid",
        }
    ]
    assert broadcasts == []
    assert captured["calculator_event"] is event
    assert captured["dynamic_buff"] is runtime_view.active_buff_view
    assert captured["settle_tick"] == 10
    assert captured["settle_enemy"] is context.enemy
    assert captured["settle_skill_node"] is None
    assert captured["settle_anomaly_bar"] is event
    assert runtime_view.active_view_calls == 1
    assert runtime_view.legacy_dynamic_calls == 0
    assert runtime_view.legacy_exist_calls == 0


def test_handler_report_layers_do_not_publish_dot_or_debuff():
    handler_modules = {
        "anomaly": anomaly_module,
        "disorder": disorder_module,
        "polarity_disorder": polarity_disorder_module,
        "abloom": abloom_module,
    }
    forbidden_terms = {
        "ScheduleDispatchPort",
        "create_schedule_dispatch_port",
        "publish_scheduled",
        "_publish_scheduled_event",
        "DotRuntimeStateAdapter",
        "spawn_anomaly_dot",
        "buff_add_strategy",
        "create_runtime_command_port",
        "update_anomaly(",
    }

    for name, module in handler_modules.items():
        source = inspect.getsource(module)
        for term in forbidden_terms:
            assert term not in source, f"{name} handler absorbed {term}"


def test_abloom_copied_output_handler_reports_payload_fields(
    monkeypatch: pytest.MonkeyPatch,
):
    runtime_view = _RuntimeViewProbe(
        {"alpha": [object()], "enemy": [object()]}, {}, allow_legacy=False
    )
    context, broadcasts = _build_context(runtime_view)
    context.enemy.dynamic.get_status = lambda: {"enemy_status": "runtime"}
    captured: dict[str, object] = {}
    reports: list[dict[str, object]] = []

    class _FakeCalculator:
        def __init__(self, *, abloom_obj, dynamic_buff, **kwargs) -> None:
            captured["calculator_event"] = abloom_obj
            captured["dynamic_buff"] = dynamic_buff

        def cal_anomaly_dmg(self):
            return 45.678

    monkeypatch.setattr(abloom_module, "CalAbloom", _FakeCalculator)
    monkeypatch.setattr(
        abloom_module.Report,
        "report_dmg_result",
        lambda **kwargs: reports.append(kwargs),
    )

    source = _build_copied_output_source(context.sim_instance, element_type=1)
    event = DirgeOfDestinyAnomaly(
        source,
        active_by=_build_activation("1001_ABLOOM"),
        sim_instance=context.sim_instance,
    )
    event.UUID = "abloom-report-uuid"

    AbloomEventHandler().handle(event, context)

    assert reports == [
        {
            "tick": 10,
            "element_type": 1,
            "skill_tag": "异放",
            "dmg_expect": 45.68,
            "is_anomaly": True,
            "dmg_crit": 45.68,
            "stun": 0,
            "buildup": 0,
            "enemy_status": "runtime",
            "UUID": "abloom-report-uuid",
        }
    ]
    assert broadcasts == []
    assert captured["calculator_event"] is event
    assert captured["dynamic_buff"] is runtime_view.active_buff_view
    assert runtime_view.active_view_calls == 1
    assert runtime_view.legacy_dynamic_calls == 0
    assert runtime_view.legacy_exist_calls == 0


def test_disorder_handler_reports_payload_and_listener_fields(
    monkeypatch: pytest.MonkeyPatch,
):
    runtime_view = _RuntimeViewProbe(
        {"alpha": [object()], "enemy": [object()]}, {}, allow_legacy=False
    )
    context, broadcasts = _build_context(runtime_view)
    context.enemy.dynamic.get_status = lambda: {"enemy_status": "runtime"}
    captured: dict[str, object] = {}
    reports: list[dict[str, object]] = []

    class _FakeCalculator:
        def __init__(self, *, disorder_obj, dynamic_buff, **kwargs) -> None:
            captured["calculator_event"] = disorder_obj
            captured["dynamic_buff"] = dynamic_buff

        def cal_anomaly_dmg(self):
            return 23.456

        def cal_disorder_stun(self):
            return 6.789

    monkeypatch.setattr(disorder_module, "CalDisorder", _FakeCalculator)
    monkeypatch.setattr(
        disorder_module.Report,
        "report_dmg_result",
        lambda **kwargs: reports.append(kwargs),
    )

    source = _build_copied_output_source(context.sim_instance, element_type=3)
    event = Disorder(
        source,
        active_by=_build_activation("1001_DISORDER"),
        sim_instance=context.sim_instance,
    )
    event.UUID = "disorder-report-uuid"

    DisorderEventHandler().handle(event, context)

    assert reports == [
        {
            "tick": 10,
            "element_type": 3,
            "skill_tag": "感电",
            "dmg_expect": 23.46,
            "dmg_crit": 23.46,
            "is_anomaly": True,
            "is_disorder": True,
            "stun": 6.79,
            "buildup": 0,
            "enemy_status": "runtime",
            "UUID": "disorder-report-uuid",
        }
    ]
    assert broadcasts[0] == {"event": event, "signal": LBS.DISORDER_SETTLED}
    assert broadcasts[1]["stun"] == pytest.approx(6.789)
    assert captured["calculator_event"] is event
    assert captured["dynamic_buff"] is runtime_view.active_buff_view
    assert runtime_view.active_view_calls == 1
    assert runtime_view.legacy_dynamic_calls == 0
    assert runtime_view.legacy_exist_calls == 0


def test_polarity_disorder_handler_reports_payload_and_listener_fields(
    monkeypatch: pytest.MonkeyPatch,
):
    runtime_view = _RuntimeViewProbe(
        {"alpha": [object()], "enemy": [object()]}, {}, allow_legacy=False
    )
    context, broadcasts = _build_context(runtime_view)
    context.enemy.dynamic.get_status = lambda: {"enemy_status": "runtime"}
    captured: dict[str, object] = {}
    reports: list[dict[str, object]] = []

    class _FakeCalculator:
        def __init__(self, *, disorder_obj, dynamic_buff, **kwargs) -> None:
            captured["calculator_event"] = disorder_obj
            captured["dynamic_buff"] = dynamic_buff

        def cal_anomaly_dmg(self):
            return 34.567

    monkeypatch.setattr(polarity_disorder_module, "CalPolarityDisorder", _FakeCalculator)
    monkeypatch.setattr(
        polarity_disorder_module.Report,
        "report_dmg_result",
        lambda **kwargs: reports.append(kwargs),
    )

    source = _build_copied_output_source(context.sim_instance, element_type=6)
    event = PolarityDisorder(
        source,
        1.6,
        active_by=_build_activation("1001_POLARITY"),
        sim_instance=context.sim_instance,
    )
    event.UUID = "polarity-report-uuid"

    PolarityDisorderEventHandler().handle(event, context)

    assert reports == [
        {
            "tick": 10,
            "element_type": 6,
            "skill_tag": "极性紊乱",
            "dmg_expect": 34.57,
            "dmg_crit": 34.57,
            "is_anomaly": True,
            "is_disorder": True,
            "stun": 0,
            "buildup": 0,
            "enemy_status": "runtime",
            "UUID": "polarity-report-uuid",
        }
    ]
    assert broadcasts == [{"event": event, "signal": LBS.DISORDER_SETTLED}]
    assert captured["calculator_event"] is event
    assert captured["dynamic_buff"] is runtime_view.active_buff_view
    assert runtime_view.active_view_calls == 1
    assert runtime_view.legacy_dynamic_calls == 0
    assert runtime_view.legacy_exist_calls == 0


@pytest.mark.parametrize(
    "case",
    _HANDLER_REPORT_PARITY_CASES,
    ids=lambda case: case["case_id"],
)
def test_copied_output_handler_report_payload_fields_match_retained_contracts(
    monkeypatch: pytest.MonkeyPatch,
    case: dict[str, Any],
):
    runtime_view = _RuntimeViewProbe(
        {"alpha": [object()], "enemy": [object()]}, {}, allow_legacy=False
    )
    captured: dict[str, Any] = {"settle_calls": []}
    reports: list[dict[str, Any]] = []

    class _RuntimeCommandPortProbe:
        def update_anomaly(self, **kwargs) -> None:
            raise AssertionError("handler report parity should not update anomaly state")

        def settle_buffs(self, **kwargs) -> None:
            captured["settle_calls"].append(kwargs)

    context, broadcasts = _build_context(
        runtime_view,
        runtime_command_port=_RuntimeCommandPortProbe(),
    )
    context.enemy.dynamic.get_status = lambda: {"enemy_status": case["case_id"]}
    event = _build_handler_report_event(case, context.sim_instance)
    calculator_calls: list[dict[str, Any]] = []

    class _FakeCalculator:
        def __init__(self, **kwargs) -> None:
            calculator_calls.append(kwargs)

        def cal_anomaly_dmg(self):
            return case["damage"]

        def cal_disorder_stun(self):
            return case.get("stun_update", 0)

    monkeypatch.setattr(case["module"], case["calculator_name"], _FakeCalculator)
    monkeypatch.setattr(
        case["module"].Report,
        "report_dmg_result",
        lambda **kwargs: reports.append(kwargs),
    )

    case["handler_cls"]().handle(event, context)

    copied_payload = {
        field_name: getattr(event, field_name) for field_name in case["copied_payload_fields"]
    }
    expected_copied_payload = {
        "element_type": case["element_type"],
        "rename_tag": case["rename_tag"],
        "accompany_dot": case["accompany_dot"],
        "anomaly_dmg_ratio": case["anomaly_dmg_ratio"],
        "max_duration": 620,
        "last_active": 140,
        "UUID": case["uuid"],
    }
    if case["event_kind"] == "polarity_disorder":
        expected_copied_payload.update(
            {
                "polarity_disorder_ratio": case["polarity_disorder_ratio"],
                "additional_dmg_ap_ratio": case["additional_dmg_ap_ratio"],
            }
        )
    assert copied_payload == expected_copied_payload

    assert len(calculator_calls) == 1
    calculator_call = calculator_calls[0]
    assert calculator_call[case["calculator_event_kw"]] is event
    assert calculator_call["enemy_obj"] is context.enemy
    assert calculator_call["dynamic_buff"] is runtime_view.active_buff_view
    assert calculator_call["sim_instance"] is context.sim_instance

    expected_report = {
        "tick": 10,
        "element_type": case["element_type"],
        "dmg_expect": round(case["damage"], 2),
        "is_anomaly": True,
        "dmg_crit": round(case["damage"], 2),
        "stun": case["report_stun"],
        "buildup": 0,
        "enemy_status": case["case_id"],
        "UUID": case["uuid"],
    }
    if case["report_has_skill_tag"]:
        expected_report["skill_tag"] = case["report_skill_tag"]
    if case["report_has_is_disorder"]:
        expected_report["is_disorder"] = True
    assert reports == [expected_report]

    listener_broadcasts = [entry for entry in broadcasts if "signal" in entry]
    if case["broadcast_signal"] is None:
        assert listener_broadcasts == []
    else:
        assert listener_broadcasts == [{"event": event, "signal": case["broadcast_signal"]}]
    stun_updates = [entry for entry in broadcasts if "stun" in entry]
    if case["stun_update"] is None:
        assert stun_updates == []
    else:
        assert stun_updates == [{"stun": pytest.approx(case["stun_update"])}]

    settle_calls = captured["settle_calls"]
    if case["settles_buffs"]:
        assert settle_calls == [
            {
                "tick": 10,
                "enemy": context.enemy,
                "anomaly_bar": event,
            }
        ]
    else:
        assert settle_calls == []
    assert runtime_view.active_view_calls == 1
    assert runtime_view.legacy_dynamic_calls == 0
    assert runtime_view.legacy_exist_calls == 0


def test_anomaly_handler_uses_runtime_command_port_for_settle_boundary(
    monkeypatch: pytest.MonkeyPatch,
):
    legacy_dynamic_buff = {"alpha": [object()], "enemy": [object()]}
    legacy_exist_buff_dict = {"alpha": {"alpha-buff": object()}, "enemy": {}}
    runtime_view = _RuntimeViewProbe(
        legacy_dynamic_buff,
        legacy_exist_buff_dict,
        allow_legacy=False,
    )
    captured: dict[str, object] = {}

    class _RuntimeCommandPortProbe:
        def update_anomaly(self, **kwargs) -> None:
            raise AssertionError("anomaly handler should not issue update_anomaly")

        def settle_buffs(self, *, tick, enemy, skill_node=None, anomaly_bar=None) -> None:
            captured["settle_tick"] = tick
            captured["settle_enemy"] = enemy
            captured["settle_skill_node"] = skill_node
            captured["settle_anomaly_bar"] = anomaly_bar

    runtime_command_port = _RuntimeCommandPortProbe()
    context, _ = _build_context(runtime_view, runtime_command_port=runtime_command_port)

    class _FakeCalculator:
        def __init__(self, *, dynamic_buff, **kwargs) -> None:
            captured["dynamic_buff"] = dynamic_buff

        def cal_anomaly_dmg(self):
            return 34.56

    monkeypatch.setattr(anomaly_module, "CalAnomaly", _FakeCalculator)
    monkeypatch.setattr(anomaly_module.Report, "report_dmg_result", lambda **kwargs: None)

    handler = AnomalyEventHandler()
    monkeypatch.setattr(handler, "_validate_event", lambda *args, **kwargs: None)
    event = SimpleNamespace(rename=False, rename_tag=None, element_type=1, UUID="anomaly")

    handler.handle(event, context)

    assert captured["dynamic_buff"] is runtime_view.active_buff_view
    assert captured["settle_tick"] == 10
    assert captured["settle_enemy"] is context.enemy
    assert captured["settle_skill_node"] is None
    assert captured["settle_anomaly_bar"] is event
    assert runtime_view.active_view_calls == 1
    assert runtime_view.legacy_dynamic_calls == 0
    assert runtime_view.legacy_exist_calls == 0
