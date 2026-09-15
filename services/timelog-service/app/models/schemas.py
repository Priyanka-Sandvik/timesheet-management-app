"""Pydantic v2 schemas for Timelog Service request/response bodies."""
from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field, field_validator


def _is_valid_hours(value: float) -> bool:
    """0 <= value <= 24 and value is an exact multiple of 0.25 (within float tolerance)."""
    if value < 0 or value > 24:
        return False
    # Work in quarter-hour units to avoid binary float rounding issues.
    quarters = value * 4
    return abs(quarters - round(quarters)) < 1e-6


class EntryIn(BaseModel):
    taskCode: str
    entryDate: date
    hours: float
    notes: str | None = None

    @field_validator("hours")
    @classmethod
    def _validate_hours(cls, v: float) -> float:
        if not _is_valid_hours(v):
            raise ValueError("hours must be between 0 and 24 in increments of 0.25")
        return v


class BulkUpsertRequest(BaseModel):
    weekStart: date
    entries: list[EntryIn]


class BulkUpsertResponse(BaseModel):
    saved: int


class EntryOut(BaseModel):
    taskCode: str
    taskName: str | None = None
    projectName: str | None = None
    entryDate: date
    hours: float
    notes: str | None = None
    status: str


class TimesheetGridResponse(BaseModel):
    weekStart: date
    weekEnd: date
    status: str
    entries: list[EntryOut]
    dailyTotals: dict[str, float]
    weeklyTotal: float


class GenerateResponse(BaseModel):
    rowsCreated: int


class CopyPreviousResponse(BaseModel):
    rowsCopied: int


class SubmitResponse(BaseModel):
    status: str
