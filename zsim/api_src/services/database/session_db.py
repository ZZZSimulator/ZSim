import json
from typing import Any

import aiosqlite

from zsim.define import SQLITE_PATH
from zsim.models.session.session_create import Session


class SessionDB:
    def __init__(self):
        self._cache: dict[str, Any] = {}
        self._db_init: bool = False

    async def _init_db(self) -> None:
        """初始化数据库，创建 sessions 表"""
        if self._db_init:
            return
        async with aiosqlite.connect(SQLITE_PATH) as db:
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                create_time TEXT NOT NULL,
                session_run TEXT,
                session_result TEXT
                )"""
            )
            await db.commit()
        self._db_init = True

    async def add_session(self, session: Session) -> None:
        """添加一个新的会话到数据库"""
        await self._init_db()
        async with aiosqlite.connect(SQLITE_PATH) as db:
            await db.execute(
                "INSERT INTO sessions (session_id, create_time, session_run, session_result) VALUES (?, ?, ?, ?)",
                (
                    session.session_id,
                    session.create_time.isoformat(),
                    session.session_run.model_dump_json(indent=4) if session.session_run else None,
                    json.dumps(session.session_result) if session.session_result else None,
                ),
            )
            await db.commit()

    async def get_session(self, session_id: str) -> Session | None:
        """根据 session_id 从数据库获取会话"""
        await self._init_db()
        async with aiosqlite.connect(SQLITE_PATH) as db:
            cursor = await db.execute("SELECT * FROM sessions WHERE session_id = ?", (session_id,))
            row = await cursor.fetchone()
            if row:
                return Session(
                    session_id=row[0],
                    create_time=row[1],
                    session_run=json.loads(row[2]) if row[2] else None,
                    session_result=json.loads(row[3]) if row[3] else None,
                )
        return None

    async def update_session(self, session: Session) -> None:
        """更新数据库中的会话"""
        await self._init_db()
        async with aiosqlite.connect(SQLITE_PATH) as db:
            await db.execute(
                """UPDATE sessions
                SET create_time = ?, session_run = ?, session_result = ?
                WHERE session_id = ?""",
                (
                    session.create_time.isoformat(),
                    session.session_run.model_dump_json(indent=4) if session.session_run else None,
                    json.dumps(session.session_result) if session.session_result else None,
                    session.session_id,
                ),
            )
            await db.commit()

    async def delete_session(self, session_id: str) -> None:
        """从数据库删除会话"""
        await self._init_db()
        async with aiosqlite.connect(SQLITE_PATH) as db:
            await db.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
            await db.commit()

    async def list_sessions(self) -> list[Session]:
        """从数据库获取所有会话列表"""
        await self._init_db()
        sessions = []
        async with aiosqlite.connect(SQLITE_PATH) as db:
            cursor = await db.execute("SELECT * FROM sessions ORDER BY create_time DESC")
            rows = await cursor.fetchall()
            for row in rows:
                sessions.append(
                    Session(
                        session_id=row[0],
                        create_time=row[1],
                        session_run=json.loads(row[2]) if row[2] else None,
                        session_result=json.loads(row[3]) if row[3] else None,
                    )
                )
        return sessions


_session_db: SessionDB | None = None  # 单例实例


async def get_session_db() -> SessionDB:
    """便捷函数：获取 SessionDB 的单例实例"""
    global _session_db
    if _session_db is None:
        _session_db = SessionDB()
    return _session_db
