from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class CharacterConfig(BaseModel):
    """角色配置数据模型"""

    config_id: str = Field(description="角色配置ID，格式为 {name}_{config_name}")
    name: str = Field(description="角色名称")
    config_name: str = Field(description="配置名称")
    weapon: str
    weapon_level: int
    cinema: int
    crit_balancing: bool
    crit_rate_limit: float
    scATK_percent: int
    scATK: int
    scHP_percent: int
    scHP: int
    scDEF_percent: int
    scDEF: int
    scAnomalyProficiency: int
    scPEN: int
    scCRIT: int
    scCRIT_DMG: int
    drive4: str
    drive5: str
    drive6: str
    equip_style: str
    equip_set4: Optional[str] = None
    equip_set2_a: Optional[str] = None
    equip_set2_b: Optional[str] = None
    equip_set2_c: Optional[str] = None
    create_time: datetime = Field(default_factory=datetime.now, description="配置创建时间")
    update_time: datetime = Field(default_factory=datetime.now, description="配置更新时间")
