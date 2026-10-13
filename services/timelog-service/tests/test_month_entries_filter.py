"""Unit test: the monthly admin export must only include Submitted rows."""
from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from app.models.entities import TimesheetEntity
from tests.fakes import FakeTimesheetRepository


def _entity(entry_date: date, task_code: str, status: str) -> TimesheetEntity:
    now = datetime.now(timezone.utc)
    return TimesheetEntity(
        user_id="alice@sandvik.com",
        entry_date=entry_date,
        task_code=task_code,
        task_name=f"{task_code} name",
        project_name="Project Z",
        week_start_date=entry_date,
        hours_logged=4.0,
        notes=None,
        status=status,
        created_at=now,
        updated_at=now,
    )


@pytest.mark.asyncio
async def test_get_month_entries_excludes_non_submitted_rows() -> None:
    repo = FakeTimesheetRepository()
    await repo.upsert_entries(
        [
            _entity(date(2026, 8, 3), "TASK-A", "Submitted"),
            _entity(date(2026, 8, 4), "TASK-B", "Pending"),
        ]
    )

    results = await repo.get_month_entries("alice@sandvik.com", "2026-08-01_", "2026-09-01_")

    assert len(results) == 1
    assert results[0].task_code == "TASK-A"
    assert results[0].status == "Submitted"


@pytest.mark.asyncio
async def test_get_month_entries_all_statuses_includes_pending_rows() -> None:
    repo = FakeTimesheetRepository()
    await repo.upsert_entries(
        [
            _entity(date(2026, 8, 3), "TASK-A", "Submitted"),
            _entity(date(2026, 8, 4), "TASK-B", "Pending"),
        ]
    )

    results = await repo.get_month_entries_all_statuses("alice@sandvik.com", "2026-08-01_", "2026-09-01_")

    assert {r.task_code for r in results} == {"TASK-A", "TASK-B"}
