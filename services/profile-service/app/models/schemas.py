"""Pydantic request/response schemas for Profile Service (architecture doc §8.1)."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


# ---------- Requests ----------


class RegisterRequest(BaseModel):
    email: EmailStr
    fullName: str = Field(min_length=1, max_length=200)
    password: str = Field(min_length=8, max_length=256)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=256)


class UpdateUserStatusRequest(BaseModel):
    isActive: bool


# ---------- Responses ----------


class RegisterResponse(BaseModel):
    email: str
    fullName: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class MeResponse(BaseModel):
    email: str
    fullName: str
    isAdmin: bool
    isActive: bool


class UserStatusResponse(BaseModel):
    email: str
    isActive: bool


class AdminUserSummary(BaseModel):
    email: str
    fullName: str
    isActive: bool
    isAdmin: bool
    createdAt: datetime
    updatedAt: datetime


class AdminUserListResponse(BaseModel):
    users: list[AdminUserSummary]


class JwksResponse(BaseModel):
    keys: list[dict]
