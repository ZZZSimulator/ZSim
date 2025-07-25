import logging
from fastapi import APIRouter, Depends, HTTPException
from typing import List
from datetime import datetime

from zsim.models.character.character_config import CharacterConfig
from zsim.api_src.services.database.character_db import get_character_db, CharacterDB

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/characters/", response_model=List[str])
async def get_characters(db: CharacterDB = Depends(get_character_db)):
    """获取所有可用角色列表"""
    # TODO: 从数据库或配置文件中获取角色列表
    # 这里暂时返回一个示例列表
    return ["Hugo", "Vivian", "AstraYao", "Yixuan", "Trigger", "Yuzuha"]


@router.get("/characters/{name}/info", response_model=dict)
async def get_character_info(name: str, db: CharacterDB = Depends(get_character_db)):
    """获取角色详细信息"""
    # TODO: 从数据库或配置文件中获取角色详细信息
    # 这里暂时返回一个示例信息
    character_info = {
        "name": name,
        "element": "以太",  # 示例元素类型
        "weapon_type": "音擎",  # 示例武器类型
        "rarity": 5,  # 示例稀有度
        "description": f"{name}的角色描述信息"
    }
    return character_info


@router.get("/weapons/", response_model=List[str])
async def get_weapons(db: CharacterDB = Depends(get_character_db)):
    """获取所有可用武器列表"""
    # TODO: 从数据库或配置文件中获取武器列表
    # 这里暂时返回一个示例列表
    return ["音擎A", "音擎B", "音擎C", "音擎D"]


@router.get("/equipments/", response_model=List[str])
async def get_equipments(db: CharacterDB = Depends(get_character_db)):
    """获取所有可用装备列表"""
    # TODO: 从数据库或配置文件中获取装备列表
    # 这里暂时返回一个示例列表
    return ["装备A", "装备B", "装备C", "装备D"]


@router.get("/equipments/sets", response_model=List[str])
async def get_equipment_sets(db: CharacterDB = Depends(get_character_db)):
    """获取装备套装信息"""
    # TODO: 从数据库或配置文件中获取装备套装信息
    # 这里暂时返回一个示例列表
    return ["套装A", "套装B", "套装C", "套装D"]


@router.post("/characters/{name}/configs", response_model=CharacterConfig)
async def create_character_config(name: str, config: CharacterConfig, db: CharacterDB = Depends(get_character_db)):
    """为指定角色创建配置"""
    # 检查角色配置是否已存在
    existing_config = await db.get_character_config(name, config.config_name)
    if existing_config:
        raise HTTPException(status_code=400, detail="角色配置已存在")
    
    # 设置角色名称和配置ID
    config.name = name
    config.config_id = f"{name}_{config.config_name}"
    config.create_time = datetime.now()
    config.update_time = datetime.now()
    
    # 添加到数据库
    await db.add_character_config(config)
    return config


@router.get("/characters/{name}/configs", response_model=List[CharacterConfig])
async def list_character_configs(name: str, db: CharacterDB = Depends(get_character_db)):
    """获取指定角色的所有配置"""
    return await db.list_character_configs(name)


@router.get("/characters/{name}/configs/{config_name}", response_model=CharacterConfig)
async def get_character_config(name: str, config_name: str, db: CharacterDB = Depends(get_character_db)):
    """获取指定角色的特定配置"""
    config = await db.get_character_config(name, config_name)
    if not config:
        raise HTTPException(status_code=404, detail="角色配置未找到")
    return config


@router.put("/characters/{name}/configs/{config_name}", response_model=CharacterConfig)
async def update_character_config(name: str, config_name: str, config: CharacterConfig, db: CharacterDB = Depends(get_character_db)):
    """更新指定角色的特定配置"""
    # 检查角色配置是否存在
    existing_config = await db.get_character_config(name, config_name)
    if not existing_config:
        raise HTTPException(status_code=404, detail="角色配置未找到")
    
    # 设置角色名称、配置名称和配置ID
    config.name = name
    config.config_name = config_name
    config.config_id = f"{name}_{config_name}"
    
    # 更新数据库
    await db.update_character_config(config)
    return config


@router.delete("/characters/{name}/configs/{config_name}", status_code=204)
async def delete_character_config(name: str, config_name: str, db: CharacterDB = Depends(get_character_db)):
    """删除指定角色的特定配置"""
    # 检查角色配置是否存在
    existing_config = await db.get_character_config(name, config_name)
    if not existing_config:
        raise HTTPException(status_code=404, detail="角色配置未找到")
    
    # 从数据库删除
    await db.delete_character_config(name, config_name)