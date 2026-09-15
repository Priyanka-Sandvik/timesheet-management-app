"""GET /api/v1/me — authenticated employee/admin self-lookup."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.dependencies import AuthenticatedUser, get_require_user, get_user_service
from app.models.schemas import MeResponse
from app.services.user_service import UserService

router = APIRouter(tags=["me"])

_require_user = get_require_user()


@router.get("/api/v1/me", response_model=MeResponse)
async def get_me(
    user: AuthenticatedUser = Depends(_require_user),
    user_service: UserService = Depends(get_user_service),
) -> MeResponse:
    return user_service.get_me(user.email)
