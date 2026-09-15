"""Unit tests: generate_week() pre-fills a standard 9h workday (Mon-Fri), split evenly
across that day's assigned tasks in 0.25-hour increments, and defaults weekends to 0h.
"""
from __future__ import annotations

from datetime import date

import pytest

from app.services.timesheet_service import TimesheetService, _split_hours_evenly
from tests.fakes import FakeTaskServiceClient, FakeTimesheetRepository


def test_split_hours_evenly_divides_cleanly() -> None:
    assert _split_hours_evenly(9.0, 2) == [4.5, 4.5]
    assert _split_hours_evenly(9.0, 3) == [3.0, 3.0, 3.0]
    assert _split_hours_evenly(9.0, 4) == [2.25, 2.25, 2.25, 2.25]


def test_split_hours_evenly_distributes_remainder_to_first_tasks() -> None:
    # 9.0h = 36 quarter-hours / 5 tasks = 7 quarters (1.75h) each, remainder 1 quarter,
    # which goes to the first task (2.0h) so the total still sums to exactly 9.0.
    result = _split_hours_evenly(9.0, 5)
    assert result == [2.0, 1.75, 1.75, 1.75, 1.75]
    assert sum(result) == 9.0


def test_split_hours_evenly_empty_when_no_tasks() -> None:
    assert _split_hours_evenly(9.0, 0) == []


@pytest.mark.asyncio
async def test_generate_week_defaults_weekdays_to_split_9h_and_weekends_to_0h() -> None:
    assignments = [
        {"taskCode": "TASK-A", "taskName": "Task A", "projectName": "Project X"},
        {"taskCode": "TASK-B", "taskName": "Task B", "projectName": "Project Y"},
    ]
    repo = FakeTimesheetRepository()
    task_client = FakeTaskServiceClient(assignments)
    service = TimesheetService(repo, task_client)

    week_start = date(2026, 9, 7)  # a Monday
    week_end = date(2026, 9, 13)  # the following Sunday

    created = await service.generate_week(user_id="alice@sandvik.com", week_start=week_start, bearer_token="tok")
    assert created == 14  # 7 days * 2 tasks

    entries = await repo.get_week_entries("alice@sandvik.com", week_start, week_end)
    by_date_and_task = {(e.entry_date, e.task_code): e.hours_logged for e in entries}

    for offset in range(5):  # Mon..Fri
        d = date(2026, 9, 7 + offset)
        assert by_date_and_task[(d, "TASK-A")] == 4.5
        assert by_date_and_task[(d, "TASK-B")] == 4.5

    for offset in (5, 6):  # Sat, Sun
        d = date(2026, 9, 7 + offset)
        assert by_date_and_task[(d, "TASK-A")] == 0.0
        assert by_date_and_task[(d, "TASK-B")] == 0.0
