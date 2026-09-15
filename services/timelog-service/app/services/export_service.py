"""Monthly .xlsx export builder for the admin export endpoint.

Builds the entire workbook in memory via openpyxl and streams it — never writes to disk,
never persists to Blob Storage (there is no Blob Storage in this architecture).
"""
from __future__ import annotations

import calendar
import io
import re
from dataclasses import dataclass
from datetime import date

from openpyxl import Workbook
from openpyxl.styles import Font
from openpyxl.utils import get_column_letter

from app.models.entities import TimesheetEntity

_INVALID_SHEET_CHARS = re.compile(r"[\\/*\[\]:?]")
_MAX_SHEET_NAME_LEN = 31


def month_bounds(month: str) -> tuple[date, date, str, str]:
    """Given "YYYY-MM", returns (first_day, last_day, lower_row_key_bound, upper_row_key_bound).

    lower/upper bounds are RowKey prefixes ("YYYY-MM-DD#") suitable for a lexicographic
    `RowKey >= lower and RowKey < upper` Table Storage range query. Handles December ->
    January year rollover and leap-year February correctly.
    """
    year_str, month_str = month.split("-")
    year, mon = int(year_str), int(month_str)
    first_day = date(year, mon, 1)
    days_in_month = calendar.monthrange(year, mon)[1]
    last_day = date(year, mon, days_in_month)

    if mon == 12:
        next_year, next_month = year + 1, 1
    else:
        next_year, next_month = year, mon + 1
    first_of_next_month = date(next_year, next_month, 1)

    lower_bound = f"{first_day.isoformat()}_"
    upper_bound = f"{first_of_next_month.isoformat()}_"
    return first_day, last_day, lower_bound, upper_bound


def previous_calendar_month(today: date) -> str:
    """Returns "YYYY-MM" for the calendar month immediately before `today`'s month."""
    if today.month == 1:
        return f"{today.year - 1}-12"
    return f"{today.year}-{today.month - 1:02d}"


def sanitize_sheet_name(email: str, used_names: set[str]) -> str:
    """Sanitizes an employee email into a valid, unique Excel sheet name (<=31 chars,
    no \\/*[]:? characters).
    """
    name = _INVALID_SHEET_CHARS.sub("_", email)[:_MAX_SHEET_NAME_LEN]
    if not name:
        name = "sheet"
    base = name
    suffix = 1
    while name in used_names:
        suffix_str = f"~{suffix}"
        name = base[: _MAX_SHEET_NAME_LEN - len(suffix_str)] + suffix_str
        suffix += 1
    used_names.add(name)
    return name


@dataclass
class EmployeeMonthData:
    email: str
    entries: list[TimesheetEntity]


def _build_summary_sheet(
    wb: Workbook,
    employees: list[EmployeeMonthData],
    day_numbers: list[int],
) -> None:
    """Adds a "Summary" sheet: one row per active employee, columns = total hours logged
    per day of the month, plus a final cumulative-total-for-the-month column.
    """
    ws = wb.create_sheet(title="Summary", index=0)
    bold = Font(bold=True)

    ws.cell(row=1, column=1, value="Employee").font = bold
    for i, day_num in enumerate(day_numbers):
        ws.cell(row=1, column=2 + i, value=day_num).font = bold
    total_col = 2 + len(day_numbers)
    ws.cell(row=1, column=total_col, value="Total").font = bold

    sorted_employees = sorted(employees, key=lambda e: e.email.lower())
    column_totals = [0.0] * len(day_numbers)
    current_row = 2
    for emp in sorted_employees:
        daily_hours: dict[int, float] = {}
        for e in emp.entries:
            daily_hours[e.entry_date.day] = daily_hours.get(e.entry_date.day, 0.0) + e.hours_logged

        ws.cell(row=current_row, column=1, value=emp.email)
        row_total = 0.0
        for i, day_num in enumerate(day_numbers):
            hours = round(daily_hours.get(day_num, 0.0), 2)
            ws.cell(row=current_row, column=2 + i, value=hours)
            row_total += hours
            column_totals[i] += hours
        ws.cell(row=current_row, column=total_col, value=round(row_total, 2))
        current_row += 1

    # Grand total row across all employees.
    ws.cell(row=current_row, column=1, value="Grand Total").font = bold
    for i, col_total in enumerate(column_totals):
        ws.cell(row=current_row, column=2 + i, value=round(col_total, 2)).font = bold
    ws.cell(row=current_row, column=total_col, value=round(sum(column_totals), 2)).font = bold

    ws.column_dimensions[get_column_letter(1)].width = 28
    for i in range(len(day_numbers) + 1):
        ws.column_dimensions[get_column_letter(2 + i)].width = 8


