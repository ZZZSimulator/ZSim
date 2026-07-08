import json
from collections.abc import Callable

import polars as pl
import pytest

from zsim.lib_webui import process_buff_result as webui_buff
from zsim.lib_webui import process_dmg_result as webui_dmg
from zsim.models.session.session_result import (
    BUFF_TIMELINE_PUBLIC_FIELDS,
    DAMAGE_RESULT_SECTIONS,
    DAMAGE_UUID_AGGREGATE_FIELDS,
    NORMAL_RESULT_OPTIONAL_SECTIONS,
    AttrCurvePayload,
    BuffResult,
    DmgResult,
    NormalModeResult,
    NormalResultPayload,
    ParallelAttrCurveResultPayload,
    ParallelModeResult,
    ParallelResultPayload,
    build_buff_timeline_entry,
    normalize_buff_timeline_payload,
    normalize_damage_result_schema,
)
from zsim.utils import main_loop_consistency as mlc
from zsim.utils import process_buff_result as utility_buff
from zsim.utils import process_dmg_result as utility_dmg

DamageNormalizer = Callable[[pl.DataFrame], pl.DataFrame]


@pytest.mark.parametrize(
    ("frame", "expected"),
    [
        (pl.DataFrame({"damage": [1.0, 2.0]}), [False, False]),
        (
            pl.DataFrame(
                {
                    "damage": [1.0, 2.0],
                    "is_anomaly": pl.Series([None, None], dtype=pl.Null),
                }
            ),
            [False, False],
        ),
        (
            pl.DataFrame({"damage": [1.0, 2.0], "is_anomaly": [True, None]}),
            [True, False],
        ),
        (
            pl.DataFrame({"damage": [1.0, 2.0, 3.0], "is_anomaly": ["true", "1", "false"]}),
            [True, True, False],
        ),
    ],
)
def test_damage_schema_normalization_is_shared_by_data_analysis_processors(
    frame: pl.DataFrame,
    expected: list[bool],
) -> None:
    normalizers: tuple[DamageNormalizer, ...] = (
        normalize_damage_result_schema,
        utility_dmg._normalize_damage_schema,
        webui_dmg._normalize_damage_schema,
        mlc._normalize_consistency_damage_df,
    )

    for normalize in normalizers:
        normalized = normalize(frame)
        assert normalized["is_anomaly"].to_list() == expected


def test_buff_timeline_public_fields_are_shared_by_processors_and_parity() -> None:
    timeline_frame = pl.DataFrame(
        {
            "time_tick": [1, 2, 3],
            "buff_alpha": [0.0, 1.0, 1.0],
            "buff_beta": [None, 2.0, 0.0],
        }
    )

    utility_entries = utility_buff._prepare_buff_timeline_data(timeline_frame)
    webui_entries = webui_buff._prepare_buff_timeline_data(timeline_frame)
    expected_payload = normalize_buff_timeline_payload({"source": utility_entries})

    assert utility_entries == webui_entries
    assert mlc._normalize_buff_timeline_payload({"source": webui_entries}) == expected_payload
    summary = mlc._buff_timeline_summary(
        present=True,
        source_type="json",
        source_paths=[],
        timeline=expected_payload,
        records=mlc._buff_timeline_records(expected_payload),
    )
    assert summary["public_fields"] == list(BUFF_TIMELINE_PUBLIC_FIELDS)
    assert {tuple(entry) for entry in utility_entries} == {BUFF_TIMELINE_PUBLIC_FIELDS}


def test_buff_timeline_normalizes_legacy_integer_display_by_task_name() -> None:
    payload = normalize_buff_timeline_payload(
        {
            "爱丽丝": [
                {
                    "Task": "Buff-角色-柚叶-组队被动-积蓄值增幅",
                    "Start": 1,
                    "Finish": 2,
                    "Value": 63.919998,
                }
            ],
            "柚叶": [
                {
                    "Task": "Buff-角色-柚叶-组队被动-积蓄值增幅",
                    "Start": 1,
                    "Finish": 2,
                    "Value": 63.919998,
                }
            ],
        }
    )

    assert payload["爱丽丝"][0]["Value"] == 63.0
    assert payload["柚叶"][0]["Value"] == 63.0


def test_normal_mode_result_serializes_data_analysis_contract_shape() -> None:
    damage_uuid_row = {field: None for field in DAMAGE_UUID_AGGREGATE_FIELDS}
    damage_uuid_row.update(
        {
            "UUID": "attack-1",
            "name": "agent",
            "element_type": "electric",
            "is_anomaly": False,
            "dmg_expect_sum": 10.0,
        }
    )
    damage_payload = {section: [] for section in DAMAGE_RESULT_SECTIONS}
    damage_payload["uuid_df"] = [damage_uuid_row]
    buff_payload = {
        "agent": [
            build_buff_timeline_entry(
                task="buff_alpha",
                start=1,
                finish=3,
                value=2.0,
            )
        ]
    }

    result = NormalModeResult(
        mode="normal",
        result=NormalResultPayload(
            dmg_result=DmgResult(root=damage_payload),
            buff_result=BuffResult(root=buff_payload),
        ),
    )

    dumped = result.model_dump(mode="json")
    json.dumps(dumped)

    assert tuple(dumped["result"]) == NORMAL_RESULT_OPTIONAL_SECTIONS
    assert tuple(dumped["result"]["dmg_result"]) == DAMAGE_RESULT_SECTIONS
    buff_entry = dumped["result"]["buff_result"]["agent"][0]
    assert tuple(buff_entry) == BUFF_TIMELINE_PUBLIC_FIELDS
    assert "task" not in buff_entry


