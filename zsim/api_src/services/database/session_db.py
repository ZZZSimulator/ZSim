import json
from typing import Any, Self

import aiosqlite

from zsim.define import SQLITE_PATH
from zsim.models.session.session_create import Session

_session_db: "SessionDB | None" = None  # 单例实例


class SessionDB:
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
        """初始化数据库，创建 sessions 表"""
        if self._db_init:
            return
        async with aiosqlite.connect(SQLITE_PATH) as db:
            # Check if the table exists and has the session_name column
            cursor = await db.execute("PRAGMA table_info(sessions)")
            columns = await cursor.fetchall()
            column_names = [column[1] for column in columns]

            if not columns:
                # Table doesn't exist, create it with all columns
                await db.execute(
                    """CREATE TABLE sessions (
                        session_id TEXT PRIMARY KEY,
                        session_name TEXT NOT NULL DEFAULT '',
                        create_time TEXT NOT NULL,
                        status TEXT NOT NULL,
                        session_run TEXT,
                        session_result TEXT
                    )"""
                )
            elif "session_name" not in column_names:
                # Table exists but doesn't have session_name column, add it
                await db.execute(
                    "ALTER TABLE sessions ADD COLUMN session_name TEXT NOT NULL DEFAULT ''"
                )

            await db.commit()
        self._db_init = True

    async def add_session(self, session: Session) -> None:
        """添加一个新的会话到数据库"""
        async with aiosqlite.connect(SQLITE_PATH) as db:
            await db.execute(
                "INSERT INTO sessions (session_id, session_name, create_time, status, session_run, session_result) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    session.session_id,
                    session.session_name,
                    session.create_time.isoformat(),
                    session.status,
                    session.session_run.model_dump_json(indent=4) if session.session_run else None,
                    json.dumps([r.model_dump() for r in session.session_result])
                    if session.session_result
                    else None,
                ),
            )
            await db.commit()

    async def get_session(self, session_id: str) -> Session | None:
        """根据 session_id 从数据库获取会话"""
        async with aiosqlite.connect(SQLITE_PATH) as db:
            cursor = await db.execute("SELECT * FROM sessions WHERE session_id = ?", (session_id,))
            row = await cursor.fetchone()
            if row:
                # Get column names to ensure correct indexing
                column_names = [description[0] for description in cursor.description]
                row_dict = dict(zip(column_names, row))

                return Session(
                    session_id=row_dict["session_id"],
                    session_name=row_dict["session_name"],
                    create_time=row_dict["create_time"],
                    status=row_dict["status"],
                    session_run=json.loads(row_dict["session_run"])
                    if row_dict["session_run"]
                    else None,
                    session_result=json.loads(row_dict["session_result"])
                    if row_dict["session_result"]
                    else None,
                )
        return None

    async def update_session(self, session: Session) -> None:
        """更新数据库中的会话"""
        async with aiosqlite.connect(SQLITE_PATH) as db:
            await db.execute(
                """UPDATE sessions
                SET session_name = ?, create_time = ?, status = ?, session_run = ?, session_result = ?
                WHERE session_id = ?""",
                (
                    session.session_name,
                    session.create_time.isoformat(),
                    session.status,
                    session.session_run.model_dump_json(indent=4) if session.session_run else None,
                    json.dumps([r.model_dump() for r in session.session_result])
                    if session.session_result
                    else None,
                    session.session_id,
                ),
            )
            await db.commit()

    async def delete_session(self, session_id: str) -> None:
        """从数据库删除会话"""
        async with aiosqlite.connect(SQLITE_PATH) as db:
            await db.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
            await db.commit()

    async def list_sessions(self) -> list[Session]:
        """从数据库获取所有会话列表"""
        sessions = []
        async with aiosqlite.connect(SQLITE_PATH) as db:
            cursor = await db.execute("SELECT * FROM sessions ORDER BY create_time DESC")
            rows = await cursor.fetchall()
            column_names = [description[0] for description in cursor.description]
            for row in rows:
                row_dict = dict(zip(column_names, row))
                sessions.append(
                    Session(
                        session_id=row_dict["session_id"],
                        session_name=row_dict["session_name"],
                        create_time=row_dict["create_time"],
                        status=row_dict["status"],
                        session_run=json.loads(row_dict["session_run"])
                        if row_dict["session_run"]
                        else None,
                        session_result=json.loads(row_dict["session_result"])
                        if row_dict["session_result"]
                        else None,
                    )
                )
        return sessions


async def get_session_db() -> SessionDB:
    """便捷函数：获取 SessionDB 的单例实例"""
    global _session_db
    if _session_db is None:
        _session_db = await SessionDB.creat()
    return _session_db
