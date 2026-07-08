import json
import shutil
import sys
import tomllib
from pathlib import Path
from typing import Any, Callable, ClassVar, Literal, cast

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_pascal
from pydantic_settings import (
    BaseSettings,
    JsonConfigSettingsSource,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)

# 属性类型：
ElementType = Literal[0, 1, 2, 3, 4, 5, 6]
Number = int | float

INVALID_ELEMENT_ERROR = "无效的元素类型"
NORMAL_MODE_ID_JSON = "results/id_cache.json"


results_dir = "results/"


data_dir = Path("./zsim/data")
config_path = Path("./zsim/config.json")


class DebugConfig(BaseModel):
    enabled: bool = True
    level: int = 4
    check_skill_mul: bool = False
    check_skill_mul_tag: list[str] = []


class WatchdogConfig(BaseModel):
    enabled: bool = False
    level: int = 4


class CharacterConfig(BaseModel):
    crit_balancing: bool = True
    back_attack_rate: float = 1.0


class EnemyConfig(BaseModel):
    index_id: int
    adjust_id: int
    difficulty: float

    model_config = ConfigDict(alias_generator=lambda x: x.replace("id", "ID"))


class AplModeConfig(BaseModel):
    enabled: bool = True
    na_order: str
    enemy_random_attack: bool = False
    enemy_regular_attack: bool = False
    enemy_attack_response: bool = False
    enemy_attack_method_config: str
    enemy_attack_action_data: str
    enemy_attack_report: bool = True
    player_level: int = 5
    default_apl_dir: str
    custom_apl_dir: str
    yanagi: str
    hugo: str
    alice: str
    seed: str
    perfect_player: bool = True
    apl_thought_check: bool = False
    apl_thought_check_window: list[int] = [0, 1]

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_pascal)


class SwapCancelModeConfig(BaseModel):
    enabled: bool = True
    completion_coefficient: float
    lag_time: float
    debug: bool = False
    debug_target_skill: str


class DatabaseConfig(BaseModel):
    sqlite_path: str
    character_data_path: str
    weapon_data_path: str
    equip_2pc_data_path: str
    skill_data_path: str
    enemy_data_path: str
    enemy_adjustment_path: str
    default_skill_path: str
    judge_file_path: str
    effect_file_path: str
    exist_file_path: str
    apl_file_path: str

    model_config = ConfigDict(populate_by_name=True, alias_generator=str.upper)


class Buff0ReportConfig(BaseModel):
    enabled: bool = False


class CharReportConfig(BaseModel):
    vivian: bool
    astra_yao: bool
    hugo: bool
    yixuan: bool
    trigger: bool
    jufufu: bool
    yuzuha: bool
    alice: bool
    seed: bool

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_pascal)


class NaModeLevelConfig(BaseModel):
    hugo: int

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_pascal)


class DevConfig(BaseModel):
    new_sim_boot: bool = True


class BuffRuntimeConfig(BaseModel):
    mode: str = "owner_only"


class Config(BaseSettings):
    model_config: ClassVar[SettingsConfigDict] = SettingsConfigDict(
        json_file=config_path,
        json_file_encoding="utf-8",
        env_file=".env",
        env_ignore_empty=True,
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        env_prefix="ZSIM_",
        populate_by_name=True,
    )
    debug: DebugConfig
    stop_tick: int = 10800
    watchdog: WatchdogConfig
    character: CharacterConfig
    enemy: EnemyConfig
    apl_mode: AplModeConfig
    swap_cancel_mode: SwapCancelModeConfig
    database: DatabaseConfig
    translate: dict[str, str] = {}
    buff_0_report: Buff0ReportConfig
    char_report: CharReportConfig
    na_mode_level: NaModeLevelConfig
    parallel_mode: dict[str, Any] = {}
    dev: DevConfig = DevConfig()
    buff_runtime: BuffRuntimeConfig = BuffRuntimeConfig()

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (
            init_settings,
            JsonConfigSettingsSource(settings_cls),
            env_settings,
            dotenv_settings,
            file_secret_settings,
        )


# 确保数据目录存在
data_dir.mkdir(exist_ok=True, parents=True)
char_config_file = data_dir / "character_config.toml"
saved_char_config = {}


