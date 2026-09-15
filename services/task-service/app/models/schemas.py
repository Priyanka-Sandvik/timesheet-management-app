"""Pydantic v2 schemas for Task Service (architecture doc §6 / §8.2)."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

VALID_STATUSES = ("Open", "OnHold", "Closed")
UNASSIGNED_PARTITION = "UNASSIGNED"


# --------------------------------------------------------------------------- #
# Core task representation
# --------------------------------------------------------------------------- #
class TaskOut(BaseModel):
    taskCode: str
    taskName: str
    description: str | None = None
    sponsor: str | None = None
    costCentre: str | None = None
    coeResponsible: str | None = None
    status: str
    assignedUserId: str | None = None
    createdAt: str | None = None
    updatedAt: str | None = None


class TaskListResponse(BaseModel):
    tasks: list[TaskOut]


class AdminTaskListResponse(BaseModel):
    tasks: list[TaskOut]
    nextPage: str | None = None


# --------------------------------------------------------------------------- #
# Import
# --------------------------------------------------------------------------- #
class ImportRowError(BaseModel):
    row: int
    reason: str


class ImportResult(BaseModel):
    imported: int
    skipped: int
    errors: list[ImportRowError] = Field(default_factory=list)


class ParsedTaskRow(BaseModel):
    task_code: str
    task_name: str
    description: str | None = None
    sponsor: str | None = None
    cost_centre: str | None = None
    coe_responsible: str | None = None
    status: str


class ImportParseResult(BaseModel):
    rows: list[ParsedTaskRow] = Field(default_factory=list)
    errors: list[ImportRowError] = Field(default_factory=list)


# --------------------------------------------------------------------------- #
# Assign / unassign
# --------------------------------------------------------------------------- #
class AssignRequest(BaseModel):
    emails: list[str]

    @field_validator("emails")
    @classmethod
    def _non_empty(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("emails must contain at least one address")
        return v


class SkippedAssignment(BaseModel):
    email: str
    reason: str


class AssignResponse(BaseModel):
    assigned: list[str]
    skipped: list[SkippedAssignment]


# --------------------------------------------------------------------------- #
# Admin manual create
# --------------------------------------------------------------------------- #
class TaskCreateRequest(BaseModel):
    taskCode: str
    taskName: str
    description: str | None = None
    sponsor: str | None = None
    costCentre: str | None = None
    coeResponsible: str | None = None
    status: Literal["Open", "OnHold", "Closed"] = "Open"

    @field_validator("taskCode", "taskName")
    @classmethod
    def _non_empty_required(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("must not be empty")
        return v.strip()


# --------------------------------------------------------------------------- #
# Admin template edit
# --------------------------------------------------------------------------- #
class TaskUpdateRequest(BaseModel):
    taskName: str | None = None
    description: str | None = None
    sponsor: str | None = None
    costCentre: str | None = None
    coeResponsible: str | None = None
    status: Literal["Open", "OnHold", "Closed"] | None = None
