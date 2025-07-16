"""
单个会话的启动配置参数

SessionCreate 的初始化json样例:
{
    "stop_tick": 3600,
    "mode": "parallel",
    "common_config": {
        "char_config": [
            {
                "name": "角色名",
                "CID": 1,
                "weapon": "武器名",
                "weapon_level": 5,
                "equip_style": "4+2",
                "equip_set4": "套装4",
                "equip_set2_a": "套装2a",
                "drive4": "驱动4",
                "drive5": "驱动5",
                "drive6": "驱动6",
                "scATK_percent": 10,
                "scCRIT": 10,
                "scCRIT_DMG": 10
            }, ..., ...,
            需要至少三个角色
        ],
        "enemy_config": {
            "index_id": 1,
            "adjustment_id": "s",
            "difficulty": 8.74
        },
        "apl_path": "path/to/apl.txt"
    },
    "parallel_config": {
        "enable": true,
        "func": "attr_curve",        # 可选值功能，后续会拓展
        "func_config": {             # 根据 func 的值，自动将 func_config 字典转换为正确的模型实例
            "sc_range": [0, 40],
            "sc_list": ["scATK_percent", "scCRIT", "scCRIT_DMG"],
            "remove_equip_list": []
        }
    }
}
"""

from typing import Any, Literal

from pydantic import (
    BaseModel,
    Field,
    NonNegativeFloat,
    NonNegativeInt,
    ValidationError,
    model_validator,
)


class CharConfig(BaseModel):
    """角色配置参数"""

    name: str | None = None
    CID: int | None = None
    weapon: str | None = None
    weapon_level: Literal[1, 2, 3, 4, 5] = 1
    equip_style: Literal["4+2", "2+2+2"] = "4+2"
    equip_set4: str | None = None
    equip_set2_a: str | None = None
    equip_set2_b: str | None = None
    equip_set2_c: str | None = None
    drive4: str | None = None
    drive5: str | None = None
    drive6: str | None = None
    scATK_percent: NonNegativeInt = 0
    scATK: NonNegativeInt = 0
    scHP_percent: NonNegativeInt = 0
    scHP: NonNegativeInt = 0
    scDEF_percent: NonNegativeInt = 0
    scDEF: NonNegativeInt = 0
    scAnomalyProficiency: NonNegativeInt = 0
    scPEN: NonNegativeInt = 0
    scCRIT: NonNegativeInt = 0
    scCRIT_DMG: NonNegativeInt = 0
    sp_limit: NonNegativeInt | NonNegativeFloat = 120
    cinema: NonNegativeInt = 0
    crit_balancing: bool = True
    crit_rate_limit: NonNegativeFloat = 0.95

    @model_validator(mode="after")
    def validate_stats(self) -> "CharConfig":
        """验证属性值是否合法"""
        # name和CID不能同时为空
        if self.name is None and self.CID is None:
            raise ValidationError("name和CID不能同时为空")
        # 验证暴击率上限
        if not 0.05 <= self.crit_rate_limit <= 1:
            raise ValidationError("暴击率上限必须在0.05到1之间")
        return self


class EnemyConfig(BaseModel):
    """敌人配置参数"""

    index_id: int
    adjustment_id: int | str
    difficulty: int | float = 8.74


class SimulationConfig(BaseModel):
    """模拟配置参数"""

    # all mode common:
    stop_tick: int | None = Field(None, description="指定模拟的tick数量")
    mode: Literal["normal", "parallel"] | None = Field(None, description="运行模式")
    func: Literal["attr_curve", "weapon"] | None = Field(None, description="功能选择")
    adjust_char: Literal[1, 2, 3] | None = Field(None, description="调整的角色相对位置")
    run_turn_uuid: str | None = Field(None, description="本轮次并行运行的uuid")


class ExecAttrCurveCfg(SimulationConfig):
    """调整副词条配置参数"""

    func: Literal["attr_curve", "weapon"] | None = "attr_curve"
    sc_name: str
    sc_value: int
    remove_equip: bool = False


class ExecWeaponCfg(SimulationConfig):
    """调整武器配置参数"""

    func: Literal["attr_curve", "weapon"] | None = "weapon"
    weapon_name: str
    weapon_level: Literal[1, 2, 3, 4, 5]


