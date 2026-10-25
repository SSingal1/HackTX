from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel

from nextmove import __version__

router = APIRouter(tags=["system"])


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    service: str = "toyota-nextmove-backend"
    version: str = __version__


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse()
