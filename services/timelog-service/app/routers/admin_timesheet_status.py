"""Admin-only routes for viewing and toggling employees' weekly timesheet status."""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from py_common.core.errors import AppError
from py_common.core.jwt_verify import AuthenticatedUser

from app.config import get_settings
from app.core.jwt import build_jwt_verifier_dependencies
from app.models.schemas import AdminPeriodStatusResponse, AdminSetStatusRequest, AdminSetStatusResponse
from app.services.export_service import previous_calendar_month
from app.services.profile_client import ProfileServiceClient
from app.services.timesheet_service import TimesheetService

router = APIRouter(prefix="/admin/timesheet", tags=["admin-timesheet-status"])

_bearer_scheme = HTTPBearer(auto_error=False)
_verifier, require_user, require_admin = build_jwt_verifier_dependencies(get_settings())


def get_timesheet_service(request: Request) -> TimesheetService:
    return request.app.state.timesheet_service


def get_profile_client(request: Request) -> ProfileServiceClient:
    return request.app.state.profile_client


def get_bearer_token(credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme)) -> str:
    if credentials is None or not credentials.credentials:
        raise AppError(status_code=401, code="UNAUTHORIZED", message="Missing bearer token")
    return credentials.credentials


@router.get("/status", response_model=AdminPeriodStatusResponse)
async def get_period_statuses(
    month: str | None = None,
    user: AuthenticatedUser = Depends(require_admin),
    bearer_token: str = Depends(get_bearer_token),
    service: TimesheetService = Depends(get_timesheet_service),
    profile_client: ProfileServiceClient = Depends(get_profile_client),
):
    resolved_month = month or previous_calendar_month(date.today())

    active_users = await profile_client.get_active_users(bearer_token)
    employee_emails = [u.get("email") for u in active_users if u.get("email")]

    employees = await service.get_period_statuses(employee_emails, resolved_month)
    return AdminPeriodStatusResponse(period=resolved_month, employees=employees)


@router.put("/status/{user_id}", response_model=AdminSetStatusResponse)
async def set_week_status(
    user_id: str,
    weekStart: date,
    body: AdminSetStatusRequest,
    user: AuthenticatedUser = Depends(require_admin),
    service: TimesheetService = Depends(get_timesheet_service),
):
    new_status = await service.set_week_status(user_id=user_id, week_start=weekStart, new_status=body.status)
    return AdminSetStatusResponse(userId=user_id, weekStart=weekStart, status=new_status)
