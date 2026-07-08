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
        raise HTTPException(status_code=404, detail="会话不存在")
    return session


@router.get("/sessions/{session_id}/status", response_model=dict)
async def get_session_status(session_id: str, db: SessionDB = Depends(get_session_db)):
    """获取会话的当前状态。"""
    session = await db.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="会话不存在")
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
        raise HTTPException(status_code=404, detail="会话不存在")

    if session.status == "running":
        raise HTTPException(status_code=400, detail="会话正在运行中")

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

    return {"code": 0, "message": "会话已启动", "session_id": session.session_id}


@router.post("/sessions/{session_id}/stop", response_model=Session)
async def stop_session(session_id: str, db: SessionDB = Depends(get_session_db)):
    """停止一个正在运行的会话。"""
    # 这里暂时只做状态占位；跨进程停止正在运行的任务需要 IPC 配合。
    session = await db.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")

    if session.status != "running":
        raise HTTPException(status_code=400, detail="会话未在运行中")

    # 真正的停止逻辑后续接入；当前先更新状态。
    session.status = "stopped"
    await db.update_session(session)
    logger.warning(f"停止会话 {session_id} 的完整逻辑尚未实现。")

    return session


@router.put("/sessions/{session_id}", response_model=Session)
async def update_session(
    session_id: str, session: Session, db: SessionDB = Depends(get_session_db)
):
    """更新一个已有的会话。"""
    # 确保 session_id 匹配
    if session_id != session.session_id:
        raise HTTPException(status_code=400, detail="路径中的 session_id 与请求体不一致")

    existing_session = await db.get_session(session_id)
    if existing_session is None:
        raise HTTPException(status_code=404, detail="会话不存在")

    await db.update_session(session)
    return session


@router.delete("/sessions/{session_id}", status_code=204)
async def delete_session(session_id: str, db: SessionDB = Depends(get_session_db)):
    """根据 session_id 删除一个会话。"""
    existing_session = await db.get_session(session_id)
    if existing_session is None:
        raise HTTPException(status_code=404, detail="会话不存在")

    await db.delete_session(session_id)
    return
