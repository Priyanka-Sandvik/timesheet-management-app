"""Unit tests: RowKey range-bound computation for monthly export, including leap-year
February and December -> January year rollover.
"""
from __future__ import annotations

from datetime import date

from app.services.export_service import month_bounds, previous_calendar_month


def test_month_bounds_regular_month() -> None:
    first_day, last_day, lower, upper = month_bounds("2026-08")
    assert first_day == date(2026, 8, 1)
    assert last_day == date(2026, 8, 31)
    assert lower == "2026-08-01_"
    assert upper == "2026-09-01_"


def test_month_bounds_leap_year_february() -> None:
    first_day, last_day, lower, upper = month_bounds("2024-02")
    assert first_day == date(2024, 2, 1)
    assert last_day == date(2024, 2, 29)  # 2024 is a leap year
    assert lower == "2024-02-01_"
    assert upper == "2024-03-01_"


def test_month_bounds_non_leap_year_february() -> None:
    _, last_day, _, _ = month_bounds("2026-02")
    assert last_day == date(2026, 2, 28)


def test_month_bounds_december_rolls_over_to_next_january() -> None:
    first_day, last_day, lower, upper = month_bounds("2026-12")
    assert first_day == date(2026, 12, 1)
    assert last_day == date(2026, 12, 31)
    assert lower == "2026-12-01_"
    assert upper == "2027-01-01_"  # year rollover


def test_row_key_range_bounds_are_lexicographically_correct() -> None:
    """Verify the RowKey range query semantics: a row on the last day of the month falls
    within [lower, upper), and a row on the first day of the next month does not.
    """
    _, _, lower, upper = month_bounds("2026-08")
    last_day_row_key = "2026-08-31_TASK-1"
    first_of_next_month_row_key = "2026-09-01_TASK-1"

    assert lower <= last_day_row_key < upper
    assert not (lower <= first_of_next_month_row_key < upper)


def test_previous_calendar_month_regular() -> None:
    assert previous_calendar_month(date(2026, 9, 12)) == "2026-08"


def test_previous_calendar_month_january_rolls_back_to_prior_december() -> None:
    assert previous_calendar_month(date(2026, 1, 15)) == "2025-12"
