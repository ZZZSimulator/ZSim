from pydantic import BaseModel, Field
from typing import Any, Dict, List


class SessionResult(BaseModel):
    """保存单次模拟的最终结果"""

    final_tick: int = Field(..., description="模拟结束时的最终帧数")
    global_stats: Dict[str, Any] = Field(..., description="全局统计数据")
    char_data: List[Dict[str, Any]] = Field(..., description="角色数据")
    enemy: List[Dict[str, Any]] = Field(..., description="敌人数据")
    simulation_completed: bool = Field(..., description="模拟是否完成")