# 修复：将char_config_file作为参数传递给initialize_config_files
def initialize_config_files_with_paths(char_file: Path, data_dir: Path, config_path: Path):
    """
    初始化配置文件。
    如果配置文件不存在，则从 _example 文件复制生成。
    如果存在，则检查并使用模板更新现有配置。
    """
    char_config_example_path = Path("zsim/data/character_config_example.toml")
    config_example_path = Path("zsim/config_example.json")

    # TOML 配置文件
    if not char_file.exists():
        shutil.copy(char_config_example_path, char_file)
        print(f"已生成配置文件：{char_file}")

    # JSON 配置文件
    def update_json_config(template: dict[str, Any], user: dict[str, Any]) -> bool:
        """递归更新用户配置，返回是否被更新"""
        updated = False
        for key, value in template.items():
            if key not in user:
                user[key] = value
                updated = True
            elif isinstance(value, dict) and isinstance(user.get(key), dict):
                if update_json_config(cast(dict[str, Any], value), user[key]):
                    updated = True
        return updated

    if not Path(config_path).exists():
        shutil.copy(config_example_path, config_path)
        print(f"已生成配置文件：{config_path}")
    else:
        with open(config_example_path, "r", encoding="utf-8") as f:
            template_config = json.load(f)
        with open(config_path, "r", encoding="utf-8") as f:
            user_config = json.load(f)

        if update_json_config(template_config, user_config):
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(user_config, f, indent=4, ensure_ascii=False)
            print(f"配置文件 {config_path} 已更新。")


# 使用新的函数
initialize_config_files_with_paths(char_config_file, data_dir, config_path)
if char_config_file.exists():
    with open(char_config_file, "rb") as f:
        saved_char_config = tomllib.load(f)
else:
    raise FileNotFoundError(f"未找到角色配置文件 {char_config_file}。")

# 确保配置文件目录存在
config_path.parent.mkdir(exist_ok=True, parents=True)
config = Config()  # type:ignore

# 敌人配置
ENEMY_INDEX_ID: int = config.enemy.index_id
ENEMY_ADJUST_ID: int = config.enemy.adjust_id
ENEMY_DIFFICULTY: float = config.enemy.difficulty

# APL模式配置
APL_MODE: bool = config.apl_mode.enabled
SWAP_CANCEL: bool = config.swap_cancel_mode.enabled
APL_PATH: str = config.database.apl_file_path
APL_NA_ORDER_PATH: str = config.apl_mode.na_order
ENEMY_RANDOM_ATTACK: bool = config.apl_mode.enemy_random_attack
ENEMY_REGULAR_ATTACK: bool = config.apl_mode.enemy_regular_attack
if ENEMY_RANDOM_ATTACK and ENEMY_REGULAR_ATTACK:
    raise ValueError("不能同时开启“敌人随机进攻”与“敌人规律进攻”参数。")
ENEMY_ATTACK_RESPONSE: bool = config.apl_mode.enemy_attack_response
ENEMY_ATTACK_METHOD_CONFIG: str = config.apl_mode.enemy_attack_method_config
ENEMY_ATTACK_ACTION: str = config.apl_mode.enemy_attack_action_data
ENEMY_ATTACK_REPORT: bool = config.apl_mode.enemy_attack_report

ENEMY_ATK_PARAMETER_DICT: dict[str, int | float | bool] = {
    "Taction": 30,  # 角色弹刀与闪避动作的持续时间，不开放给用户更改。
    "Tbase": 273,  # 人类反应时间大数据中位数，单位ms，不可更改！
    "PlayerLevel": config.apl_mode.player_level,  # 玩家水平系数，由用户自己填写。
    "PerfectPlayer": config.apl_mode.perfect_player,  # 是否是完美玩家（默认是）
    "theta": 90,  # θ，人类胜利最小反应时间（神经传导极限），为90ms，不可更改！
    "c": 0.5,  # 波动调节系数，暂取0.5，不开放给用户更改。
    "delta": 30,  # 玩家水平系数所导致的中位数波动单位，暂时取30ms，不开放给用户更改。
}
PARRY_BASE_PARAMETERS: dict[str, int | float] = {
    "ChainParryActionTimeCost": 10,  # 连续招架动作的时间消耗
}

# 招架策略，有些角色的拥有不同的突击支援（比如柚叶），所以在这里用字典进行映射。
# 该字典的key为CID，value为招架动作的skill_tag
# 注意，不同的招架策略有时候存在着影画或是其他的限制条件，
# 所以若是在不满足这些条件的情况下强行使用这些招架策略，那么character中的审查函数会报错而中断程序运行。
CHAR_PARRY_STRATEGY_MAP: dict[int, str] = {1411: "1411_Assault_Aid_A"}

