"""Unit tests: generate() and copy-previous() must be idempotent (calling twice does not
duplicate rows), using a fake in-memory repository and fake Task Service client.
"""
from __future__ import annotations

from datetime import date

import pytest

from app.services.timesheet_service import TimesheetService
from tests.fakes import FakeTaskServiceClient, FakeTimesheetRepository


@pytest.fixture
def assignments() -> list[dict]:
    return [
        {"taskCode": "TASK-A", "taskName": "Task A", "projectName": "Project X"},
        {"taskCode": "TASK-B", "taskName": "Task B", "projectName": "Project Y"},
    ]


@pytest.mark.asyncio
async def test_generate_week_is_idempotent(assignments: list[dict]) -> None:
    repo = FakeTimesheetRepository()
    task_client = FakeTaskServiceClient(assignments)
    service = TimesheetService(repo, task_client)

    week_start = date(2026, 8, 3)  # a Monday

    first = await service.generate_week(user_id="alice@sandvik.com", week_start=week_start, bearer_token="tok")
    assert first == 7 * 2  # 7 days * 2 tasks

    second = await service.generate_week(user_id="alice@sandvik.com", week_start=week_start, bearer_token="tok")
    assert second == 0  # no new rows created

    all_entries = repo.all_entries()
    assert len(all_entries) == 14


@pytest.mark.asyncio
async def test_copy_previous_week_is_idempotent(assignments: list[dict]) -> None:
    repo = FakeTimesheetRepository()
    task_client = FakeTaskServiceClient(assignments)
    service = TimesheetService(repo, task_client)

    prev_week_start = date(2026, 7, 27)  # Monday
    cur_week_start = date(2026, 8, 3)  # following Monday

    await service.generate_week(user_id="bob@sandvik.com", week_start=prev_week_start, bearer_token="tok")

    first = await service.copy_previous_week(user_id="bob@sandvik.com", week_start=cur_week_start)
    assert first == 14  # 7 days * 2 distinct tasks, hours reset to 0

    second = await service.copy_previous_week(user_id="bob@sandvik.com", week_start=cur_week_start)
    assert second == 0  # already exist, not duplicated

    current_week_entries = await repo.get_week_entries(
        "bob@sandvik.com", cur_week_start, date(2026, 8, 9)
    )
    assert len(current_week_entries) == 14
    assert all(e.hours_logged == 0.0 for e in current_week_entries)


@pytest.mark.asyncio
async def test_copy_previous_week_with_no_prior_entries_copies_nothing() -> None:
    repo = FakeTimesheetRepository()
    task_client = FakeTaskServiceClient([])
    service = TimesheetService(repo, task_client)

    copied = await service.copy_previous_week(user_id="carol@sandvik.com", week_start=date(2026, 8, 3))
    assert copied == 0


@pytest.mark.asyncio
async def test_upsert_entries_rejects_unassigned_task(assignments: list[dict]) -> None:
    from app.models.schemas import EntryIn
    from py_common.core.errors import AppError

    repo = FakeTimesheetRepository()
    task_client = FakeTaskServiceClient(assignments)
    service = TimesheetService(repo, task_client)

    entries = [EntryIn(taskCode="NOT-ASSIGNED", entryDate=date(2026, 8, 3), hours=4.0)]

    with pytest.raises(AppError) as exc_info:
        await service.upsert_entries(
            user_id="alice@sandvik.com",
            week_start=date(2026, 8, 3),
            entries=entries,
            is_admin=False,
            bearer_token="tok",
        )
    assert exc_info.value.status_code == 422


@pytest.mark.asyncio
async def test_submitted_week_locks_edits_for_non_admin(assignments: list[dict]) -> None:
    from app.models.schemas import EntryIn
    from py_common.core.errors import AppError

    repo = FakeTimesheetRepository()
    task_client = FakeTaskServiceClient(assignments)
    service = TimesheetService(repo, task_client)

    week_start = date(2026, 8, 3)
    await service.generate_week(user_id="dave@sandvik.com", week_start=week_start, bearer_token="tok")
    await service.submit_week(user_id="dave@sandvik.com", week_start=week_start)

    entries = [EntryIn(taskCode="TASK-A", entryDate=week_start, hours=4.0)]

    with pytest.raises(AppError) as exc_info:
        await service.upsert_entries(
            user_id="dave@sandvik.com",
            week_start=week_start,
            entries=entries,
            is_admin=False,
            bearer_token="tok",
        )
    assert exc_info.value.status_code == 409

    # Admin override: same edit succeeds when is_admin=True.
    saved = await service.upsert_entries(
        user_id="dave@sandvik.com",
        week_start=week_start,
        entries=entries,
        is_admin=True,
        bearer_token="tok",
    )
    assert saved == 1
