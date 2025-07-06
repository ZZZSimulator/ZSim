from typing import Literal
from pydantic import BaseModel, Field


class SimulationConfig(BaseModel):
    """模拟配置参数"""

    # all mode common:
    stop_tick: int | None = Field(None, description="指定模拟的tick数量")
    mode: Literal["normal", "parallel"] | None = Field(None, description="运行模式")
    func: Literal["attr_curve", "weapon"] | None = Field(None, description="功能选择")
    adjust_char: Literal[1, 2, 3] | None = Field(None, description="调整的角色相对位置")
    run_turn_uuid: str | None = Field(None, description="本轮次并行运行的uuid")


class AttrCurveConfig(SimulationConfig):
    """调整副词条配置参数"""

    func: Literal["attr_curve"] = "attr_curve"
    sc_name: str
    sc_value: int
    remove_equip: bool = False


class WeaponConfig(SimulationConfig):
    """调整武器配置参数"""

    func: Literal["weapon"] = "weapon"
    weapon_name: str
    weapon_level: Literal[1, 2, 3, 4, 5]


if __name__ == "__main__":
    a = WeaponConfig()