# 调试参数，用于检查APL在窗口期间的想法
APL_THOUGHT_CHECK: bool = config.apl_mode.apl_thought_check
APL_THOUGHT_CHECK_WINDOW: list[int] = config.apl_mode.apl_thought_check_window


DEFAULT_APL_DIR: str = config.apl_mode.default_apl_dir
COSTOM_APL_DIR: str = config.apl_mode.custom_apl_dir
YANAGI_NA_ORDER: str = config.apl_mode.yanagi
HUGO_NA_ORDER: str = config.apl_mode.hugo
HUGO_NA_MODE_LEVEL: int = config.na_mode_level.hugo
ALICE_NA_ORDER: str = config.apl_mode.alice
SEED_NA_ORDER: str = config.apl_mode.seed

#: 合轴操作完成度系数->根据前一个技能帧数的某个比例来延后合轴
SWAP_CANCEL_MODE_COMPLETION_COEFFICIENT: float = config.swap_cancel_mode.completion_coefficient

#: 操作滞后系数->合轴操作延后的另一种迟滞方案，即固定值延后。
SWAP_CANCEL_MODE_LAG_TIME: float = config.swap_cancel_mode.lag_time
SWAP_CANCEL_MODE_DEBUG: bool = config.swap_cancel_mode.debug
SWAP_CANCEL_DEBUG_TARGET_SKILL: str = config.swap_cancel_mode.debug_target_skill

# 数据库配置
SQLITE_PATH: str = config.database.sqlite_path
CHARACTER_DATA_PATH: str = config.database.character_data_path
WEAPON_DATA_PATH: str = config.database.weapon_data_path
EQUIP_2PC_DATA_PATH: str = config.database.equip_2pc_data_path
SKILL_DATA_PATH: str = config.database.skill_data_path
ENEMY_DATA_PATH: str = config.database.enemy_data_path
ENEMY_ADJUSTMENT_PATH: str = config.database.enemy_adjustment_path
DEFAULT_SKILL_PATH: str = config.database.default_skill_path
CRIT_BALANCING: bool = config.character.crit_balancing
BACK_ATTACK_RATE: float = config.character.back_attack_rate
# FIXME：背击暂时用几率控制。
DEBUG: bool = config.debug.enabled
DEBUG_LEVEL: int = config.debug.level
JUDGE_FILE_PATH: str = config.database.judge_file_path
EFFECT_FILE_PATH: str = config.database.effect_file_path
EXIST_FILE_PATH: str = config.database.exist_file_path
BUFF_LOADING_CONDITION_TRANSLATION_DICT = config.translate
ENABLE_WATCHDOG: bool = config.watchdog.enabled
WATCHDOG_LEVEL: int = config.watchdog.level
INPUT_ACTION_LIST = ""  # 半废弃

# 初始化Buff的报告：
BUFF_0_REPORT: bool = config.buff_0_report.enabled
# 角色特殊机制报告：
VIVIAN_REPORT: bool = config.char_report.vivian
ASTRAYAO_REPORT: bool = config.char_report.astra_yao
HUGO_REPORT: bool = config.char_report.hugo
YIXUAN_REPORT: bool = config.char_report.yixuan
TRIGGER_REPORT: bool = config.char_report.trigger
YUZUHA_REPORT: bool = config.char_report.yuzuha
ALICE_REPORT: bool = config.char_report.alice
SEED_REPORT: bool = config.char_report.seed

# 伤害计算调试
CHECK_SKILL_MUL: bool = config.debug.check_skill_mul
CHECK_SKILL_MUL_TAG: list[str] = config.debug.check_skill_mul_tag

# 开发变量
NEW_SIM_BOOT: bool = config.dev.new_sim_boot

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
    6: "玄墨",
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

# 版本检查
GITHUB_REPO_OWNER = "ZZZSimulator"
GITHUB_REPO_NAME = "ZSim"

# 版本号处理
if getattr(sys, "frozen", False):
    # 打包环境：版本号由PyInstaller在打包时注入
    __version__ = "1.0.0"  # 默认值，打包时会被替换
else:
    # 开发环境：从 pyproject.toml 读取
    try:
        with open("pyproject.toml", "rb") as f:
            pyproject_config = tomllib.load(f)
            __version__ = pyproject_config.get("project", {}).get("version", "0.0.0")
    except FileNotFoundError:
        __version__ = "1.0.0"

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
    print(config.model_dump_json(indent=2, by_alias=True))
