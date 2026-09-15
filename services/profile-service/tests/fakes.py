"""In-memory fake repository used by unit tests, matching UserRepository's public
interface without touching real Table Storage.
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.models.user import UserEntity
from app.repositories.user_repository import ResourceExistsError


class FakeUserRepository:
    def __init__(self) -> None:
        self._store: dict[str, UserEntity] = {}

    def create(self, *, email: str, full_name: str, password_hash: str) -> UserEntity:
        if email in self._store:
            raise ResourceExistsError("entity already exists")
        now = datetime.now(timezone.utc)
        user = UserEntity(
            email=email,
            full_name=full_name,
            password_hash=password_hash,
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        self._store[email] = user
        return user

    def get_by_email(self, email: str) -> UserEntity | None:
        return self._store.get(email)

    def update_active_status(self, email: str, is_active: bool) -> UserEntity | None:
        user = self._store.get(email)
        if user is None:
            return None
        user.is_active = is_active
        user.updated_at = datetime.now(timezone.utc)
        return user

    def list_all(self, *, active_only: bool = False) -> list[UserEntity]:
        users = list(self._store.values())
        if active_only:
            users = [u for u in users if u.is_active]
        return users
