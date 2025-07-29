import json
from datetime import datetime
from typing import Any, Self

import aiosqlite

from zsim.define import SQLITE_PATH
from zsim.models.enemy.enemy_config import EnemyConfig

_enemy_db: "EnemyDB | None" = None


class EnemyDB:
    def __init__(self):
        self._cache: dict[str, Any] = {}
        self._db_init: bool = False

    @classmethod
    async def creat(cls) -> Self:
        self = cls()
        await self._init_db()
        self._db_init = True
        return self

    async def _init_db(self) -> None:
        """初始化数据库，创建 enemy_configs 表"""
        if self._db_init:
            return
        async with aiosqlite.connect(SQLITE_PATH) as db:
            await db.execute(
                """CREATE TABLE IF NOT EXISTS enemy_configs (
                    config_id TEXT PRIMARY KEY,
                    enemy_index INTEGER NOT NULL,
                    enemy_adjust TEXT NOT NULL,
                    create_time TEXT NOT NULL,
                    update_time TEXT NOT NULL
                )"""
            )
            await db.commit()
        self._db_init = True

    async def add_enemy_config(self, config: EnemyConfig) -> None:
        """添加一个新的敌人配置到数据库"""
        # 更新时间戳
        config.update_time = datetime.now()

        async with aiosqlite.connect(SQLITE_PATH) as db:
            await db.execute(
                "INSERT INTO enemy_configs (config_id, enemy_index, enemy_adjust, create_time, update_time) VALUES (?, ?, ?, ?, ?)",
                (
                    config.config_id,
                    config.enemy_index,
                    json.dumps(config.enemy_adjust),
                    config.create_time.isoformat(),
                    config.update_time.isoformat(),
                ),
            )
            await db.commit()

    async def get_enemy_config(self, config_id: str) -> EnemyConfig | None:
        """根据配置ID从数据库获取敌人配置"""
        async with aiosqlite.connect(SQLITE_PATH) as db:
            cursor = await db.execute(
                "SELECT config_id, enemy_index, enemy_adjust, create_time, update_time FROM enemy_configs WHERE config_id = ?",
                (config_id,),
            )
            row = await cursor.fetchone()
            if row:
                return EnemyConfig(
                    config_id=row[0],
                    enemy_index=row[1],
                    enemy_adjust=json.loads(row[2]),
                    create_time=datetime.fromisoformat(row[3]),
                    update_time=datetime.fromisoformat(row[4]),
                )
        return None

    async def update_enemy_config(self, config: EnemyConfig) -> None:
        """更新数据库中的敌人配置"""
        # 更新时间戳
        config.update_time = datetime.now()

        async with aiosqlite.connect(SQLITE_PATH) as db:
            await db.execute(
                """UPDATE enemy_configs SET
                    enemy_index = ?, enemy_adjust = ?, update_time = ?
                   WHERE config_id = ?""",
                (
                    config.enemy_index,
                    json.dumps(config.enemy_adjust),
                    config.update_time.isoformat(),
                    config.config_id,
                ),
            )
            await db.commit()

    async def delete_enemy_config(self, config_id: str) -> None:
        """从数据库删除敌人配置"""
        async with aiosqlite.connect(SQLITE_PATH) as db:
            await db.execute("DELETE FROM enemy_configs WHERE config_id = ?", (config_id,))
            await db.commit()

    async def list_enemy_configs(self) -> list[EnemyConfig]:
        """从数据库获取所有敌人配置列表"""
        configs = []
        async with aiosqlite.connect(SQLITE_PATH) as db:
            cursor = await db.execute(
                "SELECT config_id, enemy_index, enemy_adjust, create_time, update_time FROM enemy_configs ORDER BY config_id"
            )
            rows = await cursor.fetchall()
            for row in rows:
                configs.append(
                    EnemyConfig(
                        config_id=row[0],
                        enemy_index=row[1],
                        enemy_adjust=json.loads(row[2]),
                        create_time=datetime.fromisoformat(row[3]),
                        update_time=datetime.fromisoformat(row[4]),
                    )
                )
        return configs


async def get_enemy_db() -> EnemyDB:
    """便捷函数：获取 EnemyDB 的单例实例"""
    global _enemy_db
    if _enemy_db is None:
        _enemy_db = await EnemyDB.creat()
    return _enemy_db
