"""Admin-only task management endpoints (architecture doc §8.2).

All routes here require `require_admin` (isAdmin claim verified locally from the JWT -
no callback to Profile Service for that check). The optional Profile Service call in
assign_task is a separate concern: validating that an email being assigned actually
exists / is active.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, UploadFile

from py_common.core.errors import AppError
from py_common.core.jwt_verify import AuthenticatedUser

from app.config import get_settings
from app.core.deps import get_bearer_token, get_task_service, require_admin
from app.models.schemas import (
    AdminTaskListResponse,
    AssignRequest,
    AssignResponse,
    ImportResult,
    TaskCreateRequest,
    TaskOut,
    TaskUpdateRequest,
)
from app.services.import_service import parse_import_file
from app.services.task_service import TaskService

router = APIRouter(prefix="/admin/tasks", tags=["admin-tasks"])


@router.post("/import", response_model=ImportResult)
async def import_tasks(
    file: UploadFile,
    user: AuthenticatedUser = Depends(require_admin),
    service: TaskService = Depends(get_task_service),
):
    if not file.filename:
        raise AppError(status_code=400, code="VALIDATION_ERROR", message="Uploaded file must have a filename")

    content = await file.read()  # parsed entirely in memory - never written to disk
    parsed = parse_import_file(file.filename, content)
    return await service.import_tasks(parsed=parsed, actor_email=user.email)


@router.post("", response_model=TaskOut, status_code=201)
async def create_task(
    body: TaskCreateRequest,
    user: AuthenticatedUser = Depends(require_admin),
    service: TaskService = Depends(get_task_service),
):
    return await service.create_task(body=body, actor_email=user.email)


@router.post("/{task_code}/assign", response_model=AssignResponse)
async def assign_task(
    task_code: str,
    body: AssignRequest,
    user: AuthenticatedUser = Depends(require_admin),
    service: TaskService = Depends(get_task_service),
    bearer_token: str | None = Depends(get_bearer_token),
):
    return await service.assign_task(
        task_code=task_code, emails=body.emails, actor_email=user.email, bearer_token=bearer_token
    )


@router.delete("/{task_code}/assign/{email}", status_code=204)
async def unassign_task(
    task_code: str,
    email: str,
    user: AuthenticatedUser = Depends(require_admin),
    service: TaskService = Depends(get_task_service),
):
    await service.unassign_task(task_code=task_code, email=email, actor_email=user.email)


@router.get("", response_model=AdminTaskListResponse)
async def list_all_tasks(
    pageSize: int | None = Query(default=None, ge=1, le=1000),
    continuationToken: str | None = Query(default=None),
    search: str | None = Query(default=None),
    status: str | None = Query(default=None),
    user: AuthenticatedUser = Depends(require_admin),
    service: TaskService = Depends(get_task_service),
):
    page_size = pageSize or get_settings().DEFAULT_ADMIN_LIST_PAGE_SIZE
    tasks, next_token = await service.list_all_tasks(
        page_size=page_size, continuation_token=continuationToken, search=search, status=status
    )
    return AdminTaskListResponse(tasks=tasks, nextPage=next_token)


@router.put("/{task_code}", response_model=TaskOut)
async def update_task_template(
    task_code: str,
    body: TaskUpdateRequest,
    user: AuthenticatedUser = Depends(require_admin),
    service: TaskService = Depends(get_task_service),
):
    return await service.update_template(task_code=task_code, update=body, actor_email=user.email)


@router.delete("/{task_code}", status_code=204)
async def delete_task_template(
    task_code: str,
    user: AuthenticatedUser = Depends(require_admin),
    service: TaskService = Depends(get_task_service),
):
    await service.delete_template(task_code=task_code, actor_email=user.email)
