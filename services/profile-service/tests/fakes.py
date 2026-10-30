"""In-memory fake repository used by unit tests, matching UserRepository's public
interface without touching real Table Storage.
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.models.user import UserDetails, UserEntity
from app.repositories.user_repository import ResourceExistsError


class FakeUserRepository:
    def __init__(self) -> None:
        self._store: dict[str, UserEntity] = {}

    def create(
        self,
        *,
        email: str,
        full_name: str,
        password_hash: str | None = None,
        details: UserDetails | None = None,
    ) -> UserEntity:
        if email in self._store:
            raise ResourceExistsError("entity already exists")
        now = datetime.now(timezone.utc)
        user = UserEntity(
            email=email,
            full_name=full_name,
            password_hash=password_hash,
            created_at=now,
            updated_at=now,
            **(details.model_dump() if details else {}),
        )
        self._store[email] = user
        return user

    def get_by_email(self, email: str) -> UserEntity | None:
        return self._store.get(email)

    def update_profile(self, email: str, full_name: str, details: UserDetails) -> UserEntity | None:
        user = self._store.get(email)
        if user is None:
            return None
        updated = user.model_copy(
            update={**details.model_dump(), "full_name": full_name, "updated_at": datetime.now(timezone.utc)}
        )
        self._store[email] = updated
        return updated

    def set_password_hash(self, email: str, password_hash: str) -> UserEntity | None:
        user = self._store.get(email)
        if user is None:
            return None
        user.password_hash = password_hash
        user.updated_at = datetime.now(timezone.utc)
        return user

    def list_all(self, *, active_only: bool = False) -> list[UserEntity]:
        users = list(self._store.values())
        if active_only:
            users = [u for u in users if u.is_active]
        return users
