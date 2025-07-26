"""
APL API 测试
测试APL相关API端点和数据模型
"""

import pytest
from zsim.api_src.models.apl import (
    APLCharacterConfig,
    APLCharactersInfo,
    APLLogicInfo,
    APLConfigCreateRequest,
    APLConfigUpdateRequest,
)


def test_apl_character_config_cinema_as_list():
    """测试APL角色配置中cinema字段作为列表的处理"""
    # 测试有效的cinema列表
    config = APLCharacterConfig(cinema=[0, 1, 2], weapon="TestWeapon", equip_set4="TestSet")
    assert config.cinema == [0, 1, 2]
    assert config.weapon == "TestWeapon"
    assert config.equip_set4 == "TestSet"

    # 测试空的cinema列表
    config = APLCharacterConfig(cinema=[], weapon="TestWeapon")
    assert config.cinema == []
    assert config.weapon == "TestWeapon"

    # 测试None值
    config = APLCharacterConfig(cinema=None, weapon="TestWeapon")
    assert config.cinema is None
    assert config.weapon == "TestWeapon"


def test_apl_characters_info_dynamic_fields():
    """测试APL角色信息模型的动态字段支持"""
    characters_info = APLCharactersInfo(
        required=["Character1", "Character2"],
        optional=["Character3"],
        Character1={"cinema": [0, 1], "weapon": "Weapon1"},
        Character2={"cinema": [2, 3], "weapon": "Weapon2"},
        Character3={"cinema": [4], "weapon": "Weapon3"},
    )

    assert characters_info.required == ["Character1", "Character2"]
    assert characters_info.optional == ["Character3"]
    # 验证动态字段被正确存储
    assert hasattr(characters_info, "Character1")
    assert hasattr(characters_info, "Character2")
    assert hasattr(characters_info, "Character3")


def test_apl_config_create_request():
    """测试APL配置创建请求模型"""
    # 创建完整的APL配置请求
    characters = APLCharactersInfo(
        required=["Character1"],
        optional=[],
        Character1={"cinema": [0, 1, 2], "weapon": "TestWeapon"},
    )

    apl_logic = APLLogicInfo(logic="# Test APL logic\n1|action+=|1_S1|condition==True")

    request = APLConfigCreateRequest(
        title="Test APL Config",
        comment="Test comment",
        author="Test Author",
        characters=characters,
        apl_logic=apl_logic,
    )

    assert request.title == "Test APL Config"
    assert request.comment == "Test comment"
    assert request.author == "Test Author"
    assert request.characters.required == ["Character1"]
    assert request.characters.Character1["cinema"] == [0, 1, 2]
    assert request.apl_logic.logic == "# Test APL logic\n1|action+=|1_S1|condition==True"


def test_apl_config_update_request():
    """测试APL配置更新请求模型"""
    # 创建APL配置更新请求
    characters = APLCharactersInfo(required=["Character1", "Character2"], optional=["Character3"])

    apl_logic = APLLogicInfo(logic="# Updated APL logic\n2|action+=|2_S1|condition==False")

    request = APLConfigUpdateRequest(
        title="Updated APL Config",
        comment="Updated comment",
        characters=characters,
        apl_logic=apl_logic,
    )

    assert request.title == "Updated APL Config"
    assert request.comment == "Updated comment"
    assert request.characters.required == ["Character1", "Character2"]
    assert request.characters.optional == ["Character3"]
    assert request.apl_logic.logic == "# Updated APL logic\n2|action+=|2_S1|condition==False"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
