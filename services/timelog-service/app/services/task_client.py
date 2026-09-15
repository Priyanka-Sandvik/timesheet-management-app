"""Async HTTP client for Task Service, forwarding the caller's Bearer JWT unchanged."""
from __future__ import annotations

import httpx
from py_common.core.errors import AppError


class TaskAssignment(dict):
    """Thin dict wrapper for a task assignment record returned by Task Service.

    Expected shape (per Task Service contract): { taskCode, taskName, projectName, ... }
    """

    @property
    def task_code(self) -> str:
        return self.get("taskCode", "")

    @property
    def task_name(self) -> str | None:
        return self.get("taskName")

    @property
    def project_name(self) -> str | None:
        return self.get("projectName")


class TaskServiceClient:
    def __init__(self, base_url: str, timeout: float = 10.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    async def get_my_tasks(self, bearer_token: str) -> list[TaskAssignment]:
        """GET /api/v1/tasks?scope=mine — returns the caller's active task assignments."""
        url = f"{self._base_url}/api/v1/tasks"
        headers = {"Authorization": f"Bearer {bearer_token}"}
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.get(url, params={"scope": "mine"}, headers=headers)
        except httpx.HTTPError as exc:
            raise AppError(
                status_code=502,
                code="UPSTREAM_ERROR",
                message=f"Unable to reach Task Service: {exc}",
            ) from exc

        if response.status_code >= 400:
            raise AppError(
                status_code=502,
                code="UPSTREAM_ERROR",
                message=f"Task Service returned {response.status_code} for scope=mine",
            )

        payload = response.json()
        if isinstance(payload, dict):
            items = payload.get("tasks", [])
            if not isinstance(items, list):
                raise AppError(
                    status_code=502,
                    code="UPSTREAM_ERROR",
                    message=f"Task Service response has unexpected format: tasks field is not a list",
                )
        elif isinstance(payload, list):
            items = payload
        else:
            items = []
        return [TaskAssignment(item) for item in items]
