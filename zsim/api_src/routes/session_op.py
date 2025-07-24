import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from zsim.api_src.services.database.session_db import SessionDB, get_session_db
from zsim.api_src.services.sim_controller.sim_controller import SimController
from zsim.models.session.session_create import Session
from zsim.models.session.session_run import SessionRun

logger = logging.getLogger(__name__)
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


@router.get("/sessions/{session_id}/status", response_model=dict)
async def get_session_status(session_id: str, db: SessionDB = Depends(get_session_db)):
    """获取会话的当前状态。"""
    session = await db.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"status": session.status, "result": session.session_result}


@router.post("/sessions/{session_id}/run", response_model=dict)
async def run_session(
    session_id: str,
    session_run: SessionRun,
    background_tasks: BackgroundTasks,
    db: SessionDB = Depends(get_session_db),
    test_mode: bool = False,
):
    """启动一个会话模拟。"""
    session = await db.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.status == "running":
        raise HTTPException(status_code=400, detail="Session is already running")

    session.session_run = session_run
    session.status = "running"
    await db.update_session(session)

    sim_controller = SimController()
    if test_mode:
        background_tasks.add_task(sim_controller.execute_simulation_test)
    else:
        background_tasks.add_task(sim_controller.execute_simulation)

    if session_run.mode == "parallel" and session_run.parallel_config:
        args_iterator = sim_controller.generate_parallel_args(session, session_run)
        for sim_cfg in args_iterator:
            await sim_controller.put_into_queue(
                session.session_id, session_run.common_config, sim_cfg
            )
    else:
        await sim_controller.put_into_queue(session.session_id, session_run.common_config, None)

    return {"code": 0, "message": "Session started successfully", "session_id": session.session_id}


@router.post("/sessions/{session_id}/stop", response_model=Session)
async def stop_session(session_id: str, db: SessionDB = Depends(get_session_db)):
    """停止一个正在运行的会话。"""
    # This is a placeholder for now, as stopping a running process
    # from another process is complex and requires IPC.
    session = await db.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.status != "running":
        raise HTTPException(status_code=400, detail="Session is not running")

    # Logic to stop the simulation would go here.
    # For now, we'll just update the status.
    session.status = "stopped"
    await db.update_session(session)
    logger.warning(f"Stopping session {session_id} is not fully implemented.")

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
