from fastapi import APIRouter

from . import session_op

router = APIRouter()

router.include_router(session_op.router, tags=["Session"])
