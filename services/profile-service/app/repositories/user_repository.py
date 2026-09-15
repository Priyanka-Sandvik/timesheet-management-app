"""Table Storage access for the Users table (architecture doc §6).

PartitionKey = Email, RowKey = "PROFILE" (fixed value - one profile entity per user).
Routers/services never touch Table Storage directly; only this repository does.
"""
from __future__ import annotations

from datetime import datetime, timezone

from azure.core.exceptions import ResourceExistsError, ResourceNotFoundError
from azure.data.tables import TableClient, UpdateMode

from app.models.user import UserEntity

ROW_KEY = "PROFILE"


class UserRepository:
    def __init__(self, table_client: TableClient) -> None:
        self._table_client = table_client

    @staticmethod
    def _to_entity_dict(user: UserEntity) -> dict:
        return {
            "PartitionKey": user.email,
            "RowKey": ROW_KEY,
            "FullName": user.full_name,
            "PasswordHash": user.password_hash,
            "PasswordAlgo": user.password_algo,
            "IsActive": user.is_active,
            "CreatedAt": user.created_at.isoformat(),
            "UpdatedAt": user.updated_at.isoformat(),
        }

    @staticmethod
    def _from_entity_dict(entity: dict) -> UserEntity:
        return UserEntity(
            email=entity["PartitionKey"],
            full_name=entity["FullName"],
            password_hash=entity["PasswordHash"],
            password_algo=entity.get("PasswordAlgo", "argon2id"),
            is_active=bool(entity.get("IsActive", True)),
            created_at=datetime.fromisoformat(entity["CreatedAt"]),
            updated_at=datetime.fromisoformat(entity["UpdatedAt"]),
        )

    def create(self, *, email: str, full_name: str, password_hash: str) -> UserEntity:
        """Creates a new user profile. Raises ResourceExistsError (mapped to 409 by the
        service layer) if the email already exists.
        """
        now = datetime.now(timezone.utc)
        user = UserEntity(
            email=email,
            full_name=full_name,
            password_hash=password_hash,
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        self._table_client.create_entity(entity=self._to_entity_dict(user))
        return user

    def get_by_email(self, email: str) -> UserEntity | None:
        try:
            entity = self._table_client.get_entity(partition_key=email, row_key=ROW_KEY)
        except ResourceNotFoundError:
            return None
        return self._from_entity_dict(entity)

    def update_active_status(self, email: str, is_active: bool) -> UserEntity | None:
        existing = self.get_by_email(email)
        if existing is None:
            return None
        existing.is_active = is_active
        existing.updated_at = datetime.now(timezone.utc)
        self._table_client.update_entity(entity=self._to_entity_dict(existing), mode=UpdateMode.REPLACE)
        return existing

    def list_all(self, *, active_only: bool = False) -> list[UserEntity]:
        filter_query = "IsActive eq true" if active_only else None
        entities = self._table_client.query_entities(query_filter=filter_query) if filter_query else self._table_client.list_entities()
        return [self._from_entity_dict(e) for e in entities]


__all__ = ["UserRepository", "ResourceExistsError", "ResourceNotFoundError"]
