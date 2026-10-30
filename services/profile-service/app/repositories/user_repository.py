"""Table Storage access for the Users table (architecture doc §6).

PartitionKey = Email, RowKey = "PROFILE" (fixed value - one profile entity per user).
Routers/services never touch Table Storage directly; only this repository does.
"""
from __future__ import annotations

from datetime import date, datetime, timezone

from azure.core.exceptions import ResourceExistsError, ResourceNotFoundError
from azure.data.tables import TableClient, UpdateMode

from app.models.user import UserDetails, UserEntity

ROW_KEY = "PROFILE"


class UserRepository:
    def __init__(self, table_client: TableClient) -> None:
        self._table_client = table_client

    @staticmethod
    def _to_entity_dict(user: UserEntity) -> dict:
        entity = {
            "PartitionKey": user.email,
            "RowKey": ROW_KEY,
            "FullName": user.full_name,
            "PasswordHash": user.password_hash,
            "PasswordAlgo": user.password_algo,
            "StartDate": user.start_date.isoformat() if user.start_date else None,
            "EndDate": user.end_date.isoformat() if user.end_date else None,
            "Vendor": user.vendor,
            "VendorEmail": user.vendor_email,
            "VendorPhone": user.vendor_phone,
            "VendorRate": user.vendor_rate,
            "SandvikRate": user.sandvik_rate,
            "CreatedAt": user.created_at.isoformat(),
            "UpdatedAt": user.updated_at.isoformat(),
        }
        # Unset optional values are left out entirely so a REPLACE clears them.
        return {k: v for k, v in entity.items() if v is not None}

    @staticmethod
    def _from_entity_dict(entity: dict) -> UserEntity:
        start_date = entity.get("StartDate")
        end_date = entity.get("EndDate")
        vendor_rate = entity.get("VendorRate")
        sandvik_rate = entity.get("SandvikRate")
        return UserEntity(
            email=entity["PartitionKey"],
            full_name=entity["FullName"],
            password_hash=entity.get("PasswordHash"),
            password_algo=entity.get("PasswordAlgo", "argon2id"),
            start_date=date.fromisoformat(start_date) if start_date else None,
            end_date=date.fromisoformat(end_date) if end_date else None,
            vendor=entity.get("Vendor"),
            vendor_email=entity.get("VendorEmail"),
            vendor_phone=entity.get("VendorPhone"),
            vendor_rate=float(vendor_rate) if vendor_rate is not None else None,
            sandvik_rate=float(sandvik_rate) if sandvik_rate is not None else None,
            created_at=datetime.fromisoformat(entity["CreatedAt"]),
            updated_at=datetime.fromisoformat(entity["UpdatedAt"]),
        )

    def create(
        self,
        *,
        email: str,
        full_name: str,
        password_hash: str | None = None,
        details: UserDetails | None = None,
    ) -> UserEntity:
        """Creates a new user profile. Raises ResourceExistsError (mapped to 409 by the
        service layer) if the email already exists.
        """
        now = datetime.now(timezone.utc)
        user = UserEntity(
            email=email,
            full_name=full_name,
            password_hash=password_hash,
            created_at=now,
            updated_at=now,
            **(details.model_dump() if details else {}),
        )
        self._table_client.create_entity(entity=self._to_entity_dict(user))
        return user

    def get_by_email(self, email: str) -> UserEntity | None:
        try:
            entity = self._table_client.get_entity(partition_key=email, row_key=ROW_KEY)
        except ResourceNotFoundError:
            return None
        return self._from_entity_dict(entity)

    def update_profile(self, email: str, full_name: str, details: UserDetails) -> UserEntity | None:
        """Replaces the user's name and details (the password is left untouched)."""
        existing = self.get_by_email(email)
        if existing is None:
            return None
        updated = existing.model_copy(
            update={**details.model_dump(), "full_name": full_name, "updated_at": datetime.now(timezone.utc)}
        )
        self._table_client.update_entity(entity=self._to_entity_dict(updated), mode=UpdateMode.REPLACE)
        return updated

    def set_password_hash(self, email: str, password_hash: str) -> UserEntity | None:
        existing = self.get_by_email(email)
        if existing is None:
            return None
        existing.password_hash = password_hash
        existing.updated_at = datetime.now(timezone.utc)
        self._table_client.update_entity(entity=self._to_entity_dict(existing), mode=UpdateMode.REPLACE)
        return existing

    def list_all(self, *, active_only: bool = False) -> list[UserEntity]:
        users = [self._from_entity_dict(e) for e in self._table_client.list_entities()]
        return [u for u in users if u.is_active] if active_only else users


__all__ = ["UserRepository", "ResourceExistsError", "ResourceNotFoundError"]
