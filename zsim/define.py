import json
import shutil
from pathlib import Path
from typing import Callable, Literal

import toml

# 属性类型：
ElementType = Literal[0, 1, 2, 3, 4, 5, 6]
Number = int | float

INVALID_ELEMENT_ERROR = "Invalid element type"
NORMAL_MODE_ID_JSON = "results/id_cache.json"


def initialize_config_files():
    """
    初始化配置文件。
    如果配置文件不存在，则从 _example 文件复制生成。
    如果存在，则检查并使用模板更新现有配置。
    """
    # TOML config
    char_config_example_path = Path("zsim/data/character_config_example.toml")
    if not char_config_file.exists():
        shutil.copy(char_config_example_path, char_config_file)
        print(f"已生成配置文件：{char_config_file}")

    # JSON config
    config_example_path = Path("zsim/config_example.json")

    def update_json_config(template: dict, user: dict) -> bool:
        """递归更新用户配置，返回是否被更新"""
        updated = False
        for key, value in template.items():
            if key not in user:
                user[key] = value
                updated = True
            elif isinstance(value, dict) and isinstance(user.get(key), dict):
                if update_json_config(value, user[key]):
                    updated = True
        return updated

    if not Path(CONFIG_PATH).exists():
        shutil.copy(config_example_path, CONFIG_PATH)
        print(f"已生成配置文件：{CONFIG_PATH}")
    else:
        with open(config_example_path, "r", encoding="utf-8") as f:
            template_config = json.load(f)
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            user_config = json.load(f)

        if update_json_config(template_config, user_config):
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(user_config, f, indent=4, ensure_ascii=False)
            print(f"配置文件 {CONFIG_PATH} 已更新。")


results_dir = "results/"

# 加载角色配置
CONFIG_PATH = "zsim/config.json"
data_dir = Path("./zsim/data")
data_dir.mkdir(exist_ok=True)
char_config_file = data_dir / "character_config.toml"
saved_char_config = {}
initialize_config_files()
if char_config_file.exists():
    with open(char_config_file, "r", encoding="utf-8") as f:
        saved_char_config = toml.load(f)
else:
    raise FileNotFoundError(f"Character config file {char_config_file} not found.")


_config = json.load(open(CONFIG_PATH, encoding="utf-8-sig"))

# 敌人配置
ENEMY_INDEX_ID: int = _config["enemy"]["index_ID"]
ENEMY_ADJUST_ID: int = _config["enemy"]["adjust_ID"]
ENEMY_DIFFICULTY: float = _config["enemy"]["difficulty"]

# APL模式配置
APL_MODE: bool = _config["apl_mode"]["enabled"]
SWAP_CANCEL: bool = _config["swap_cancel_mode"]["enabled"]
APL_PATH: str = _config["database"]["APL_FILE_PATH"]
APL_NA_ORDER_PATH: str = _config["apl_mode"]["na_order"]
ENEMY_RANDOM_ATTACK: bool = _config["apl_mode"]["enemy_random_attack"]
ENEMY_REGULAR_ATTACK: bool = _config["apl_mode"]["enemy_regular_attack"]
if ENEMY_RANDOM_ATTACK and ENEMY_REGULAR_ATTACK:
    raise ValueError("不能同时开启“敌人随机进攻”与“敌人规律进攻”参数。")
ENEMY_ATTACK_RESPONSE: bool = _config["apl_mode"]["enemy_attack_response"]
ENEMY_ATTACK_METHOD_CONFIG: str = _config["apl_mode"]["enemy_attack_method_config"]
ENEMY_ATTACK_ACTION: str = _config["apl_mode"]["enemy_attack_action_data"]
ENEMY_ATTACK_REPORT: bool = _config["apl_mode"]["enemy_attack_report"]

ENEMY_ATK_PARAMETER_DICT: dict[str, int | float] = {
    "Taction": 30,  # 角色弹刀与闪避动作的持续时间，不开放给用户更改。
    "Tbase": 273,  # 人类反应时间大数据中位数，单位ms，不可更改！
    "PlayerLevel": _config["apl_mode"]["player_level"],  # 玩家水平系数，由用户自己填写。
    "theta": 90,  # θ，人类胜利最小反应时间（神经传导极限），为90ms，不可更改！
    "c": 0.5,  # 波动调节系数，暂取0.5，不开放给用户更改。
    "delta": 30,  # 玩家水平系数所导致的中位数波动单位，暂时取30ms，不开放给用户更改。
}
PARRY_BASE_PARAMETERS: dict[str, int | float] = {
    "ChainParryActionTimeCost": 10,  # 连续招架动作的时间消耗
}


DEFAULT_APL_DIR: str = _config["apl_mode"]["default_apl_dir"]
COSTOM_APL_DIR: str = _config["apl_mode"]["custom_apl_dir"]
YANAGI_NA_ORDER: str = _config["apl_mode"]["Yanagi"]
HUGO_NA_ORDER: str = _config["apl_mode"]["Hugo"]
HUGO_NA_MODE_LEVEL: int = _config["na_mode_level"]["Hugo"]

#: 合轴操作完成度系数->根据前一个技能帧数的某个比例来延后合轴
SWAP_CANCEL_MODE_COMPLETION_COEFFICIENT: float = _config["swap_cancel_mode"][
    "completion_coefficient"
]

#: 操作滞后系数->合轴操作延后的另一种迟滞方案，即固定值延后。
SWAP_CANCEL_MODE_LAG_TIME: float = _config["swap_cancel_mode"]["lag_time"]
SWAP_CANCEL_MODE_DEBUG: bool = _config["swap_cancel_mode"]["debug"]
SWAP_CANCEL_DEBUG_TARGET_SKILL: str = _config["swap_cancel_mode"]["debug_target_skill"]

