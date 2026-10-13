"""Unit tests for admin-driven weekly status review and toggling."""
from __future__ import annotations

from datetime import date, timedelta

import pytest
from py_common.core.errors import AppError

from app.models.schemas import EntryIn
from app.services.timesheet_service import TimesheetService
from tests.fakes import FakeTaskServiceClient, FakeTimesheetRepository


@pytest.fixture
def assignments() -> list[dict]:
    return [{"taskCode": "TASK-A", "taskName": "Task A", "projectName": "Project X"}]


@pytest.mark.asyncio
async def test_get_period_statuses_derives_week_status_per_employee(assignments: list[dict]) -> None:
    repo = FakeTimesheetRepository()
    task_client = FakeTaskServiceClient(assignments)
    service = TimesheetService(repo, task_client)

    week_start = date(2026, 8, 3)  # a Monday in August 2026
    await service.generate_week(user_id="alice@sandvik.com", week_start=week_start, bearer_token="tok")
    await service.submit_week(user_id="alice@sandvik.com", week_start=week_start)
    await service.generate_week(user_id="bob@sandvik.com", week_start=week_start, bearer_token="tok")

    results = await service.get_period_statuses(["alice@sandvik.com", "bob@sandvik.com"], "2026-08")

    by_user = {r.userId: r.status for r in results}
    assert by_user["alice@sandvik.com"] == "Submitted"
    assert by_user["bob@sandvik.com"] == "Pending"


@pytest.mark.asyncio
async def test_set_week_status_submitted_to_pending_unlocks_edits(assignments: list[dict]) -> None:
    repo = FakeTimesheetRepository()
    task_client = FakeTaskServiceClient(assignments)
    service = TimesheetService(repo, task_client)

    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    await service.generate_week(user_id="dave@sandvik.com", week_start=week_start, bearer_token="tok")
    await service.submit_week(user_id="dave@sandvik.com", week_start=week_start)

    new_status = await service.set_week_status(user_id="dave@sandvik.com", week_start=week_start, new_status="Pending")
    assert new_status == "Pending"

    entries = [EntryIn(taskCode="TASK-A", entryDate=week_start, hours=4.0)]
    saved = await service.upsert_entries(
        user_id="dave@sandvik.com",
        week_start=week_start,
        entries=entries,
        is_admin=False,
        bearer_token="tok",
    )
    assert saved == 1


@pytest.mark.asyncio
async def test_set_week_status_pending_to_submitted_locks_edits(assignments: list[dict]) -> None:
    repo = FakeTimesheetRepository()
    task_client = FakeTaskServiceClient(assignments)
    service = TimesheetService(repo, task_client)

    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    await service.generate_week(user_id="erin@sandvik.com", week_start=week_start, bearer_token="tok")

    await service.set_week_status(user_id="erin@sandvik.com", week_start=week_start, new_status="Submitted")

    entries = [EntryIn(taskCode="TASK-A", entryDate=week_start, hours=4.0)]
    with pytest.raises(AppError) as exc_info:
        await service.upsert_entries(
            user_id="erin@sandvik.com",
            week_start=week_start,
            entries=entries,
            is_admin=False,
            bearer_token="tok",
        )
    assert exc_info.value.status_code == 409


@pytest.mark.asyncio
async def test_set_week_status_raises_404_when_no_entries_exist() -> None:
    repo = FakeTimesheetRepository()
    task_client = FakeTaskServiceClient([])
    service = TimesheetService(repo, task_client)

    with pytest.raises(AppError) as exc_info:
        await service.set_week_status(user_id="nobody@sandvik.com", week_start=date(2026, 8, 3), new_status="Submitted")
    assert exc_info.value.status_code == 404
