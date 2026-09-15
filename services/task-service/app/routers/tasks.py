"""GET /api/v1/tasks - employee-facing "my tasks" endpoint (architecture doc §8.2)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from py_common.core.jwt_verify import AuthenticatedUser

from app.core.deps import get_task_service, require_user
from app.models.schemas import TaskListResponse
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
