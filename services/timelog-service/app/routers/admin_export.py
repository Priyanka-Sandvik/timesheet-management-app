"""Admin-only monthly timesheet export route — streams an .xlsx built entirely in memory."""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from py_common.core.jwt_verify import AuthenticatedUser

from app.config import get_settings
from app.core.jwt import build_jwt_verifier_dependencies
from app.services.export_service import (
    EmployeeMonthData,
    build_monthly_workbook,
    month_bounds,
    previous_calendar_month,
)
from app.services.profile_client import ProfileServiceClient
from app.services.task_client import TaskAssignment  # noqa: F401 (typing reference only)

router = APIRouter(prefix="/admin/timesheet", tags=["admin-export"])

_bearer_scheme = HTTPBearer(auto_error=False)
_verifier, require_user, require_admin = build_jwt_verifier_dependencies(get_settings())

XLSX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def get_repository(request: Request):
    return request.app.state.timesheet_repository


def get_profile_client(request: Request) -> ProfileServiceClient:
    return request.app.state.profile_client


def get_bearer_token(credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme)) -> str:
    from py_common.core.errors import AppError

    if credentials is None or not credentials.credentials:
        raise AppError(status_code=401, code="UNAUTHORIZED", message="Missing bearer token")
    return credentials.credentials


@router.get("/export/monthly")
async def export_monthly(
    month: str | None = None,
    user: AuthenticatedUser = Depends(require_admin),
    bearer_token: str = Depends(get_bearer_token),
    repository=Depends(get_repository),
    profile_client: ProfileServiceClient = Depends(get_profile_client),
):
    resolved_month = month or previous_calendar_month(date.today())
    _, _, lower_bound, upper_bound = month_bounds(resolved_month)

    active_users = await profile_client.get_active_users(bearer_token)
    employee_emails = [u.get("email") for u in active_users if u.get("email")]

    employees_data: list[EmployeeMonthData] = []
    for email in employee_emails:
        entries = await repository.get_month_entries(email, lower_bound, upper_bound)
        employees_data.append(EmployeeMonthData(email=email, entries=entries))

    workbook_bytes = build_monthly_workbook(resolved_month, employees_data)

    filename = f"timesheet-export-{resolved_month}.xlsx"
    return StreamingResponse(
        iter([workbook_bytes]),
        media_type=XLSX_MEDIA_TYPE,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
