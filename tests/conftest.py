import tempfile
import pytest
from pathlib import Path


@pytest.fixture
def temp_config_dir():
    """Create a temporary directory for test configuration files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def mock_character_config():
    """Create minimal mock character configuration for testing."""
    return {
        "艾莲": {
            "name": "艾莲",
            "weapon": "深海访客",
            "weapon_level": 1,
            "cinema": 0,
            "crit_balancing": False,
            "scATK_percent": 10,
            "scATK": 0,
            "scHP_percent": 0,
            "scHP": 0,
            "scDEF_percent": 0,
            "scDEF": 0,
            "scAnomalyProficiency": 0,
            "scPEN": 0,
            "scCRIT": 10,
            "scCRIT_DMG": 10,
            "drive4": "攻击力%",
            "drive5": "冰属性伤害%",
            "drive6": "攻击力%",
            "equip_style": "4+2",
            "equip_set4": "啄木鸟电音",
            "equip_set2_a": "极地重金属",
        },
        "苍角": {
            "name": "苍角",
            "weapon": "含羞恶面",
            "weapon_level": 5,
            "cinema": 2,
            "crit_balancing": False,
            "scATK_percent": 20,
            "scATK": 0,
            "scHP_percent": 0,
            "scHP": 0,
            "scDEF_percent": 0,
            "scDEF": 0,
            "scAnomalyProficiency": 0,
            "scPEN": 0,
            "scCRIT": 0,
            "scCRIT_DMG": 0,
            "drive4": "攻击力%",
            "drive5": "攻击力%",
            "drive6": "攻击力%",
            "equip_style": "4+2",
            "equip_set4": "自由蓝调",
            "equip_set2_a": "灵魂摇滚",
        },
    }


@pytest.fixture
def mock_simulation_config():
    """Create minimal mock simulation configuration for testing."""
    return {
        "debug": {"enabled": False, "level": 4},
        "stop_tick": 1000,
        "watchdog": {"enabled": False, "level": 4},
        "character": {"crit_balancing": True, "back_attack_rate": 1},
        "enemy": {"index_ID": 11412, "adjust_ID": 22412, "difficulty": 8.74},
        "apl_mode": {
            "enabled": True,
            "na_order": "./zsim/data/DefaultConfig/NAOrder.json",
            "enemy_random_attack": False,
            "enemy_regular_attack": False,
            "enemy_attack_response": False,
            "enemy_attack_method_config": "./zsim/data/enemy_attack_method.csv",
            "enemy_attack_action_data": "./zsim/data/enemy_attack_action.csv",
            "enemy_attack_report": False,
            "player_level": 5,
            "default_apl_dir": "./zsim/data/APLData",
            "custom_apl_dir": "./zsim/data/APLData/custom",
        },
        "swap_cancel_mode": {
            "enabled": True,
            "completion_coefficient": 0.3,
            "lag_time": 20,
            "debug": False,
        },
        "database": {
            "SQLITE_PATH": "./zsim/data/zsim.db",
            "CHARACTER_DATA_PATH": "./zsim/data/character.csv",
            "WEAPON_DATA_PATH": "./zsim/data/weapon.csv",
            "EQUIP_2PC_DATA_PATH": "./zsim/data/equip_set_2pc.csv",
            "SKILL_DATA_PATH": "./zsim/data/skill.csv",
            "ENEMY_DATA_PATH": "./zsim/data/enemy.csv",
            "ENEMY_ADJUSTMENT_PATH": "./zsim/data/enemy_adjustment.csv",
            "DEFAULT_SKILL_PATH": "./zsim/data/default_skill.csv",
            "JUDGE_FILE_PATH": "./zsim/data/触发判断.csv",
            "EFFECT_FILE_PATH": "./zsim/data/buff_effect.csv",
            "EXIST_FILE_PATH": "./zsim/data/激活判断.csv",
            "APL_FILE_PATH": "./zsim/data/APLData/薇薇安-柳-耀嘉音.toml",
        },
        "buff_0_report": {"enabled": False},
        "char_report": {
            "Vivian": False,
            "AstraYao": False,
            "Hugo": False,
            "Yixuan": False,
            "Trigger": False,
            "Yuzuha": False,
        },
        "parallel_mode": {"enabled": False, "adjust_char": 1},
        "dev": {"new_sim_boot": True},
    }
