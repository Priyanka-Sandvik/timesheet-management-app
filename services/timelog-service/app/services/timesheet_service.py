"""Business logic for the employee-facing timesheet endpoints (grid, entries, generate,
copy-previous, submit). Week math is always Mon-Sun.
"""
from __future__ import annotations

from datetime import date, timedelta

from py_common.core.errors import AppError

from app.models.entities import STATUS_PENDING, STATUS_SUBMITTED, TimesheetEntity, utcnow
from app.models.schemas import EntryIn, EntryOut, TimesheetGridResponse
from app.repositories.timesheet_repository import TimesheetRepository
from app.services.task_client import TaskServiceClient


def week_end(week_start: date) -> date:
    """Given the Monday of a week, returns that week's Sunday."""
    return week_start + timedelta(days=6)


def week_dates(week_start: date) -> list[date]:
    """Mon..Sun inclusive list of dates for the week starting on `week_start`."""
    return [week_start + timedelta(days=i) for i in range(7)]


def normalize_week_start(week_start: date) -> date:
    """Normalizes any date to the Monday of its week (defensive — callers are expected to
    already pass a Monday, but this guards against off-by-one query params).
    """
    return week_start - timedelta(days=week_start.weekday())


STANDARD_WORKDAY_HOURS = 9.0
_HOUR_INCREMENT = 0.25


def _split_hours_evenly(total_hours: float, n: int) -> list[float]:
    """Splits `total_hours` across `n` tasks in `_HOUR_INCREMENT` steps, as evenly as
    possible, so the values sum back to exactly `total_hours` (any leftover quarter-hours
    go to the first tasks). Returns an empty list if `n == 0`.
    """
    if n == 0:
        return []
    total_units = round(total_hours / _HOUR_INCREMENT)
    base_units, remainder = divmod(total_units, n)
    return [(base_units + (1 if i < remainder else 0)) * _HOUR_INCREMENT for i in range(n)]


