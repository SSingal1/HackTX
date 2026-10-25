from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from nextmove.api.dependencies import get_profile_repository
from nextmove.data.repositories import ProfileRepository

router = APIRouter(prefix="/profiles", tags=["profiles"])


class ProfileListResponse(BaseModel):
    profile_ids: list[str]


def _service_unavailable(exc: Exception) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=f"Profile data is unavailable: {type(exc).__name__}",
    )


@router.get("", response_model=ProfileListResponse)
def list_profiles(
    repository: ProfileRepository = Depends(get_profile_repository),
) -> ProfileListResponse:
    try:
        return ProfileListResponse(profile_ids=repository.list_profile_ids())
    except Exception as exc:
        raise _service_unavailable(exc) from exc


@router.get("/{profile_id}", response_model=dict[str, Any])
def get_profile(
    profile_id: str,
    repository: ProfileRepository = Depends(get_profile_repository),
) -> dict[str, Any]:
    try:
        profile = repository.get_profile(profile_id)
    except Exception as exc:
        raise _service_unavailable(exc) from exc
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
    return dict(profile)
