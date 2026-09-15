"""Business logic for /api/v1/me and /admin/users* routes."""
from __future__ import annotations

from py_common.core.errors import AppError

from app.models.schemas import AdminUserSummary, MeResponse
from app.models.user import UserEntity
from app.repositories.user_repository import UserRepository


class UserService:
    def __init__(self, *, repository: UserRepository, admin_emails: set[str]) -> None:
        self._repository = repository
        self._admin_emails = {e.lower() for e in admin_emails}

    def _is_admin(self, email: str) -> bool:
        return email.strip().lower() in self._admin_emails

    def get_me(self, email: str) -> MeResponse:
        user = self._repository.get_by_email(email.strip().lower())
        if user is None:
            raise AppError(status_code=404, code="NOT_FOUND", message="User not found")
        return MeResponse(
            email=user.email,
            fullName=user.full_name,
            isAdmin=self._is_admin(user.email),
            isActive=user.is_active,
        )

    def set_user_status(self, email: str, is_active: bool) -> UserEntity:
        normalized = email.strip().lower()
        updated = self._repository.update_active_status(normalized, is_active)
        if updated is None:
            raise AppError(status_code=404, code="NOT_FOUND", message="User not found")
        return updated

    def list_users(self, *, active_only: bool = False) -> list[AdminUserSummary]:
        users = self._repository.list_all(active_only=active_only)
        return [
            AdminUserSummary(
                email=u.email,
                fullName=u.full_name,
                isActive=u.is_active,
                isAdmin=self._is_admin(u.email),
                createdAt=u.created_at,
                updatedAt=u.updated_at,
            )
            for u in users
        ]
