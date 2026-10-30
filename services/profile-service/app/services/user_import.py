"""CSV/XLSX parsing + validation for POST /admin/users/import.

Rules:
- Columns: Name and Email (required), Start Date, End Date, Vendor, Vendor Email, Vendor
  Phone, Vendor Rate, Sandvik Rate (all optional - the column may be absent or its cells
  blank). Header row required. Unknown extra columns are ignored.
- A missing Name or Email COLUMN fails the whole import. Per-row problems (blank name or
  email, malformed email, unparseable date, end date before start date, non-numeric or
  negative rate, duplicate email within the file) are reported per row and that row is
  skipped; the other rows still import.
- .csv is parsed with the stdlib `csv` module; .xlsx with `openpyxl` (read-only, in memory).
"""
from __future__ import annotations

import csv
import io
import math
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

from openpyxl import load_workbook
from pydantic import EmailStr, TypeAdapter, ValidationError
from py_common.core.errors import AppError

from app.models.schemas import UserImportRowError

REQUIRED_COLUMNS = ("Name", "Email")

HEADER_ALIASES: dict[str, str] = {
    "name": "Name",
    "full name": "Name",
    "fullname": "Name",
    "email": "Email",
    "e-mail": "Email",
    "start date": "StartDate",
    "startdate": "StartDate",
    "end date": "EndDate",
    "enddate": "EndDate",
    "vendor": "Vendor",
    "vendor email": "VendorEmail",
    "vendoremail": "VendorEmail",
    "vendor phone": "VendorPhone",
    "vendorphone": "VendorPhone",
    "vendor rate": "VendorRate",
    "vendorrate": "VendorRate",
    "sandvik rate": "SandvikRate",
    "sandvikrate": "SandvikRate",
}

# Import column -> UserDetails field name
_TEXT_FIELDS = {"Vendor": "vendor", "VendorEmail": "vendor_email", "VendorPhone": "vendor_phone"}
_DATE_FIELDS = {"StartDate": "start_date", "EndDate": "end_date"}
_RATE_FIELDS = {"VendorRate": "vendor_rate", "SandvikRate": "sandvik_rate"}

_DATE_FORMATS = ("%Y-%m-%d", "%d/%m/%Y", "%d.%m.%Y", "%d-%m-%Y")
_email_adapter = TypeAdapter(EmailStr)


@dataclass
class ParsedUserRow:
    row: int
    email: str
    full_name: str
    # UserDetails field name -> value, only for cells that were filled in.
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class UserImportParseResult:
    rows: list[ParsedUserRow] = field(default_factory=list)
    errors: list[UserImportRowError] = field(default_factory=list)


def _normalize_header(raw_headers: list[Any]) -> dict[str, int]:
    mapping: dict[str, int] = {}
    for idx, raw in enumerate(raw_headers):
        if raw is None:
            continue
        known = HEADER_ALIASES.get(str(raw).strip().lower())
        if known and known not in mapping:
            mapping[known] = idx
    return mapping


def _check_required_columns(header_map: dict[str, int]) -> None:
    missing = [c for c in REQUIRED_COLUMNS if c not in header_map]
    if missing:
        raise AppError(
            status_code=400,
            code="VALIDATION_ERROR",
            message=f"Import file is missing required column(s): {', '.join(missing)}",
            details=[{"field": c, "issue": "required column missing from header row"} for c in missing],
        )


def _raw(row: list[Any], header_map: dict[str, int], column: str) -> Any:
    idx = header_map.get(column)
    if idx is None or idx >= len(row):
        return None
    value = row[idx]
    if isinstance(value, str):
        value = value.strip()
    return value if value not in (None, "") else None


def _text(value: Any) -> str | None:
    return None if value is None else str(value).strip() or None


def _parse_date(value: Any) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    raise ValueError(text)


def _parse_rate(value: Any) -> float:
    if isinstance(value, bool):
        raise ValueError(str(value))
    rate = float(value) if isinstance(value, (int, float)) else float(str(value).strip())
    if not math.isfinite(rate) or rate < 0:
        raise ValueError(str(value))
    return rate


