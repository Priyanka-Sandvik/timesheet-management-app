"""Removing a task from a time sheet deletes that week's rows only."""
from __future__ import annotations

from datetime import date

import pytest
from py_common.core.errors import AppError

from app.services.timesheet_service import TimesheetService
from tests.fakes import FakeTaskServiceClient, FakeTimesheetRepository

USER = "alice@sandvik.com"
WEEK1 = date(2026, 9, 7)  # Mondays
WEEK2 = date(2026, 9, 14)
ASSIGNMENTS = [
    {"taskCode": "TASK-A", "taskName": "Task A"},
    {"taskCode": "TASK-B", "taskName": "Task B"},
]


def _service():
    repo = FakeTimesheetRepository()
    return TimesheetService(repo, FakeTaskServiceClient(ASSIGNMENTS)), repo


@pytest.mark.asyncio
async def test_remove_task_from_week_leaves_other_weeks_and_tasks() -> None:
    service, repo = _service()
    for week in (WEEK1, WEEK2):
        await service.generate_week(user_id=USER, week_start=week, bearer_token="t")

    deleted = await service.remove_task_from_week(
        user_id=USER, week_start=WEEK1, task_code="TASK-A", is_admin=False
    )
    assert deleted == 7

    remaining = {(e.week_start_date, e.task_code) for e in repo.all_entries()}
    assert (WEEK1, "TASK-A") not in remaining
    assert (WEEK1, "TASK-B") in remaining
    assert (WEEK2, "TASK-A") in remaining


@pytest.mark.asyncio
async def test_remove_task_from_submitted_week_rejected_for_employee() -> None:
    service, _ = _service()
    await service.generate_week(user_id=USER, week_start=WEEK1, bearer_token="t")
    await service.submit_week(user_id=USER, week_start=WEEK1)
    with pytest.raises(AppError) as exc:
        await service.remove_task_from_week(user_id=USER, week_start=WEEK1, task_code="TASK-A", is_admin=False)
    assert exc.value.status_code == 409