# 数据库配置
SQLITE_PATH: str = _config["database"]["SQLITE_PATH"]
CHARACTER_DATA_PATH: str = _config["database"]["CHARACTER_DATA_PATH"]
WEAPON_DATA_PATH: str = _config["database"]["WEAPON_DATA_PATH"]
EQUIP_2PC_DATA_PATH: str = _config["database"]["EQUIP_2PC_DATA_PATH"]
SKILL_DATA_PATH: str = _config["database"]["SKILL_DATA_PATH"]
ENEMY_DATA_PATH: str = _config["database"]["ENEMY_DATA_PATH"]
ENEMY_ADJUSTMENT_PATH: str = _config["database"]["ENEMY_ADJUSTMENT_PATH"]
DEFAULT_SKILL_PATH: str = _config["database"]["DEFAULT_SKILL_PATH"]
CHARACTER_IMAGE_PATH: str = _config["database"]["CHARACTER_IMAGE_PATH"]
STAR_IMAGE_PATH: str = _config["database"]["STAR_IMAGE_PATH"]
CRIT_BALANCING: bool = _config["character"]["crit_balancing"]
BACK_ATTACK_RATE: bool = _config["character"]["back_attack_rate"]
# FIXME：背击暂时用几率控制。
DEBUG: bool = _config["debug"]["enabled"]
DEBUG_LEVEL: int = _config["debug"]["level"]
JUDGE_FILE_PATH: str = _config["database"]["JUDGE_FILE_PATH"]
EFFECT_FILE_PATH: str = _config["database"]["EFFECT_FILE_PATH"]
EXIST_FILE_PATH: str = _config["database"]["EXIST_FILE_PATH"]
BUFF_LOADING_CONDITION_TRANSLATION_DICT: dict = _config["translate"]
ENABLE_WATCHDOG: bool = _config["watchdog"]["enabled"]
WATCHDOG_LEVEL: int = _config["watchdog"]["level"]
INPUT_ACTION_LIST = ""  # 半废弃

# 初始化Buff的报告：
BUFF_0_REPORT: bool = _config["buff_0_report"]["enabled"]
# 角色特殊机制报告：
VIVIAN_REPORT: bool = _config["char_report"]["Vivian"]
ASTRAYAO_REPORT: bool = _config["char_report"]["AstraYao"]
HUGO_REPORT: bool = _config["char_report"]["Hugo"]
YIXUAN_REPORT: bool = _config["char_report"]["Yixuan"]
TRIGGER_REPORT: bool = _config["char_report"]["Trigger"]
YUZUHA_REPORT: bool = _config["char_report"]["Yuzuha"]

# 开发变量
NEW_SIM_BOOT: bool = _config.get("dev", {}).get("new_sim_boot", True)

compare_methods_mapping: dict[str, Callable[[float | int, float | int], bool]] = {
    "<": lambda a, b: a < b,
    "<=": lambda a, b: a <= b,
    ">": lambda a, b: a > b,
    ">=": lambda a, b: a >= b,
    "==": lambda a, b: a == b,
    "!=": lambda a, b: a != b,
}
ANOMALY_MAPPING: dict[ElementType, str] = {
    0: "强击",
    1: "灼烧",
    2: "碎冰",
    3: "感电",
    4: "侵蚀",
    5: "烈霜碎冰",
    6: "玄墨侵蚀",
}

ELEMENT_TYPE_MAPPING: dict[ElementType, str] = {
    0: "物理",
    1: "火",
    2: "冰",
    3: "电",
    4: "以太",
    5: "烈霜",
    6: "玄墨"
}
# 属性类型等价映射字典
ELEMENT_EQUIVALENCE_MAP: dict[ElementType, list[ElementType]] = {
    0: [0],
    1: [1],
    2: [2, 5],  # 烈霜也能享受到冰属性加成
    3: [3],
    4: [4, 6],  # 玄墨也能享受到以太属性加成
    5: [5],
    6: [6],
}

SUB_STATS_MAPPING: dict[
    Literal[
        "scATK_percent",
        "scATK",
        "scHP_percent",
        "scHP",
        "scDEF_percent",
        "scDEF",
        "scAnomalyProficiency",
        "scPEN",
        "scCRIT",
        "scCRIT_DMG",
        "DMG_BONUS",
        "PEN_RATIO",
        "ANOMALY_MASTERY",
        "SP_REGEN",
    ],
    Number,
] = {
    "scATK_percent": 0.03,
    "scATK": 19,
    "scHP_percent": 0.03,
    "scHP": 112,
    "scDEF_percent": 0.048,
    "scDEF": 15,
    "scAnomalyProficiency": 9,
    "scPEN": 9,
    "scCRIT": 0.024,
    "scCRIT_DMG": 0.048,
    "DMG_BONUS": 0.03,
    "PEN_RATIO": 0.024,
    "ANOMALY_MASTERY": 0.03,
    "SP_REGEN": 0.06,
}

DOCS_DIR = "docs"

# Version Check
GITHUB_REPO_OWNER = "ZZZSimulator"
GITHUB_REPO_NAME = "ZSim"

with open("pyproject.toml", "r", encoding="utf-8") as f:
    pyproject_config = toml.load(f)
    # 获取当前版本号
    __version__ = pyproject_config.get("project", {}).get("version", "0.0.0")

if __name__ == "__main__":
    # 打印全部CONSTANT变量名
    def print_constant_names_and_values():
        # 获取当前全局命名空间
        global_vars = globals()
        # 筛选出所有全大写的变量名及其值
        constant_names_and_values = {
            name: value for name, value in global_vars.items() if name.isupper()
        }
        # 打印这些变量名及其值
        for name, value in constant_names_and_values.items():
            print(f"{name}: {value}")

    print_constant_names_and_values()
