import asyncio
import json

import pytest
from fastapi.testclient import TestClient

from zsim.api import app
from zsim.api_src.services.database.session_db import get_session_db
from zsim.api_src.services.sim_controller import sim_controller as controller_module
from zsim.api_src.services.sim_controller.sim_controller import SimController
from zsim.models.session.session_result import (
    BUFF_TIMELINE_PUBLIC_FIELDS,
    DAMAGE_RESULT_SECTIONS,
    NORMAL_RESULT_OPTIONAL_SECTIONS,
    BuffResult,
    DmgResult,
    NormalModeResult,
    NormalResultPayload,
)
from zsim.simulator.simulator_class import Confirmation
from zsim.utils import main_loop_consistency as mlc

client = TestClient(app)
SMOKE_SESSION_ID = "electron-smoke-contract-session"


def _session_payload() -> dict[str, object]:
    return {
        "session_id": SMOKE_SESSION_ID,
        "session_name": "Electron smoke contract",
    }


def _session_run_payload() -> dict[str, object]:
    return {
        "stop_tick": 1,
        "mode": "normal",
        "common_config": {
            "session_id": SMOKE_SESSION_ID,
            "char_config": [
                {"name": "仪玄"},
                {"name": "耀嘉音"},
                {"name": "扳机"},
            ],
            "enemy_config": {"index_id": 11412, "adjustment_id": 22412},
            "apl_path": "zsim/data/APLData/仪玄-耀嘉音-扳机.toml",
        },
    }


def _matrix_smoke_summary() -> dict[str, object]:
    diff_domain_status = {
        "damage": {
            "expected": True,
            "implemented": True,
            "status": "match",
            "matches": True,
        },
        "buff_timeline": {
            "expected": True,
            "implemented": True,
            "status": "match",
            "matches": True,
        },
    }
    selected_row = {
        "schema": mlc.EXTERNAL_GOLDEN_MATRIX_ROW_SCHEMA,
        "row_id": "electron-api-smoke-selected-row",
        "status": "pass",
        "signoff_effect": "provisional",
        "reason_code": "fixture-contract-smoke",
        "reason": "selected matrix row is compatible with the API smoke result contract",
        "golden_result_dir": "tests/fixtures/external_golden_parity/buff-csv-golden",
        "config_identity": {
            "kind": "team",
            "team": "fake-team",
            "common_cfg_path": None,
        },
        "apl": "./fixture.toml",
        "stop_tick": 1,
        "expected_domains": ["damage", "buff_timeline"],
        "tolerance_policy": {},
        "signoff_label": "webui-api-smoke",
        "missing_input_policy": "block",
        "diff_domain_status": diff_domain_status,
        "mismatch_samples": {},
        "data_analysis_contract": mlc._external_golden_data_analysis_contract(diff_domain_status),
    }
    return mlc.build_external_golden_matrix_summary(
        rows=[selected_row],
        matrix_source={"kind": "webui-api-smoke", "path": None, "schema": None},
        generated_at="2026-06-24T00:00:00+0800",
    )


@pytest.mark.asyncio
async def test_electron_normal_full_simulation_smoke_contract(monkeypatch) -> None:
    db = await get_session_db()
    await db.delete_session(SMOKE_SESSION_ID)

    controller = SimController()
    controller._queue = asyncio.Queue()
    controller._running_tasks.clear()

    def fake_runtime_simulator(common_cfg, sim_cfg, stop_tick):
        assert common_cfg.session_id == SMOKE_SESSION_ID
        assert sim_cfg is None
        assert stop_tick == 1
        return Confirmation(
            session_id=common_cfg.session_id,
            status="completed",
            timestamp=1,
            sim_cfg=sim_cfg,
        )

    async def fake_process_simulation_result(self, confirmation):
        assert confirmation.session_id == SMOKE_SESSION_ID
        damage_payload = {section: [] for section in DAMAGE_RESULT_SECTIONS}
        return NormalModeResult(
            mode="normal",
            result=NormalResultPayload(
                dmg_result=DmgResult(root=damage_payload),
                buff_result=BuffResult(
                    root={
                        "smoke-agent": [
                            {
                                "Task": "smoke-buff",
                                "Start": 1,
                                "Finish": 2,
                                "Value": 1.0,
                            }
                        ]
                    }
                ),
            ),
        )

    monkeypatch.setattr(
        controller_module,
        "_run_default_runtime_simulator",
        fake_runtime_simulator,
    )
    monkeypatch.setattr(
        SimController,
        "_process_simulation_result",
        fake_process_simulation_result,
    )

    try:
        create_response = client.post("/api/sessions/", json=_session_payload())
        assert create_response.status_code == 200

        run_response = client.post(
            f"/api/sessions/{SMOKE_SESSION_ID}/run?test_mode=true",
            json=_session_run_payload(),
        )
        assert run_response.status_code == 200
        assert run_response.json() == {
            "code": 0,
            "message": "会话已启动",
            "session_id": SMOKE_SESSION_ID,
        }

        status_response = client.get(f"/api/sessions/{SMOKE_SESSION_ID}/status")
        assert status_response.status_code == 200
        status_payload = status_response.json()
        assert status_payload["status"] == "completed"

        result_payload = status_payload["result"]
        assert isinstance(result_payload, list)
        assert result_payload[0]["mode"] == "normal"

        data_analysis_payload = result_payload[0]["result"]
        assert tuple(data_analysis_payload) == ("dmg_result", "buff_result")
        assert tuple(data_analysis_payload["dmg_result"]) == DAMAGE_RESULT_SECTIONS

        buff_entry = data_analysis_payload["buff_result"]["smoke-agent"][0]
        assert tuple(buff_entry) == BUFF_TIMELINE_PUBLIC_FIELDS

        read_response = client.get(f"/api/sessions/{SMOKE_SESSION_ID}")
        assert read_response.status_code == 200
        read_payload = read_response.json()
        assert read_payload["session_result"] == result_payload

        matrix_summary = _matrix_smoke_summary()
        selected_matrix_row = matrix_summary["rows"][0]
        selected_contract = selected_matrix_row["data_analysis_contract"]

        assert matrix_summary["schema"] == mlc.EXTERNAL_GOLDEN_MATRIX_SCHEMA
        assert selected_contract["normal_mode_sections"] == list(NORMAL_RESULT_OPTIONAL_SECTIONS)
        assert set(selected_contract["normal_mode_sections"]) == set(data_analysis_payload)
        assert (
            tuple(selected_contract["buff_timeline"]["public_fields"])
            == BUFF_TIMELINE_PUBLIC_FIELDS
        )
        assert tuple(buff_entry) == tuple(selected_contract["buff_timeline"]["public_fields"])

        matrix_aware_payload = {
            **read_payload,
            "matrix_signoff": {
                "schema": matrix_summary["schema"],
                "signoff_status": matrix_summary["signoff_status"],
                "row_count": matrix_summary["row_count"],
            },
            "selected_matrix_row": selected_matrix_row,
        }
        json.dumps(matrix_aware_payload)
        assert matrix_aware_payload["session_result"] == result_payload
        assert matrix_aware_payload["selected_matrix_row"]["row_id"] == (
            "electron-api-smoke-selected-row"
        )
    finally:
        await db.delete_session(SMOKE_SESSION_ID)
        controller._queue = asyncio.Queue()
