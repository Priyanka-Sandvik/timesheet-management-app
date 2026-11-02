"""Admin-only routes: list, create, edit and bulk-import users (the list is also used by
Timelog Service's monthly export employee list)."""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Query, UploadFile
from py_common.core.errors import AppError

from app.core.logging import log_event
from app.dependencies import AuthenticatedUser, get_require_admin, get_user_service
from app.models.schemas import (
    AdminUserListResponse,
    AdminUserSummary,
    CoeAdminSyncRequest,
    CoeAdminSyncResponse,
    CreateUserRequest,
    UpdateUserRequest,
    UserImportResponse,
)
from app.services.user_import import parse_import_file
from app.services.user_service import UserService

router = APIRouter(tags=["admin"])
logger = logging.getLogger("profile-service")

_require_admin = get_require_admin()


@router.get("/admin/users", response_model=AdminUserListResponse)
async def list_users(
    activeOnly: bool = Query(default=False),
    _admin: AuthenticatedUser = Depends(_require_admin),
    user_service: UserService = Depends(get_user_service),
) -> AdminUserListResponse:
    users = user_service.list_users(active_only=activeOnly)
    return AdminUserListResponse(users=users)


@router.post("/admin/users", response_model=AdminUserSummary, status_code=201)
async def create_user(
    payload: CreateUserRequest,
    _admin: AuthenticatedUser = Depends(_require_admin),
    user_service: UserService = Depends(get_user_service),
) -> AdminUserSummary:
    return user_service.create_user(payload)


@router.post("/admin/users/import", response_model=UserImportResponse)
async def import_users(
    file: UploadFile,
    _admin: AuthenticatedUser = Depends(_require_admin),
    user_service: UserService = Depends(get_user_service),
) -> UserImportResponse:
    if not file.filename:
        raise AppError(status_code=400, code="VALIDATION_ERROR", message="Uploaded file must have a filename")

    content = await file.read()  # parsed entirely in memory - never written to disk
    return user_service.import_users(parse_import_file(file.filename, content))


# Declared before /admin/users/{email} so "coe-admins" isn't read as an email.
@router.put("/admin/users/coe-admins", response_model=CoeAdminSyncResponse)
async def sync_coe_admins(
    payload: CoeAdminSyncRequest,
    _admin: AuthenticatedUser = Depends(_require_admin),
    user_service: UserService = Depends(get_user_service),
) -> CoeAdminSyncResponse:
    result = user_service.sync_coe_admins(payload.emails)
    log_event(
        logger,
        "coe_admin_sync",
        user=_admin.email,
        requested=len(payload.emails),
        promoted=result.promoted,
        demoted=result.demoted,
        unknown=result.unknown,
    )
    return result


@router.put("/admin/users/{email}", response_model=AdminUserSummary)
async def update_user(
    email: str,
    payload: UpdateUserRequest,
    _admin: AuthenticatedUser = Depends(_require_admin),
    user_service: UserService = Depends(get_user_service),
) -> AdminUserSummary:
    return user_service.update_user(email, payload)