class TimesheetService:
    def __init__(self, repository: TimesheetRepository, task_client: TaskServiceClient) -> None:
        self._repository = repository
        self._task_client = task_client

    async def get_week_grid(self, user_id: str, week_start: date) -> TimesheetGridResponse:
        week_start = normalize_week_start(week_start)
        w_end = week_end(week_start)
        entities = await self._repository.get_week_entries(user_id, week_start, w_end)

        entries = [
            EntryOut(
                taskCode=e.task_code,
                taskName=e.task_name,
                projectName=e.project_name,
                entryDate=e.entry_date,
                hours=e.hours_logged,
                notes=e.notes,
                status=e.status,
            )
            for e in entities
        ]

        daily_totals: dict[str, float] = {d.isoformat(): 0.0 for d in week_dates(week_start)}
        for e in entities:
            key = e.entry_date.isoformat()
            daily_totals[key] = round(daily_totals.get(key, 0.0) + e.hours_logged, 2)

        weekly_total = round(sum(daily_totals.values()), 2)

        # Week status: Submitted if ANY row for the week is Submitted (rows are created/
        # transitioned together by submit()), otherwise Pending.
        week_status = STATUS_SUBMITTED if any(e.status == STATUS_SUBMITTED for e in entities) else STATUS_PENDING

        return TimesheetGridResponse(
            weekStart=week_start,
            weekEnd=w_end,
            status=week_status,
            entries=entries,
            dailyTotals=daily_totals,
            weeklyTotal=weekly_total,
        )

    async def _assert_not_locked(self, user_id: str, week_start: date, is_admin: bool) -> None:
        if is_admin:
            return
        w_end = week_end(week_start)
        entities = await self._repository.get_week_entries(user_id, week_start, w_end)
        if any(e.status == STATUS_SUBMITTED for e in entities):
            raise AppError(
                status_code=409,
                code="CONFLICT",
                message="This week has already been submitted and can no longer be edited",
            )

    async def upsert_entries(
        self,
        *,
        user_id: str,
        week_start: date,
        entries: list[EntryIn],
        is_admin: bool,
        bearer_token: str,
    ) -> int:
        week_start = normalize_week_start(week_start)
        await self._assert_not_locked(user_id, week_start, is_admin)

        assignments = await self._task_client.get_my_tasks(bearer_token)
        assigned_codes = {a.task_code for a in assignments}
        assignment_by_code = {a.task_code: a for a in assignments}

        invalid = [e.taskCode for e in entries if e.taskCode not in assigned_codes]
        if invalid:
            raise AppError(
                status_code=422,
                code="VALIDATION_ERROR",
                message="One or more tasks are not active assignments for this user",
                details=[{"field": "taskCode", "issue": f"Not an active assignment: {code}"} for code in invalid],
            )

        now = utcnow()
        to_save: list[TimesheetEntity] = []
        for entry in entries:
            existing = await self._repository.get_entry(user_id, entry.entryDate, entry.taskCode)
            assignment = assignment_by_code.get(entry.taskCode, {})
            to_save.append(
                TimesheetEntity(
                    user_id=user_id,
                    entry_date=entry.entryDate,
                    task_code=entry.taskCode,
                    task_name=assignment.get("taskName") if assignment else (existing.task_name if existing else None),
                    project_name=assignment.get("projectName") if assignment else (existing.project_name if existing else None),
                    week_start_date=week_start,
                    hours_logged=entry.hours,
                    notes=entry.notes,
                    status=existing.status if existing else STATUS_PENDING,
                    created_at=existing.created_at if existing else now,
                    updated_at=now,
                )
            )

        await self._repository.upsert_entries(to_save)
        return len(to_save)

    async def generate_week(self, *, user_id: str, week_start: date, bearer_token: str) -> int:
        week_start = normalize_week_start(week_start)
        assignments = await self._task_client.get_my_tasks(bearer_token)
        w_end = week_end(week_start)
        existing_entities = await self._repository.get_week_entries(user_id, week_start, w_end)
        existing_keys = {(e.entry_date, e.task_code) for e in existing_entities}

        # Default hours: a standard workday (9h, Mon-Fri) is split evenly, in 0.25-hour
        # increments, across that day's assigned tasks. Weekends have no standard workday
        # and default to 0h, left for the employee to fill in if they choose to.
        default_hours_by_task = _split_hours_evenly(STANDARD_WORKDAY_HOURS, len(assignments))

        now = utcnow()
        to_create: list[TimesheetEntity] = []
        for d in week_dates(week_start):
            is_weekday = d.weekday() < 5  # Monday=0 .. Sunday=6
            for i, assignment in enumerate(assignments):
                key = (d, assignment.task_code)
                if key in existing_keys:
                    continue
                to_create.append(
                    TimesheetEntity(
                        user_id=user_id,
                        entry_date=d,
                        task_code=assignment.task_code,
                        task_name=assignment.task_name,
                        project_name=assignment.project_name,
                        week_start_date=week_start,
                        hours_logged=default_hours_by_task[i] if is_weekday else 0.0,
                        notes=None,
                        status=STATUS_PENDING,
                        created_at=now,
                        updated_at=now,
                    )
                )
                existing_keys.add(key)

        await self._repository.upsert_entries(to_create)
        return len(to_create)

    async def copy_previous_week(self, *, user_id: str, week_start: date) -> int:
        week_start = normalize_week_start(week_start)
        prev_week_start = week_start - timedelta(days=7)
        prev_week_end = week_end(prev_week_start)

        prev_entities = await self._repository.get_week_entries(user_id, prev_week_start, prev_week_end)
        distinct_tasks: dict[str, tuple[str | None, str | None]] = {}
        for e in prev_entities:
            distinct_tasks.setdefault(e.task_code, (e.task_name, e.project_name))

        if not distinct_tasks:
            return 0

        cur_week_end = week_end(week_start)
        cur_entities = await self._repository.get_week_entries(user_id, week_start, cur_week_end)
        existing_keys = {(e.entry_date, e.task_code) for e in cur_entities}

        now = utcnow()
        to_create: list[TimesheetEntity] = []
        for d in week_dates(week_start):
            for task_code, (task_name, project_name) in distinct_tasks.items():
                key = (d, task_code)
                if key in existing_keys:
                    continue
                to_create.append(
                    TimesheetEntity(
                        user_id=user_id,
                        entry_date=d,
                        task_code=task_code,
                        task_name=task_name,
                        project_name=project_name,
                        week_start_date=week_start,
                        hours_logged=0.0,
                        notes=None,
                        status=STATUS_PENDING,
                        created_at=now,
                        updated_at=now,
                    )
                )
                existing_keys.add(key)

        await self._repository.upsert_entries(to_create)
        return len(to_create)

    async def submit_week(self, *, user_id: str, week_start: date) -> str:
        week_start = normalize_week_start(week_start)
        w_end = week_end(week_start)
        entities = await self._repository.get_week_entries(user_id, week_start, w_end)
        if not entities:
            raise AppError(
                status_code=404,
                code="NOT_FOUND",
                message="No timesheet entries found for this week to submit",
            )

        now = utcnow()
        for e in entities:
            e.status = STATUS_SUBMITTED
            e.updated_at = now
        await self._repository.upsert_entries(entities)
        return STATUS_SUBMITTED
