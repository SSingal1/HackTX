from fastapi import APIRouter

from nextmove.api.decisions import router as decisions_router
from nextmove.api.guardian import router as guardian_router
from nextmove.api.health import router as health_router
from nextmove.api.profiles import router as profiles_router

api_router = APIRouter()
api_router.include_router(guardian_router)
api_router.include_router(health_router)
api_router.include_router(profiles_router)
api_router.include_router(decisions_router)
