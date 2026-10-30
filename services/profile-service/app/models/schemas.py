"""Pydantic request/response schemas for Profile Service (architecture doc §8.1)."""
from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator


# ---------- Requests ----------


class RegisterRequest(BaseModel):
    email: EmailStr
    fullName: str = Field(min_length=1, max_length=200)
    password: str = Field(min_length=8, max_length=256)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=256)


class UserDetailsPayload(BaseModel):
    """Optional admin-maintained user details; blank strings are treated as not provided."""

    startDate: date | None = None
    endDate: date | None = None
    vendor: str | None = None
    vendorEmail: str | None = None
    vendorPhone: str | None = None
    vendorRate: float | None = Field(default=None, ge=0)
    sandvikRate: float | None = Field(default=None, ge=0)

    @field_validator("vendor", "vendorEmail", "vendorPhone", mode="before")
    @classmethod
    def _blank_to_none(cls, v: object) -> object:
        if isinstance(v, str):
            v = v.strip()
            return v or None
        return v

    @model_validator(mode="after")
    def _end_not_before_start(self) -> "UserDetailsPayload":
        if self.startDate and self.endDate and self.endDate < self.startDate:
            raise ValueError("endDate must not be before startDate")
        return self


class CreateUserRequest(UserDetailsPayload):
    fullName: str = Field(min_length=1, max_length=200)
    email: EmailStr


class UpdateUserRequest(UserDetailsPayload):
    fullName: str = Field(min_length=1, max_length=200)


# ---------- Responses ----------


class RegisterResponse(BaseModel):
    email: str
    fullName: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    # The other panel's token for admins (admin <-> employee), so the frontend can switch
    # panels without a second login. Null for non-admins.
    alternate_access_token: str | None = None


class MeResponse(BaseModel):
    email: str
    fullName: str
    isAdmin: bool
    isActive: bool


class AdminUserSummary(BaseModel):
    email: str
    fullName: str
    isActive: bool
    isAdmin: bool
    startDate: date | None = None
    endDate: date | None = None
    vendor: str | None = None
    vendorEmail: str | None = None
    vendorPhone: str | None = None
    vendorRate: float | None = None
    sandvikRate: float | None = None
    createdAt: datetime
    updatedAt: datetime


class AdminUserListResponse(BaseModel):
    users: list[AdminUserSummary]


class UserImportRowError(BaseModel):
    row: int
    reason: str


class UserImportResponse(BaseModel):
    created: int
    updated: int
    errors: list[UserImportRowError]


class JwksResponse(BaseModel):
    keys: list[dict]