def build_monthly_workbook(
    month: str,
    employees: list[EmployeeMonthData],
) -> bytes:
    """Builds a "Summary" sheet (rows = active employees, columns = total hours logged per
    day of the month plus a monthly cumulative total) followed by one sheet per employee
    (including zero-hour employees), rows = distinct tasks logged that month (or a "No
    entries" placeholder row), columns = days of the month, plus weekly subtotal rows and a
    monthly grand total row. Returns the .xlsx file bytes.
    """
    first_day, last_day, _, _ = month_bounds(month)
    days_in_month = last_day.day
    day_numbers = list(range(1, days_in_month + 1))

    wb = Workbook()
    # Remove the default sheet created by Workbook(); we add one per employee explicitly.
    default_sheet = wb.active
    wb.remove(default_sheet)

    _build_summary_sheet(wb, employees, day_numbers)

    used_names: set[str] = set()

    for emp in sorted(employees, key=lambda e: e.email.lower()):
        sheet_name = sanitize_sheet_name(emp.email, used_names)
        ws = wb.create_sheet(title=sheet_name)

        bold = Font(bold=True)

        # Header row: Task | Day 1 | Day 2 | ... | Day N | Total
        ws.cell(row=1, column=1, value="Task").font = bold
        for i, day_num in enumerate(day_numbers):
            ws.cell(row=1, column=2 + i, value=day_num).font = bold
        total_col = 2 + len(day_numbers)
        ws.cell(row=1, column=total_col, value="Total").font = bold

        # Distinct tasks logged this month, in stable order of first appearance.
        distinct_tasks: dict[str, str] = {}
        for e in emp.entries:
            if e.task_code not in distinct_tasks:
                distinct_tasks[e.task_code] = e.task_name or e.task_code

        current_row = 2

        if not distinct_tasks:
            ws.cell(row=current_row, column=1, value="No entries")
            for i in range(len(day_numbers)):
                ws.cell(row=current_row, column=2 + i, value=0)
            ws.cell(row=current_row, column=total_col, value=0)
            current_row += 1
        else:
            # hours_by_task[task_code][day_of_month] = hours
            hours_by_task: dict[str, dict[int, float]] = {code: {} for code in distinct_tasks}
            for e in emp.entries:
                hours_by_task[e.task_code][e.entry_date.day] = (
                    hours_by_task[e.task_code].get(e.entry_date.day, 0.0) + e.hours_logged
                )

            task_row_map: dict[str, int] = {}
            for task_code, task_name in distinct_tasks.items():
                ws.cell(row=current_row, column=1, value=task_name)
                row_total = 0.0
                for i, day_num in enumerate(day_numbers):
                    hours = hours_by_task[task_code].get(day_num, 0.0)
                    ws.cell(row=current_row, column=2 + i, value=hours)
                    row_total += hours
                ws.cell(row=current_row, column=total_col, value=round(row_total, 2))
                task_row_map[task_code] = current_row
                current_row += 1

            # Weekly subtotal rows: one per Mon-Sun week overlapping the month.
            first_weekday = first_day.weekday()  # Monday=0
            week_starts_days = list(range(1 - first_weekday, days_in_month + 1, 7))
            for week_start_day in week_starts_days:
                week_days = [d for d in range(week_start_day, week_start_day + 7) if 1 <= d <= days_in_month]
                if not week_days:
                    continue
                label = f"Week subtotal ({week_days[0]}-{week_days[-1]})"
                ws.cell(row=current_row, column=1, value=label).font = bold
                week_total = 0.0
                for i, day_num in enumerate(day_numbers):
                    if day_num in week_days:
                        col_total = sum(hours_by_task[code].get(day_num, 0.0) for code in distinct_tasks)
                        ws.cell(row=current_row, column=2 + i, value=round(col_total, 2)).font = bold
                        week_total += col_total
                ws.cell(row=current_row, column=total_col, value=round(week_total, 2)).font = bold
                current_row += 1

        # Monthly grand total row.
        ws.cell(row=current_row, column=1, value="Grand Total").font = bold
        grand_total = 0.0
        for i, day_num in enumerate(day_numbers):
            if distinct_tasks:
                col_total = sum(hours_by_task[code].get(day_num, 0.0) for code in distinct_tasks)
            else:
                col_total = 0.0
            ws.cell(row=current_row, column=2 + i, value=round(col_total, 2)).font = bold
            grand_total += col_total
        ws.cell(row=current_row, column=total_col, value=round(grand_total, 2)).font = bold

        # Reasonable column widths.
        ws.column_dimensions[get_column_letter(1)].width = 28
        for i in range(len(day_numbers) + 1):
            ws.column_dimensions[get_column_letter(2 + i)].width = 8

    buffer = io.BytesIO()
    wb.save(buffer)
    return buffer.getvalue()
