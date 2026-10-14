"""GET /api/v1/tasks - employee-facing "my tasks" endpoint (architecture doc §8.2)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from py_common.core.jwt_verify import AuthenticatedUser

from app.core.deps import get_task_service, require_user
from app.models.schemas import TaskListResponse, TaskOut
from app.services.task_service import TaskService

router = APIRouter(prefix="/api/v1/tasks", tags=["tasks"])


@router.get("", response_model=TaskListResponse)
async def list_my_tasks(
    scope: str = Query(default="mine"),
    search: str | None = Query(default=None),
    user: AuthenticatedUser = Depends(require_user),
    service: TaskService = Depends(get_task_service),
):
    # `scope=mine` is the only supported scope today: results are always filtered to the
    # caller's own assigned rows (PartitionKey = caller's email), per architecture doc §8.2.
    tasks = await service.list_my_tasks(email=user.email, search=search)
    return TaskListResponse(tasks=tasks)


@router.get("/catalog", response_model=TaskListResponse)
async def list_available_tasks(
    search: str | None = Query(default=None),
    user: AuthenticatedUser = Depends(require_user),
    service: TaskService = Depends(get_task_service),
):
    """Open task templates the caller can self-assign to - excludes tasks already assigned
    to them, and never exposes OnHold/Closed templates (those remain admin-assign-only).
    """
    tasks = await service.list_available_tasks(email=user.email, search=search)
    return TaskListResponse(tasks=tasks)


@router.post("/{task_code}/assign-self", response_model=TaskOut, status_code=201)
async def assign_self(
    task_code: str,
    user: AuthenticatedUser = Depends(require_user),
    service: TaskService = Depends(get_task_service),
):
    """Employee self-assignment to an existing Open task template. Creating new task
    templates remains an admin-only action (see /admin/tasks).
    """
    return await service.self_assign_task(task_code=task_code, email=user.email)


@router.delete("/{task_code}/assign-self", status_code=204)
async def unassign_self(
    task_code: str,
    user: AuthenticatedUser = Depends(require_user),
    service: TaskService = Depends(get_task_service),
):
    """Employee self-removal from a task they previously self-assigned (or were assigned
    to by an admin) - only removes the caller's own assignment row.
    """
    await service.self_unassign_task(task_code=task_code, email=user.email)
