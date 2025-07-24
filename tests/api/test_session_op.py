import pytest
from fastapi.testclient import TestClient
from zsim.api import app
from zsim.api_src.services.database.session_db import get_session_db
from zsim.models.session.session_create import Session
from zsim.models.session.session_run import SessionRun

client = TestClient(app)

@pytest.fixture
def session_data():
    return {
        "session_id": "test_session",
        "session_name": "Test Session",
        "session_type": "test",
        "apl_file_path": "data/APL/test_apl.toml",
        "character_config_path": "test/path",
        "enemy_config_path": "test/path",
        "simulation_config_path": "test/path",
    }

@pytest.fixture
def session_run_data():
    return {
        "common_config": {
            "session_id": "test_session",
            "char_config": [
                {"name": "仪玄"},
                {"name": "耀嘉音"},
                {"name": "扳机"},
            ],
            "enemy_config": {"index_id": 11412, "adjustment_id": 22412},
            "apl_path": "zsim/data/APLData/仪玄-耀嘉音-扳机.toml",
        },
        "mode": "normal",
    }


@pytest.mark.asyncio
async def test_create_session(session_data):
    db = await get_session_db()
    await db.delete_session("test_session")

    response = client.post("/api/sessions/", json=session_data)
    assert response.status_code == 200
    data = response.json()
    assert data["session_id"] == "test_session"

@pytest.mark.asyncio
async def test_read_sessions(session_data):
    db = await get_session_db()
    await db.delete_session("test_session")
    session = Session(**session_data)
    await db.add_session(session)

    response = client.get("/api/sessions/")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0

@pytest.mark.asyncio
async def test_read_session(session_data):
    db = await get_session_db()
    await db.delete_session("test_session")
    session = Session(**session_data)
    await db.add_session(session)

    response = client.get(f"/api/sessions/{session_data['session_id']}")
    assert response.status_code == 200
    data = response.json()
    assert data["session_id"] == session_data["session_id"]

@pytest.mark.asyncio
async def test_get_session_status(session_data):
    db = await get_session_db()
    await db.delete_session("test_session")
    session = Session(**session_data)
    await db.add_session(session)

    response = client.get(f"/api/sessions/{session_data['session_id']}/status")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "result" in data

@pytest.mark.asyncio
async def test_run_session(session_data, session_run_data):
    db = await get_session_db()
    await db.delete_session("test_session")
    session = Session(**session_data)
    await db.add_session(session)

    response = client.post(f"/api/sessions/{session_data['session_id']}/run?test_mode=true", json=session_run_data)
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Session started successfully"

    # Check that the session status is now "completed"
    response = client.get(f"/api/sessions/{session_data['session_id']}/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"

@pytest.mark.asyncio
async def test_stop_session(session_data, session_run_data):
    db = await get_session_db()
    await db.delete_session("test_session")
    session = Session(**session_data)
    session.status = "running"
    await db.add_session(session)

    response = client.post(f"/api/sessions/{session_data['session_id']}/stop")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "stopped"

@pytest.mark.asyncio
async def test_update_session(session_data):
    db = await get_session_db()
    await db.delete_session("test_session")
    session = Session(**session_data)
    await db.add_session(session)

    updated_data = session_data.copy()
    updated_data["session_name"] = "Updated Test Session"

    response = client.put(f"/api/sessions/{session_data['session_id']}", json=updated_data)
    assert response.status_code == 200
    data = response.json()
    assert data["session_name"] == "Updated Test Session"

@pytest.mark.asyncio
async def test_delete_session(session_data):
    db = await get_session_db()
    await db.delete_session("test_session")
    session = Session(**session_data)
    await db.add_session(session)

    response = client.delete(f"/api/sessions/{session_data['session_id']}")
    assert response.status_code == 204

    response = client.get(f"/api/sessions/{session_data['session_id']}")
    assert response.status_code == 404