def _validate_row(row_number: int, raw_row: list[Any], header_map: dict[str, int], seen_emails: set[str]):
    """Returns (ParsedUserRow, None) on success or (None, UserImportRowError) on failure."""
    problems: list[str] = []

    full_name = _text(_raw(raw_row, header_map, "Name"))
    if not full_name:
        problems.append("Missing required value for Name")

    email = _text(_raw(raw_row, header_map, "Email"))
    if not email:
        problems.append("Missing required value for Email")
    else:
        email = email.lower()
        try:
            _email_adapter.validate_python(email)
        except ValidationError:
            problems.append(f"Invalid Email '{email}'")
        else:
            if email in seen_emails:
                problems.append(f"Duplicate Email '{email}' within file")

    details: dict[str, Any] = {}
    for column, attr in _TEXT_FIELDS.items():
        value = _text(_raw(raw_row, header_map, column))
        if value is not None:
            details[attr] = value
    for column, attr in _DATE_FIELDS.items():
        value = _raw(raw_row, header_map, column)
        if value is not None:
            try:
                details[attr] = _parse_date(value)
            except ValueError:
                problems.append(f"Invalid {column} '{value}' (use YYYY-MM-DD)")
    for column, attr in _RATE_FIELDS.items():
        value = _raw(raw_row, header_map, column)
        if value is not None:
            try:
                details[attr] = _parse_rate(value)
            except ValueError:
                problems.append(f"Invalid {column} '{value}' (must be a non-negative number)")

    start, end = details.get("start_date"), details.get("end_date")
    if start and end and end < start:
        problems.append("EndDate is before StartDate")

    if problems:
        return None, UserImportRowError(row=row_number, reason="; ".join(problems))

    seen_emails.add(email)
    return ParsedUserRow(row=row_number, email=email, full_name=full_name, details=details), None


def _parse_rows(header: list[Any], data_rows) -> UserImportParseResult:
    header_map = _normalize_header(header)
    _check_required_columns(header_map)

    result = UserImportParseResult()
    seen: set[str] = set()
    for offset, raw_row in enumerate(data_rows):
        row_number = offset + 2  # +1 for 1-indexing, +1 for the header row
        raw_row = list(raw_row)
        if not any(c is not None and str(c).strip() for c in raw_row):
            continue  # skip fully blank rows silently
        parsed, error = _validate_row(row_number, raw_row, header_map, seen)
        if error is not None:
            result.errors.append(error)
        else:
            result.rows.append(parsed)
    return result


def _empty_file_error() -> AppError:
    return AppError(
        status_code=400,
        code="VALIDATION_ERROR",
        message="Import file is empty; a header row is required",
    )


def parse_csv(content: bytes) -> UserImportParseResult:
    reader = csv.reader(io.StringIO(content.decode("utf-8-sig")))
    try:
        header = next(reader)
    except StopIteration:
        raise _empty_file_error()
    return _parse_rows(header, reader)


def parse_xlsx(content: bytes) -> UserImportParseResult:
    workbook = load_workbook(filename=io.BytesIO(content), read_only=True, data_only=True)
    try:
        rows_iter = workbook.active.iter_rows(values_only=True)
        try:
            header = list(next(rows_iter))
        except StopIteration:
            raise _empty_file_error()
        return _parse_rows(header, rows_iter)
    finally:
        workbook.close()


def parse_import_file(filename: str, content: bytes) -> UserImportParseResult:
    lower = filename.lower()
    if lower.endswith(".csv"):
        return parse_csv(content)
    if lower.endswith(".xlsx"):
        return parse_xlsx(content)
    raise AppError(
        status_code=400,
        code="VALIDATION_ERROR",
        message="Unsupported file type; only .csv and .xlsx are accepted",
        details=[{"field": "file", "issue": f"unsupported extension for '{filename}'"}],
    )
