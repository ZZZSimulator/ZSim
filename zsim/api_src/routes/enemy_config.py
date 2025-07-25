import logging
from fastapi import APIRouter, Depends, HTTPException
from typing import List
from datetime import datetime

from zsim.models.enemy.enemy_config import EnemyConfig
from zsim.api_src.services.database.enemy_db import get_enemy_db, EnemyDB

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/enemies/", response_model=List[str])
async def get_enemies(db: EnemyDB = Depends(get_enemy_db)):
    """获取所有可用敌人列表"""
    # TODO: 从数据库或配置文件中获取敌人列表
    # 这里暂时返回一个示例列表
    return ["敌人A", "敌人B", "敌人C", "敌人D"]


@router.get("/enemies/{enemy_id}/info", response_model=dict)
async def get_enemy_info(enemy_id: str, db: EnemyDB = Depends(get_enemy_db)):
    """获取敌人详细信息"""
    # TODO: 从数据库或配置文件中获取敌人详细信息
    # 这里暂时返回一个示例信息
    enemy_info = {
        "id": enemy_id,
        "name": f"敌人{enemy_id}",
        "level": 80,  # 示例等级
        "element": "物理",  # 示例元素类型
        "description": f"敌人{enemy_id}的详细信息"
    }
    return enemy_info


@router.post("/enemy-configs/", response_model=EnemyConfig)
async def create_enemy_config(config: EnemyConfig, db: EnemyDB = Depends(get_enemy_db)):
    """创建敌人配置"""
    # 检查敌人配置是否已存在
    existing_config = await db.get_enemy_config(config.config_id)
    if existing_config:
        raise HTTPException(status_code=400, detail="敌人配置已存在")
    
    # 设置创建和更新时间
    config.create_time = datetime.now()
    config.update_time = datetime.now()
    
    # 添加到数据库
    await db.add_enemy_config(config)
    return config


@router.get("/enemy-configs/", response_model=List[EnemyConfig])
async def list_enemy_configs(db: EnemyDB = Depends(get_enemy_db)):
    """获取所有敌人配置"""
    return await db.list_enemy_configs()


@router.get("/enemy-configs/{config_id}", response_model=EnemyConfig)
async def get_enemy_config(config_id: str, db: EnemyDB = Depends(get_enemy_db)):
    """获取特定敌人配置"""
    config = await db.get_enemy_config(config_id)
    if not config:
        raise HTTPException(status_code=404, detail="敌人配置未找到")
    return config


@router.put("/enemy-configs/{config_id}", response_model=EnemyConfig)
async def update_enemy_config(config_id: str, config: EnemyConfig, db: EnemyDB = Depends(get_enemy_db)):
    """更新敌人配置"""
    # 检查敌人配置是否存在
    existing_config = await db.get_enemy_config(config_id)
    if not existing_config:
        raise HTTPException(status_code=404, detail="敌人配置未找到")
    
    # 确保配置ID匹配
    if config_id != config.config_id:
        raise HTTPException(status_code=400, detail="配置ID不匹配")
    
    # 更新数据库
    await db.update_enemy_config(config)
    return config


@router.delete("/enemy-configs/{config_id}", status_code=204)
async def delete_enemy_config(config_id: str, db: EnemyDB = Depends(get_enemy_db)):
    """删除敌人配置"""
    # 检查敌人配置是否存在
    existing_config = await db.get_enemy_config(config_id)
    if not existing_config:
        raise HTTPException(status_code=404, detail="敌人配置未找到")
    
    # 从数据库删除
    await db.delete_enemy_config(config_id)