from datetime import datetime
from typing import Dict, Any
from pydantic import BaseModel, Field


class EnemyConfig(BaseModel):
    """敌人配置数据模型"""

    config_id: str = Field(description="敌人配置ID")
    enemy_index: int
    enemy_adjust: Dict[str, Any]
    create_time: datetime = Field(default_factory=datetime.now, description="配置创建时间")
    update_time: datetime = Field(default_factory=datetime.now, description="配置更新时间")