class CommonCfg(BaseModel):
    """通用配置参数"""

    char_config: list[CharConfig] = []
    enemy_config: EnemyConfig
    apl_path: str = ""

    @model_validator(mode="after")
    def validate_char_config(self) -> "CommonCfg":
        """验证角色配置参数"""
        # 角色配置参数不能为空
        if len(self.char_config) != 3:
            raise ValidationError("角色配置参数必须为3个")
        return self


class ParallelCfg(BaseModel):
    enable: bool = False
    func: Literal["attr_curve", "weapon"] | None = None
    func_config: "AttrCurveConfig | WeaponConfig | None" = None

    class AttrCurveConfig(BaseModel):
        """调整属性曲线配置参数"""

        sc_range: tuple[int, int] = (0, 40)
        sc_list: list[str]
        remove_equip_list: list[str] = []

    class WeaponConfig(BaseModel):
        """调整武器配置参数"""

        weapon_list: list[str] = []
        weapon_levels: list[Literal[1, 2, 3, 4, 5]] = [1, 5]

    @model_validator(mode="before")
    @classmethod
    def _check_func_config_type(cls, data: Any) -> Any:
        """根据 func 的值，自动将 func_config 字典转换为正确的模型实例"""
        if not isinstance(data, dict):
            return data

        func = data.get("func")
        func_config = data.get("func_config")

        # 如果 func 为 None，func_config 必须也为 None
        if func is None:
            if func_config is not None:
                raise ValidationError("当 func 为 None 时，func_config 必须为 None")
            return data

        # 如果 func_config 为 None，但 func 不为 None，报错
        if func_config is None:
            raise ValidationError(f"当 func 为 '{func}' 时，func_config 不能为 None")

        # 根据 func 的值检查 func_config 的类型并转换
        if func == "attr_curve":
            if not isinstance(func_config, cls.AttrCurveConfig):
                data["func_config"] = cls.AttrCurveConfig(**func_config)
        elif func == "weapon":
            if not isinstance(func_config, cls.WeaponConfig):
                data["func_config"] = cls.WeaponConfig(**func_config)

        return data


class SessionRun(BaseModel):
    """模拟器会话配置参数，启动会话的全部数据"""

    # all mode common:
    stop_tick: int | None = Field(None, description="指定模拟的tick数量")
    mode: Literal["normal", "parallel"] | None = Field(None, description="运行模式")
    common_config: CommonCfg
    parallel_config: ParallelCfg | None = None

    @model_validator(mode="after")
    def validate_common_config(self) -> "SessionRun":
        """验证通用配置参数"""
        if self.mode == "parallel" and self.parallel_config is None:
            raise ValidationError("并行模式下，parallel_config 不能为空")
        return self


if __name__ == "__main__":
    config = ParallelCfg(
        enable=True,
        func="attr_curve",
        func_config={
            "sc_range": (0, 40),
            "sc_list": ["scATK", "scDEF"],
            "remove_equip_list": [],
        },  # type: ignore
    )
    print(config)
    try:
        session_config = SessionRun(
            stop_tick=1000,
            mode="parallel",
            common_config={
                "char_config": [{"name": ""}, {"name": ""}, {"name": ""}],
                "enemy_config": {"index_id": 1, "adjustment_idx": "s"},
                "apl_path": "",
            },  # type: ignore
            parallel_config=config,
        )
        print(session_config.model_dump_json(indent=4))
    except ValidationError as e:
        print(e)
    try:
        session_config = SessionRun(
            **{
                "stop_tick": 3600,
                "mode": "parallel",
                "common_config": {
                    "char_config": [
                        {"name": "角色名", "CID": 1},
                        {"name": "角色名", "CID": 2},
                        {"name": "角色名", "CID": 3},
                    ],
                    "enemy_config": {
                        "index_id": 1,
                        "adjustment_idx": "s",
                        "difficulty": 8.74,
                    },
                    "apl_path": "path/to/apl.txt",
                },
                "parallel_config": {
                    "enable": "true",
                    "func": "attr_curve",  # 可选值功能，后续会拓展
                    "func_config": {  # 根据 func 的值，自动将 func_config 字典转换为正确的模型实例
                        "sc_range": [0, 40],
                        "sc_list": ["scATK_percent", "scCRIT", "scCRIT_DMG"],
                        "remove_equip_list": [],
                    },
                },
            }
        )
    except ValidationError as e:
        print(e)
