"""Business logic for the Task Service (architecture doc §8.2 / §6).

Router -> Service -> Repository layering: this module is the ONLY place business rules
live. Routers call in here; this module calls the repository for storage access.
"""
from __future__ import annotations

import logging

from py_common.core.errors import AppError
from py_common.core.logging import log_event

from app.config import Settings
from app.models.schemas import (
    AssignResponse,
    ImportParseResult,
    ImportResult,
    ImportRowError,
    SkippedAssignment,
    TaskCreateRequest,
    TaskOut,
    TaskUpdateRequest,
)
from app.repositories.task_repository import entity_to_task_out
from app.services.profile_client import validate_user_exists

logger = logging.getLogger("task-service")


class TaskService:
    def __init__(self, repository, settings: Settings) -> None:
        self._repo = repository
        self._settings = settings

    # ------------------------------------------------------------------ #
    # GET /api/v1/tasks
    # ------------------------------------------------------------------ #
    async def list_my_tasks(self, *, email: str, search: str | None) -> list[TaskOut]:
        entities = await self._repo.list_by_partition(email)
        tasks = [entity_to_task_out(e) for e in entities]

        if search:
            needle = search.lower()
            tasks = [
                t
                for t in tasks
                if needle in t.taskName.lower()
                or needle in t.taskCode.lower()
                or (t.description is not None and needle in t.description.lower())
            ]

        return tasks

    # ------------------------------------------------------------------ #
    # POST /admin/tasks/import
    # ------------------------------------------------------------------ #
    async def import_tasks(self, *, parsed: ImportParseResult, actor_email: str) -> ImportResult:
        errors: list[ImportRowError] = list(parsed.errors)
        imported = 0

        for row in parsed.rows:
            fields = {
                "TaskName": row.task_name,
                "Description": row.description,
                "Sponsor": row.sponsor,
                "CostCentre": row.cost_centre,
                "CoEResponsible": row.coe_responsible,
                "Status": row.status,
            }
            try:
                await self._repo.upsert_template(row.task_code, fields)
                imported += 1
            except Exception as exc:  # pragma: no cover - defensive; storage failures are rare
                errors.append(ImportRowError(row=0, reason=f"Failed to save TaskCode '{row.task_code}': {exc}"))

        result = ImportResult(imported=imported, skipped=len(errors), errors=errors)
        log_event(
            logger,
            "task_import",
            user=actor_email,
            imported=result.imported,
            skipped=result.skipped,
            error_count=len(errors),
        )
        return result

    # ------------------------------------------------------------------ #
    # POST /admin/tasks - manual single-task creation
    # ------------------------------------------------------------------ #
    async def create_task(self, *, body: TaskCreateRequest, actor_email: str) -> TaskOut:
        existing = await self._repo.get_template(body.taskCode)
        if existing is not None:
            raise AppError(
                status_code=409,
                code="CONFLICT",
                message=f"Task template '{body.taskCode}' already exists",
            )

        fields = {
            "TaskName": body.taskName,
            "Description": body.description,
            "Sponsor": body.sponsor,
            "CostCentre": body.costCentre,
            "CoEResponsible": body.coeResponsible,
            "Status": body.status,
        }
        entity = await self._repo.upsert_template(body.taskCode, fields)
        log_event(logger, "task_create", user=actor_email, task_code=body.taskCode)
        return entity_to_task_out(entity)

    # ------------------------------------------------------------------ #
    # POST /admin/tasks/{taskCode}/assign
    # ------------------------------------------------------------------ #
    async def assign_task(
        self, *, task_code: str, emails: list[str], actor_email: str, bearer_token: str | None
    ) -> AssignResponse:
        template = await self._repo.get_template(task_code)
        if template is None:
            raise AppError(
                status_code=404,
                code="NOT_FOUND",
                message=f"Task template '{task_code}' does not exist. Import it before assigning.",
            )

        template_fields = {
            "TaskName": template.get("TaskName", ""),
            "Description": template.get("Description"),
            "Sponsor": template.get("Sponsor"),
            "CostCentre": template.get("CostCentre"),
            "CoEResponsible": template.get("CoEResponsible"),
            "Status": template.get("Status", "Open"),
        }

        assigned: list[str] = []
        skipped: list[SkippedAssignment] = []

        seen: set[str] = set()
        for raw_email in emails:
            email = raw_email.strip()
            if not email:
                continue
            if email.lower() in seen:
                continue
            seen.add(email.lower())

            if self._settings.VALIDATE_ASSIGN_EMAILS_WITH_PROFILE_SERVICE:
                result = await validate_user_exists(
                    email=email,
                    bearer_token=bearer_token,
                    base_url=self._settings.PROFILE_SERVICE_BASE_URL,
                    timeout_seconds=self._settings.PROFILE_SERVICE_TIMEOUT_SECONDS,
                )
                if not result.valid:
                    skipped.append(SkippedAssignment(email=email, reason=result.reason or "Validation failed"))
                    continue

            await self._repo.upsert_assignment(email, task_code, template_fields)
            assigned.append(email)

        log_event(
            logger,
            "task_assign",
            user=actor_email,
            task_code=task_code,
            assigned=len(assigned),
            skipped=len(skipped),
        )
        return AssignResponse(assigned=assigned, skipped=skipped)

    # ------------------------------------------------------------------ #
    # DELETE /admin/tasks/{taskCode}/assign/{email}
    # ------------------------------------------------------------------ #
    async def unassign_task(self, *, task_code: str, email: str, actor_email: str) -> None:
        deleted = await self._repo.delete_assignment(email, task_code)
        if not deleted:
            raise AppError(
                status_code=404,
                code="NOT_FOUND",
                message=f"No assignment of task '{task_code}' to '{email}' exists",
            )
        log_event(logger, "task_unassign", user=actor_email, task_code=task_code, employee=email)

    # ------------------------------------------------------------------ #
    # GET /admin/tasks
    # ------------------------------------------------------------------ #
    async def list_all_tasks(
        self,
        *,
        page_size: int,
        continuation_token: str | None,
        search: str | None = None,
        status: str | None = None,
    ):
        if search or status:
            return await self._list_all_tasks_filtered(
                page_size=page_size, continuation_token=continuation_token, search=search, status=status
            )
        entities, next_token = await self._repo.list_all(page_size, continuation_token)
        tasks = [entity_to_task_out(e) for e in entities]
        return tasks, next_token

    async def _list_all_tasks_filtered(
        self, *, page_size: int, continuation_token: str | None, search: str | None, status: str | None
    ):
        """Search/status filters can't be satisfied by the opaque Table-Storage cursor
        used by `list_all` - there's no "contains" OData operator to push the text search
        down, and rows span mixed partitions (templates + per-employee assignment copies).
        So when either filter is active, this fetches the full (optionally status-narrowed)
        result set, filters it in Python, and paginates the filtered list with a synthetic
        `offset:<n>` token instead of the real continuation token.
        """
        entities = await self._repo.list_all_unpaged(status=status)
        tasks = [entity_to_task_out(e) for e in entities]

        if search:
            needle = search.lower()
            tasks = [
                t
                for t in tasks
                if needle in t.taskName.lower()
                or needle in t.taskCode.lower()
                or (t.description is not None and needle in t.description.lower())
            ]

        offset = 0
        if continuation_token and continuation_token.startswith("offset:"):
            try:
                offset = int(continuation_token[len("offset:") :])
            except ValueError:
                offset = 0

        page = tasks[offset : offset + page_size]
        next_offset = offset + page_size
        next_token = f"offset:{next_offset}" if next_offset < len(tasks) else None
        return page, next_token

    # ------------------------------------------------------------------ #
    # PUT /admin/tasks/{taskCode}
    # ------------------------------------------------------------------ #
    async def update_template(self, *, task_code: str, update: TaskUpdateRequest, actor_email: str) -> TaskOut:
        existing = await self._repo.get_template(task_code)
        if existing is None:
            raise AppError(
                status_code=404, code="NOT_FOUND", message=f"Task template '{task_code}' does not exist"
            )

        fields: dict = {}
        if update.taskName is not None:
            fields["TaskName"] = update.taskName
        if update.description is not None:
            fields["Description"] = update.description
        if update.sponsor is not None:
            fields["Sponsor"] = update.sponsor
        if update.costCentre is not None:
            fields["CostCentre"] = update.costCentre
        if update.coeResponsible is not None:
            fields["CoEResponsible"] = update.coeResponsible
        if update.status is not None:
            fields["Status"] = update.status

        entity = await self._repo.upsert_template(task_code, fields)
        log_event(logger, "task_template_update", user=actor_email, task_code=task_code, fields=list(fields.keys()))
        return entity_to_task_out(entity)

    # ------------------------------------------------------------------ #
    # DELETE /admin/tasks/{taskCode}
    # ------------------------------------------------------------------ #
    async def delete_template(self, *, task_code: str, actor_email: str) -> None:
        deleted = await self._repo.delete_template(task_code)
        if not deleted:
            raise AppError(
                status_code=404, code="NOT_FOUND", message=f"Task template '{task_code}' does not exist"
            )
        log_event(logger, "task_template_delete", user=actor_email, task_code=task_code)
