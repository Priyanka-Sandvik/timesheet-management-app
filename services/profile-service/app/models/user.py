"""Internal domain model for a user, decoupled from both the Table Storage entity shape
and the public API schemas.
"""
from __future__ import annotations

from datetime import date, datetime, timezone

from pydantic import BaseModel


class UserDetails(BaseModel):
    """Optional, admin-maintained details of a user (contract / vendor information)."""

    start_date: date | None = None
    end_date: date | None = None
    vendor: str | None = None
    vendor_email: str | None = None
    vendor_phone: str | None = None
    vendor_rate: float | None = None
    sandvik_rate: float | None = None


class UserEntity(UserDetails):
    """Mirrors the Users table schema (architecture doc §6):

    PartitionKey = Email, RowKey = "PROFILE".
    Fields: FullName, PasswordHash (Argon2id), PasswordAlgo, StartDate, EndDate, Vendor,
    VendorEmail, VendorPhone, VendorRate, SandvikRate, CreatedAt, UpdatedAt.

    `password_hash` is None for a user an admin created (or imported) who has not yet
    completed their own registration; such a user cannot log in until they do.

    `is_active` is derived, not stored: a user is active until their end date has passed
    (no end date means active indefinitely).

    NOTE: there is intentionally no general Role/isAdmin column. Admin status comes from the
    fixed ADMIN_CREDENTIALS config, plus `is_coe_admin` below, and is embedded only in the
    issued JWT. An admin may also have a row here (registered as an employee), which is what
    lists them in User Management and lets them use the employee panel.

    `is_coe_admin` is maintained by Task Service (PUT /admin/users/coe-admins) after every
    task change: True while the user is CoE Responsible of an Open or OnHold task. It is kept
    apart from the config admins so a task change can never demote one of those.
    """

    email: str
    full_name: str
    password_hash: str | None = None
    password_algo: str = "argon2id"
    is_coe_admin: bool = False
    created_at: datetime
    updated_at: datetime

    @property
    def is_active(self) -> bool:
        return self.end_date is None or datetime.now(timezone.utc).date() <= self.end_date
