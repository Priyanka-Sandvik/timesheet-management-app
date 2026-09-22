"""Internal domain model for a user, decoupled from both the Table Storage entity shape
and the public API schemas.
"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class UserEntity(BaseModel):
    """Mirrors the Users table schema (architecture doc §6):

    PartitionKey = Email, RowKey = "PROFILE".
    Fields: FullName, PasswordHash (Argon2id), PasswordAlgo, IsActive, CreatedAt, UpdatedAt.

    NOTE: there is intentionally no Role/isAdmin column, and admin accounts are never rows
    in this table at all — admin identity/password lives only in the fixed ADMIN_CREDENTIALS
    config, checked exclusively by /auth/login-as-admin, and embedded only in the issued JWT.
    """

    email: str
    full_name: str
    password_hash: str
    password_algo: str = "argon2id"
    is_active: bool = True
    created_at: datetime
    updated_at: datetime