def test_normal_mode_result_accepts_current_and_internal_buff_timeline_payloads() -> None:
    result = NormalModeResult(
        mode="normal",
        result=NormalResultPayload(
            dmg_result=DmgResult(root=None),
            buff_result=BuffResult(
                root={
                    "alias_payload": [{"Task": "buff_alpha", "Start": 1, "Finish": 2, "Value": 1}],
                    "field_payload": [{"task": "buff_beta", "start": 3, "finish": 4, "value": 2.5}],
                }
            ),
        ),
    )

    dumped = result.model_dump(mode="json")

    assert dumped["result"]["buff_result"]["alias_payload"][0] == {
        "Task": "buff_alpha",
        "Start": 1,
        "Finish": 2,
        "Value": 1.0,
    }
    assert dumped["result"]["buff_result"]["field_payload"][0] == {
        "Task": "buff_beta",
        "Start": 3,
        "Finish": 4,
        "Value": 2.5,
    }


def test_parallel_result_contract_still_validates() -> None:
    payload = ParallelAttrCurveResultPayload(
        func="attr_curve",
        result=AttrCurvePayload(
            root={
                "agent": {
                    "atk": {
                        "1": {
                            "result": 100.0,
                            "rate": None,
                        }
                    }
                }
            }
        ),
    )
    result = ParallelModeResult(
        mode="parallel",
        func="attr_curve",
        result=ParallelResultPayload(root=payload),
    )

    dumped = result.model_dump(mode="json")

    assert dumped["mode"] == "parallel"
    assert dumped["func"] == "attr_curve"
    assert dumped["result"]["func"] == "attr_curve"
    assert dumped["result"]["result"]["agent"]["atk"]["1"] == {
        "result": 100.0,
        "rate": None,
    }


def test_matrix_summary_contract_is_serializable_for_data_analysis_consumers() -> None:
    diff_domain_status = {
        "damage": {
            "expected": True,
            "implemented": True,
            "status": "match",
            "matches": True,
        },
        "damage_attribution": {
            "expected": False,
            "implemented": True,
            "status": "not_provided",
            "matches": True,
        },
        "buff_timeline": {
            "expected": True,
            "implemented": True,
            "status": "match",
            "matches": True,
        },
    }
    row = {
        "schema": mlc.EXTERNAL_GOLDEN_MATRIX_ROW_SCHEMA,
        "row_id": "contract-smoke",
        "status": "pass",
        "signoff_effect": "pass",
        "reason_code": "passed",
        "reason": "all expected external golden domains matched",
        "golden_result_dir": "tests/fixtures/external_golden_parity/buff-csv-golden",
        "config_identity": {
            "kind": "team",
            "team": "fake-team",
            "common_cfg_path": None,
        },
        "apl": "./fixture.toml",
        "stop_tick": 9,
        "expected_domains": ["damage", "buff_timeline"],
        "tolerance_policy": {},
        "signoff_label": "data-analysis-contract",
        "missing_input_policy": "block",
        "diff_domain_status": diff_domain_status,
        "mismatch_samples": {},
        "data_analysis_contract": mlc._external_golden_data_analysis_contract(diff_domain_status),
    }

    summary = mlc.build_external_golden_matrix_summary(
        rows=[row],
        matrix_source={"kind": "contract-smoke", "path": None, "schema": None},
        generated_at="2026-06-24T00:00:00+0800",
    )
    dumped = json.loads(json.dumps(summary))

    assert dumped["data_analysis_contract"]["normal_mode_sections"] == list(
        NORMAL_RESULT_OPTIONAL_SECTIONS
    )
    row_contract = dumped["rows"][0]["data_analysis_contract"]
    assert row_contract["damage"]["result_sections"] == list(DAMAGE_RESULT_SECTIONS)
    assert row_contract["damage"]["uuid_aggregate_fields"] == list(DAMAGE_UUID_AGGREGATE_FIELDS)
    assert row_contract["damage"]["domain_status"] == diff_domain_status["damage"]
    assert row_contract["buff_timeline"]["public_fields"] == list(BUFF_TIMELINE_PUBLIC_FIELDS)
    assert row_contract["buff_timeline"]["domain_status"] == diff_domain_status["buff_timeline"]
    assert row_contract["parallel_mode"] == {
        "status": "unchanged",
        "model": "ParallelModeResult",
    }
