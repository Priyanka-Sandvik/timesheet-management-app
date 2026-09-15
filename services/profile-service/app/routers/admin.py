"""Admin-only routes: update user status, list users (used by Timelog Service's monthly
export employee list)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.dependencies import AuthenticatedUser, get_require_admin, get_user_service
from app.models.schemas import AdminUserListResponse, UpdateUserStatusRequest, UserStatusResponse
from app.services.user_service import UserService

router = APIRouter(tags=["admin"])

_require_admin = get_require_admin()


@router.put("/admin/users/{email}/status", response_model=UserStatusResponse)
async def update_user_status(
    email: str,
    payload: UpdateUserStatusRequest,
    _admin: AuthenticatedUser = Depends(_require_admin),
    user_service: UserService = Depends(get_user_service),
) -> UserStatusResponse:
    updated = user_service.set_user_status(email, payload.isActive)
    return UserStatusResponse(email=updated.email, isActive=updated.is_active)


@router.get("/admin/users", response_model=AdminUserListResponse)
async def list_users(
    activeOnly: bool = Query(default=False),
    _admin: AuthenticatedUser = Depends(_require_admin),
    user_service: UserService = Depends(get_user_service),
) -> AdminUserListResponse:
    users = user_service.list_users(active_only=activeOnly)
    return AdminUserListResponse(users=users)
