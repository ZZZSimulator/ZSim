from fastapi import APIRouter, Depends, HTTPException

from zsim.api_src.services.database.session_db import SessionDB, get_session_db
from zsim.models.session.session_create import Session

router = APIRouter()


@router.post("/sessions/", response_model=Session)
async def create_session(session: Session, db: SessionDB = Depends(get_session_db)):
    """创建一个新的会话。"""
    await db.add_session(session)
    return session


@router.get("/sessions/", response_model=list[Session])
async def read_sessions(db: SessionDB = Depends(get_session_db)):
    """获取所有会话列表。"""
    return await db.list_sessions()


@router.get("/sessions/{session_id}", response_model=Session)
async def read_session(session_id: str, db: SessionDB = Depends(get_session_db)):
    """根据 session_id 获取单个会话。"""
    session = await db.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.put("/sessions/{session_id}", response_model=Session)
async def update_session(
    session_id: str, session: Session, db: SessionDB = Depends(get_session_db)
):
    """更新一个已有的会话。"""
    # 确保 session_id 匹配
    if session_id != session.session_id:
        raise HTTPException(status_code=400, detail="Session ID in path does not match ID in body")

    existing_session = await db.get_session(session_id)
    if existing_session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    await db.update_session(session)
    return session


@router.delete("/sessions/{session_id}", status_code=204)
async def delete_session(session_id: str, db: SessionDB = Depends(get_session_db)):
    """根据 session_id 删除一个会话。"""
    existing_session = await db.get_session(session_id)
    if existing_session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    await db.delete_session(session_id)
    return
