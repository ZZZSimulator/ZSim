from fastapi import APIRouter

from .apl import router as apl_router
from .character_config import router as character_config_router
from .enemy_config import router as enemy_config_router
from .session_op import router as session_op_router

router = APIRouter()

router.include_router(session_op_router, tags=["Session"])
router.include_router(character_config_router, tags=["Character"])
router.include_router(enemy_config_router, tags=["Enemy"])
router.include_router(apl_router, tags=["APL"])
