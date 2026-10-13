"""Unit tests: generate() must be idempotent (calling twice does not duplicate rows),
using a fake in-memory repository and fake Task Service client.
"""
from __future__ import annotations

from datetime import date, timedelta

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

    today = date.today()
    week_start = today - timedelta(days=today.weekday())  # Monday of the current week
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


def test_is_future_week() -> None:
    from app.services.timesheet_service import is_future_week

    today = date(2026, 10, 15)  # mid-October

    # A week fully inside the current month.
    assert is_future_week(date(2026, 10, 5), today) is False
    # The current month's broken last week: Monday in October, Sunday spills into November.
    assert is_future_week(date(2026, 10, 26), today) is False
    # A past week.
    assert is_future_week(date(2026, 9, 7), today) is False
    # The first full week of next month: Monday already in November.
    assert is_future_week(date(2026, 11, 2), today) is True


@pytest.mark.asyncio
async def test_submit_week_rejected_for_future_month(assignments: list[dict]) -> None:
    from py_common.core.errors import AppError

    repo = FakeTimesheetRepository()
    task_client = FakeTaskServiceClient(assignments)
    service = TimesheetService(repo, task_client)

    today = date.today()
    # A week comfortably two calendar months out — unambiguously a future month regardless
    # of where `today` falls or how week boundaries snap.
    future_year = today.year + (1 if today.month > 10 else 0)
    future_month = (today.month + 2 - 1) % 12 + 1
    future_week_start = date(future_year, future_month, 15)
    future_week_start -= timedelta(days=future_week_start.weekday())  # snap to Monday

    await service.generate_week(user_id="erin@sandvik.com", week_start=future_week_start, bearer_token="tok")

    with pytest.raises(AppError) as exc_info:
        await service.submit_week(user_id="erin@sandvik.com", week_start=future_week_start)
    assert exc_info.value.status_code == 409
    assert exc_info.value.code == "FUTURE_PERIOD"
