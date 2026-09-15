"""Unit tests for hour validation (0-24 inclusive, exact 0.25 increments)."""
from __future__ import annotations

from datetime import date

import pytest
from pydantic import ValidationError

from app.models.schemas import EntryIn


def _make_entry(hours: float) -> EntryIn:
    return EntryIn(taskCode="TASK-1", entryDate=date(2026, 8, 3), hours=hours)


@pytest.mark.parametrize("hours", [0.0, 0.25, 1.25, 1.5, 8.0, 23.75, 24.0])
def test_accepts_valid_quarter_hour_increments(hours: float) -> None:
    entry = _make_entry(hours)
    assert entry.hours == hours


@pytest.mark.parametrize("hours", [1.3, 0.1, 5.6, 24.1, -0.25, -1.0, 24.5, 100.0])
def test_rejects_invalid_hours(hours: float) -> None:
    with pytest.raises(ValidationError):
        _make_entry(hours)


def test_rejects_negative_hours() -> None:
    with pytest.raises(ValidationError):
        _make_entry(-0.25)


def test_rejects_over_24_hours() -> None:
    with pytest.raises(ValidationError):
        _make_entry(24.25)
