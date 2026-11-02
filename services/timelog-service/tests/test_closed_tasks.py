"""Closed tasks are kept off time cards; rows already on a sheet stay editable."""
from __future__ import annotations

from datetime import date

import pytest
from py_common.core.errors import AppError

from app.models.schemas import EntryIn
from app.services.timesheet_service import TimesheetService
from tests.fakes import FakeTaskServiceClient, FakeTimesheetRepository

USER = "alice@sandvik.com"
WEEK = date(2026, 9, 7)  # a Monday
OPEN = {"taskCode": "TASK-A", "taskName": "Task A", "status": "Open"}
CLOSED = {"taskCode": "TASK-C", "taskName": "Task C", "status": "Closed"}


@pytest.mark.asyncio
async def test_generate_skips_closed_tasks() -> None:
    repo = FakeTimesheetRepository()
    service = TimesheetService(repo, FakeTaskServiceClient([OPEN, CLOSED]))
    await service.generate_week(user_id=USER, week_start=WEEK, bearer_token="t")

    assert {e.task_code for e in repo.all_entries()} == {"TASK-A"}
    # The standard 9h day goes entirely to the one open task.
    assert {e.hours_logged for e in repo.all_entries() if e.entry_date.weekday() < 5} == {9.0}


@pytest.mark.asyncio
async def test_new_entries_for_closed_task_rejected() -> None:
    service = TimesheetService(FakeTimesheetRepository(), FakeTaskServiceClient([OPEN, CLOSED]))
    with pytest.raises(AppError) as exc:
        await service.upsert_entries(
            user_id=USER,
            week_start=WEEK,
            entries=[EntryIn(taskCode="TASK-C", entryDate=WEEK, hours=2)],
            is_admin=False,
            bearer_token="t",
        )
    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_existing_entries_for_task_closed_later_stay_editable() -> None:
    repo = FakeTimesheetRepository()
    await TimesheetService(repo, FakeTaskServiceClient([OPEN])).generate_week(
        user_id=USER, week_start=WEEK, bearer_token="t"
    )

    # Same rows, but the task is now Closed in the employee's assignments.
    closed_service = TimesheetService(repo, FakeTaskServiceClient([{**OPEN, "status": "Closed"}]))
    saved = await closed_service.upsert_entries(
        user_id=USER,
        week_start=WEEK,
        entries=[EntryIn(taskCode="TASK-A", entryDate=WEEK, hours=3)],
        is_admin=False,
        bearer_token="t",
    )
    assert saved == 1


@pytest.mark.asyncio
async def test_regenerate_does_not_add_a_task_closed_since() -> None:
    repo = FakeTimesheetRepository()
    await TimesheetService(repo, FakeTaskServiceClient([OPEN])).generate_week(
        user_id=USER, week_start=WEEK, bearer_token="t"
    )
    service = TimesheetService(repo, FakeTaskServiceClient([OPEN, CLOSED]))
    assert await service.generate_week(user_id=USER, week_start=WEEK, bearer_token="t") == 0
