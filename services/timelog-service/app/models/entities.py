"""Internal representation of a Timesheet table entity, mapped to/from Azure Table Storage.

PartitionKey = UserId (Email). RowKey = `EntryDate_TaskCode` (EntryDate as ISO YYYY-MM-DD).
This RowKey scheme structurally prevents duplicate (user, task, date) rows.

Note: `_` (not `#`) is used as the delimiter because Azure Table Storage forbids the
forward slash, backslash, `#`, and `?` characters in PartitionKey/RowKey values — Azurite
enforces this too and rejects any entity containing `#` with a 400 InvalidInput error.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone


STATUS_PENDING = "Pending"
STATUS_SUBMITTED = "Submitted"


def make_row_key(entry_date: date, task_code: str) -> str:
    return f"{entry_date.isoformat()}_{task_code}"


def parse_row_key(row_key: str) -> tuple[date, str]:
    date_part, task_code = row_key.split("_", 1)
    return date.fromisoformat(date_part), task_code


@dataclass
class TimesheetEntity:
    user_id: str  # PartitionKey
    entry_date: date
    task_code: str
    task_name: str | None
    project_name: str | None
    week_start_date: date
    hours_logged: float
    notes: str | None
    status: str
    created_at: datetime
    updated_at: datetime
    etag: str | None = field(default=None)

    @property
    def row_key(self) -> str:
        return make_row_key(self.entry_date, self.task_code)

    def to_table_entity(self) -> dict:
        return {
            "PartitionKey": self.user_id,
            "RowKey": self.row_key,
            "TaskName": self.task_name,
            "ProjectName": self.project_name,
            "WeekStartDate": self.week_start_date.isoformat(),
            "EntryDate": self.entry_date.isoformat(),
            "HoursLogged": float(self.hours_logged),
            "Notes": self.notes,
            "Status": self.status,
            "CreatedAt": self.created_at.isoformat(),
            "UpdatedAt": self.updated_at.isoformat(),
        }

    @staticmethod
    def from_table_entity(entity: dict) -> "TimesheetEntity":
        entry_date, task_code = parse_row_key(entity["RowKey"])
        return TimesheetEntity(
            user_id=entity["PartitionKey"],
            entry_date=entry_date,
            task_code=task_code,
            task_name=entity.get("TaskName"),
            project_name=entity.get("ProjectName"),
            week_start_date=date.fromisoformat(entity["WeekStartDate"]),
            hours_logged=float(entity.get("HoursLogged", 0.0)),
            notes=entity.get("Notes"),
            status=entity.get("Status", STATUS_PENDING),
            created_at=_parse_dt(entity.get("CreatedAt")),
            updated_at=_parse_dt(entity.get("UpdatedAt")),
            etag=entity.metadata.get("etag") if hasattr(entity, "metadata") else None,
        )


def _parse_dt(value) -> datetime:
    if value is None:
        return datetime.now(timezone.utc)
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value))


def utcnow() -> datetime:
    return datetime.now(timezone.utc)
