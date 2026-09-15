"""Employee-facing timesheet routes: grid, bulk entries, generate, copy-previous, submit."""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from py_common.core.errors import AppError
from py_common.core.jwt_verify import AuthenticatedUser

from app.config import get_settings
from app.core.jwt import build_jwt_verifier_dependencies
from app.models.schemas import (
    BulkUpsertRequest,
    BulkUpsertResponse,
    CopyPreviousResponse,
    GenerateResponse,
    SubmitResponse,
    TimesheetGridResponse,
)
from app.services.timesheet_service import TimesheetService

router = APIRouter(prefix="/api/v1/timesheet", tags=["timesheet"])

_bearer_scheme = HTTPBearer(auto_error=False)
_verifier, require_user, require_admin = build_jwt_verifier_dependencies(get_settings())


def get_timesheet_service(request: Request) -> TimesheetService:
    return request.app.state.timesheet_service


def get_bearer_token(credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme)) -> str:
    if credentials is None or not credentials.credentials:
        raise AppError(status_code=401, code="UNAUTHORIZED", message="Missing bearer token")
    return credentials.credentials


@router.get("", response_model=TimesheetGridResponse)
async def get_timesheet(
    weekStart: date,
    userId: str | None = None,
    user: AuthenticatedUser = Depends(require_user),
    service: TimesheetService = Depends(get_timesheet_service),
):
    target_user_id = userId or user.email
    if target_user_id != user.email and not user.is_admin:
        raise AppError(
            status_code=403,
            code="FORBIDDEN",
            message="Only Admins may view another user's timesheet",
        )

    return await service.get_week_grid(target_user_id, weekStart)


@router.put("/entries", response_model=BulkUpsertResponse)
async def put_entries(
    body: BulkUpsertRequest,
    userId: str | None = None,
    user: AuthenticatedUser = Depends(require_user),
    bearer_token: str = Depends(get_bearer_token),
    service: TimesheetService = Depends(get_timesheet_service),
):
    target_user_id = userId or user.email
    if target_user_id != user.email and not user.is_admin:
        raise AppError(
            status_code=403,
            code="FORBIDDEN",
            message="Only Admins may edit another user's timesheet",
        )

    saved = await service.upsert_entries(
        user_id=target_user_id,
        week_start=body.weekStart,
        entries=body.entries,
        is_admin=user.is_admin,
        bearer_token=bearer_token,
    )
    return BulkUpsertResponse(saved=saved)


@router.post("/generate", response_model=GenerateResponse)
async def generate_week(
    weekStart: date,
    user: AuthenticatedUser = Depends(require_user),
    bearer_token: str = Depends(get_bearer_token),
    service: TimesheetService = Depends(get_timesheet_service),
):
    rows_created = await service.generate_week(user_id=user.email, week_start=weekStart, bearer_token=bearer_token)
    return GenerateResponse(rowsCreated=rows_created)


@router.post("/copy-previous", response_model=CopyPreviousResponse)
async def copy_previous(
    weekStart: date,
    user: AuthenticatedUser = Depends(require_user),
    service: TimesheetService = Depends(get_timesheet_service),
):
    rows_copied = await service.copy_previous_week(user_id=user.email, week_start=weekStart)
    return CopyPreviousResponse(rowsCopied=rows_copied)


@router.post("/submit", response_model=SubmitResponse)
async def submit_week(
    weekStart: date,
    user: AuthenticatedUser = Depends(require_user),
    service: TimesheetService = Depends(get_timesheet_service),
):
    status_value = await service.submit_week(user_id=user.email, week_start=weekStart)
    return SubmitResponse(status=status_value)
