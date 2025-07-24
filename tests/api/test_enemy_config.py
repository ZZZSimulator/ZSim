import pytest
from fastapi.testclient import TestClient
from zsim.api import app
from zsim.api_src.services.database.enemy_db import get_enemy_db
from zsim.models.enemy.enemy_config import EnemyConfig

client = TestClient(app)


@pytest.fixture
def enemy_config_data():
    return {
        "config_id": "test_enemy_config",
        "enemy_index": 1,
        "enemy_adjust": {"def": 0.5, "res": 0.2},
    }


@pytest.mark.asyncio
async def test_create_enemy_config(enemy_config_data):
    # 清理之前的测试数据
    db = await get_enemy_db()
    await db.delete_enemy_config("test_enemy_config")

    # 创建敌人配置
    response = client.post("/api/enemy-configs/", json=enemy_config_data)
    assert response.status_code == 200
    data = response.json()
    assert data["config_id"] == "test_enemy_config"
    assert data["enemy_index"] == 1
    assert "enemy_adjust" in data
    assert "create_time" in data
    assert "update_time" in data


@pytest.mark.asyncio
async def test_get_enemy_config(enemy_config_data):
    # 首先创建一个配置
    db = await get_enemy_db()
    await db.delete_enemy_config("test_enemy_config")
    config = EnemyConfig(**enemy_config_data)
    await db.add_enemy_config(config)

    # 获取敌人配置
    response = client.get("/api/enemy-configs/test_enemy_config")
    assert response.status_code == 200
    data = response.json()
    assert data["config_id"] == "test_enemy_config"
    assert data["enemy_index"] == 1


@pytest.mark.asyncio
async def test_list_enemy_configs(enemy_config_data):
    # 首先创建一个配置
    db = await get_enemy_db()
    await db.delete_enemy_config("test_enemy_config")
    config = EnemyConfig(**enemy_config_data)
    await db.add_enemy_config(config)

    # 获取所有敌人配置
    response = client.get("/api/enemy-configs/")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0


@pytest.mark.asyncio
async def test_update_enemy_config(enemy_config_data):
    # 首先创建一个配置
    db = await get_enemy_db()
    await db.delete_enemy_config("test_enemy_config")
    config = EnemyConfig(**enemy_config_data)
    await db.add_enemy_config(config)

    # 更新敌人配置
    update_data = enemy_config_data.copy()
    update_data["enemy_index"] = 2
    response = client.put("/api/enemy-configs/test_enemy_config", json=update_data)
    assert response.status_code == 200
    data = response.json()
    assert data["enemy_index"] == 2


@pytest.mark.asyncio
async def test_delete_enemy_config(enemy_config_data):
    # 首先创建一个配置
    db = await get_enemy_db()
    await db.delete_enemy_config("test_enemy_config")
    config = EnemyConfig(**enemy_config_data)
    await db.add_enemy_config(config)

    # 删除敌人配置
    response = client.delete("/api/enemy-configs/test_enemy_config")
    assert response.status_code == 204

    # 验证配置已被删除
    response = client.get("/api/enemy-configs/test_enemy_config")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_enemies():
    response = client.get("/api/enemies/")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0


@pytest.mark.asyncio
async def test_get_enemy_info():
    response = client.get("/api/enemies/enemy1/info")
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert "name" in data
    assert "level" in data
    assert "element" in data
    assert "description" in data
