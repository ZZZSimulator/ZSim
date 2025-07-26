import pytest
from fastapi.testclient import TestClient
from zsim.api import app
from zsim.api_src.services.database.character_db import get_character_db, CharacterDB
from zsim.models.character.character_config import CharacterConfig
import asyncio

client = TestClient(app)


@pytest.fixture
def character_config_data():
    return {
        "config_id": "Hugo_test_config",
        "config_name": "test_config",
        "name": "Hugo",
        "weapon": "音擎A",
        "weapon_level": 5,
        "cinema": 6,
        "crit_balancing": True,
        "crit_rate_limit": 0.95,
        "scATK_percent": 10,
        "scATK": 20,
        "scHP_percent": 30,
        "scHP": 40,
        "scDEF_percent": 50,
        "scDEF": 60,
        "scAnomalyProficiency": 70,
        "scPEN": 80,
        "scCRIT": 90,
        "scCRIT_DMG": 100,
        "drive4": "攻击力%",
        "drive5": "暴击率",
        "drive6": "暴击伤害",
        "equip_style": "4+2",
        "equip_set4": "套装A",
    }


@pytest.mark.asyncio
async def test_create_character_config(character_config_data):
    # 清理之前的测试数据
    db = await get_character_db()
    await db.delete_character_config("Hugo", "test_config")

    # 创建角色配置
    response = client.post("/api/characters/Hugo/configs", json=character_config_data)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Hugo"
    assert data["config_name"] == "test_config"
    assert "config_id" in data
    assert "create_time" in data
    assert "update_time" in data


@pytest.mark.asyncio
async def test_get_character_config(character_config_data):
    # 首先创建一个配置
    db = await get_character_db()
    await db.delete_character_config("Hugo", "test_config")
    config = CharacterConfig(**character_config_data)
    await db.add_character_config(config)

    # 获取角色配置
    response = client.get("/api/characters/Hugo/configs/test_config")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Hugo"
    assert data["config_name"] == "test_config"


@pytest.mark.asyncio
async def test_list_character_configs(character_config_data):
    # 首先创建一个配置
    db = await get_character_db()
    await db.delete_character_config("Hugo", "test_config")
    config = CharacterConfig(**character_config_data)
    await db.add_character_config(config)

    # 获取角色的所有配置
    response = client.get("/api/characters/Hugo/configs")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0


@pytest.mark.asyncio
async def test_update_character_config(character_config_data):
    # 首先创建一个配置
    db = await get_character_db()
    await db.delete_character_config("Hugo", "test_config")
    config = CharacterConfig(**character_config_data)
    await db.add_character_config(config)

    # 更新角色配置
    update_data = character_config_data.copy()
    update_data["weapon_level"] = 3
    response = client.put("/api/characters/Hugo/configs/test_config", json=update_data)
    assert response.status_code == 200
    data = response.json()
    assert data["weapon_level"] == 3


@pytest.mark.asyncio
async def test_delete_character_config(character_config_data):
    # 首先创建一个配置
    db = await get_character_db()
    await db.delete_character_config("Hugo", "test_config")
    config = CharacterConfig(**character_config_data)
    await db.add_character_config(config)

    # 删除角色配置
    response = client.delete("/api/characters/Hugo/configs/test_config")
    assert response.status_code == 204

    # 验证配置已被删除
    response = client.get("/api/characters/Hugo/configs/test_config")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_characters():
    response = client.get("/api/characters/")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0


@pytest.mark.asyncio
async def test_get_character_info():
    response = client.get("/api/characters/安比/info")
    assert response.status_code == 200
    data = response.json()
    assert "name" in data
    assert "element" in data
    assert "weapon_type" in data
    assert "rarity" in data
    assert "base_hp" in data
