import json
import aiosqlite
from typing import Any, List, Optional
from zsim.define import SQLITE_PATH
from zsim.models.character.character_config import CharacterConfig
from datetime import datetime


_character_db: "CharacterDB | None" = None


class CharacterDB:
    def __init__(self):
        self._cache: dict[str, Any] = {}
        self._db_init: bool = False

    async def _init_db(self) -> None:
        """初始化数据库，创建 character_configs 表"""
        if self._db_init:
            return
        async with aiosqlite.connect(SQLITE_PATH) as db:
            await db.execute(
                """CREATE TABLE IF NOT EXISTS character_configs (
                    config_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    config_name TEXT NOT NULL,
                    weapon TEXT NOT NULL,
                    weapon_level INTEGER NOT NULL,
                    cinema INTEGER NOT NULL,
                    crit_balancing BOOLEAN NOT NULL,
                    crit_rate_limit REAL NOT NULL,
                    scATK_percent INTEGER NOT NULL,
                    scATK INTEGER NOT NULL,
                    scHP_percent INTEGER NOT NULL,
                    scHP INTEGER NOT NULL,
                    scDEF_percent INTEGER NOT NULL,
                    scDEF INTEGER NOT NULL,
                    scAnomalyProficiency INTEGER NOT NULL,
                    scPEN INTEGER NOT NULL,
                    scCRIT INTEGER NOT NULL,
                    scCRIT_DMG INTEGER NOT NULL,
                    drive4 TEXT NOT NULL,
                    drive5 TEXT NOT NULL,
                    drive6 TEXT NOT NULL,
                    equip_style TEXT NOT NULL,
                    equip_set4 TEXT,
                    equip_set2_a TEXT,
                    equip_set2_b TEXT,
                    equip_set2_c TEXT,
                    create_time TEXT NOT NULL,
                    update_time TEXT NOT NULL
                )"""
            )
            await db.commit()
        self._db_init = True

    async def add_character_config(self, config: CharacterConfig) -> None:
        """添加一个新的角色配置到数据库"""
        await self._init_db()
        # 设置config_id
        if not config.config_id:
            config.config_id = f"{config.name}_{config.config_name}"
            
        # 更新时间戳
        config.update_time = datetime.now()
        
        async with aiosqlite.connect(SQLITE_PATH) as db:
            await db.execute(
                """INSERT INTO character_configs (
                    config_id, name, config_name, weapon, weapon_level, cinema, crit_balancing, crit_rate_limit,
                    scATK_percent, scATK, scHP_percent, scHP, scDEF_percent, scDEF, scAnomalyProficiency,
                    scPEN, scCRIT, scCRIT_DMG, drive4, drive5, drive6, equip_style, equip_set4,
                    equip_set2_a, equip_set2_b, equip_set2_c, create_time, update_time
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    config.config_id, config.name, config.config_name, config.weapon, config.weapon_level, config.cinema,
                    config.crit_balancing, config.crit_rate_limit, config.scATK_percent, config.scATK,
                    config.scHP_percent, config.scHP, config.scDEF_percent, config.scDEF,
                    config.scAnomalyProficiency, config.scPEN, config.scCRIT, config.scCRIT_DMG,
                    config.drive4, config.drive5, config.drive6, config.equip_style, config.equip_set4,
                    config.equip_set2_a, config.equip_set2_b, config.equip_set2_c,
                    config.create_time.isoformat(), config.update_time.isoformat()
                ),
            )
            await db.commit()

    async def get_character_config(self, name: str, config_name: str) -> CharacterConfig | None:
        """根据角色名称和配置名称从数据库获取角色配置"""
        await self._init_db()
        config_id = f"{name}_{config_name}"
        async with aiosqlite.connect(SQLITE_PATH) as db:
            cursor = await db.execute(
                """SELECT config_id, name, config_name, weapon, weapon_level, cinema, crit_balancing, crit_rate_limit,
                          scATK_percent, scATK, scHP_percent, scHP, scDEF_percent, scDEF, scAnomalyProficiency,
                          scPEN, scCRIT, scCRIT_DMG, drive4, drive5, drive6, equip_style, equip_set4,
                          equip_set2_a, equip_set2_b, equip_set2_c, create_time, update_time
                   FROM character_configs 
                   WHERE config_id = ?""", 
                (config_id,)
            )
            row = await cursor.fetchone()
            if row:
                return CharacterConfig(
                    config_id=row[0],
                    name=row[1],
                    config_name=row[2],
                    weapon=row[3],
                    weapon_level=row[4],
                    cinema=row[5],
                    crit_balancing=row[6],
                    crit_rate_limit=row[7],
                    scATK_percent=row[8],
                    scATK=row[9],
                    scHP_percent=row[10],
                    scHP=row[11],
                    scDEF_percent=row[12],
                    scDEF=row[13],
                    scAnomalyProficiency=row[14],
                    scPEN=row[15],
                    scCRIT=row[16],
                    scCRIT_DMG=row[17],
                    drive4=row[18],
                    drive5=row[19],
                    drive6=row[20],
                    equip_style=row[21],
                    equip_set4=row[22],
                    equip_set2_a=row[23],
                    equip_set2_b=row[24],
                    equip_set2_c=row[25],
                    create_time=datetime.fromisoformat(row[26]),
                    update_time=datetime.fromisoformat(row[27])
                )
        return None

    async def update_character_config(self, config: CharacterConfig) -> None:
        """更新数据库中的角色配置"""
        await self._init_db()
        # 更新时间戳
        config.update_time = datetime.now()
        
        async with aiosqlite.connect(SQLITE_PATH) as db:
            await db.execute(
                """UPDATE character_configs SET
                    name = ?, config_name = ?, weapon = ?, weapon_level = ?, cinema = ?, crit_balancing = ?, crit_rate_limit = ?,
                    scATK_percent = ?, scATK = ?, scHP_percent = ?, scHP = ?, scDEF_percent = ?, scDEF = ?,
                    scAnomalyProficiency = ?, scPEN = ?, scCRIT = ?, scCRIT_DMG = ?, drive4 = ?, drive5 = ?,
                    drive6 = ?, equip_style = ?, equip_set4 = ?, equip_set2_a = ?, equip_set2_b = ?,
                    equip_set2_c = ?, update_time = ?
                   WHERE config_id = ?""",
                (
                    config.name, config.config_name, config.weapon, config.weapon_level, config.cinema, config.crit_balancing,
                    config.crit_rate_limit, config.scATK_percent, config.scATK, config.scHP_percent,
                    config.scHP, config.scDEF_percent, config.scDEF, config.scAnomalyProficiency,
                    config.scPEN, config.scCRIT, config.scCRIT_DMG, config.drive4, config.drive5,
                    config.drive6, config.equip_style, config.equip_set4, config.equip_set2_a,
                    config.equip_set2_b, config.equip_set2_c, config.update_time.isoformat(), config.config_id
                ),
            )
            await db.commit()

    async def delete_character_config(self, name: str, config_name: str) -> None:
        """从数据库删除角色配置"""
        await self._init_db()
        config_id = f"{name}_{config_name}"
        async with aiosqlite.connect(SQLITE_PATH) as db:
            await db.execute(
                "DELETE FROM character_configs WHERE config_id = ?", 
                (config_id,)
            )
            await db.commit()

    async def list_character_configs(self, name: str) -> List[CharacterConfig]:
        """从数据库获取指定角色的所有配置列表"""
        await self._init_db()
        configs = []
        async with aiosqlite.connect(SQLITE_PATH) as db:
            cursor = await db.execute(
                """SELECT config_id, name, config_name, weapon, weapon_level, cinema, crit_balancing, crit_rate_limit,
                          scATK_percent, scATK, scHP_percent, scHP, scDEF_percent, scDEF, scAnomalyProficiency,
                          scPEN, scCRIT, scCRIT_DMG, drive4, drive5, drive6, equip_style, equip_set4,
                          equip_set2_a, equip_set2_b, equip_set2_c, create_time, update_time
                   FROM character_configs 
                   WHERE name = ? 
                   ORDER BY config_name""",
                (name,)
            )
            rows = await cursor.fetchall()
            for row in rows:
                configs.append(
                    CharacterConfig(
                        config_id=row[0],
                        name=row[1],
                        config_name=row[2],
                        weapon=row[3],
                        weapon_level=row[4],
                        cinema=row[5],
                        crit_balancing=row[6],
                        crit_rate_limit=row[7],
                        scATK_percent=row[8],
                        scATK=row[9],
                        scHP_percent=row[10],
                        scHP=row[11],
                        scDEF_percent=row[12],
                        scDEF=row[13],
                        scAnomalyProficiency=row[14],
                        scPEN=row[15],
                        scCRIT=row[16],
                        scCRIT_DMG=row[17],
                        drive4=row[18],
                        drive5=row[19],
                        drive6=row[20],
                        equip_style=row[21],
                        equip_set4=row[22],
                        equip_set2_a=row[23],
                        equip_set2_b=row[24],
                        equip_set2_c=row[25],
                        create_time=datetime.fromisoformat(row[26]),
                        update_time=datetime.fromisoformat(row[27])
                    )
                )
        return configs


async def get_character_db() -> CharacterDB:
    """便捷函数：获取 CharacterDB 的单例实例"""
    global _character_db
    if _character_db is None:
        _character_db = CharacterDB()
    return _character_db