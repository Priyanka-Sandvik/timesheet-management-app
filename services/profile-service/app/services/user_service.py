"""Business logic for /api/v1/me and /admin/users* routes."""
from __future__ import annotations

from py_common.core.errors import AppError

from app.models.schemas import (
    AdminUserSummary,
    CreateUserRequest,
    MeResponse,
    UpdateUserRequest,
    UserDetailsPayload,
    UserImportResponse,
    UserImportRowError,
)
from app.models.user import UserDetails, UserEntity
from app.repositories.user_repository import ResourceExistsError, UserRepository
from app.services.user_import import UserImportParseResult


def _to_details(payload: UserDetailsPayload) -> UserDetails:
    return UserDetails(
        start_date=payload.startDate,
        end_date=payload.endDate,
        vendor=payload.vendor,
        vendor_email=payload.vendorEmail,
        vendor_phone=payload.vendorPhone,
        vendor_rate=payload.vendorRate,
        sandvik_rate=payload.sandvikRate,
    )


class UserService:
    def __init__(
        self,
        *,
        repository: UserRepository,
        admin_emails: set[str],
        allowed_email_domain: str | None = None,
    ) -> None:
        self._repository = repository
        self._admin_emails = {e.lower() for e in admin_emails}
        self._allowed_email_domain = allowed_email_domain.lower().lstrip("@") if allowed_email_domain else None

    def _is_admin(self, email: str) -> bool:
        return email.strip().lower() in self._admin_emails

    def _domain_problem(self, email: str) -> str | None:
        """Admin-created users must later register themselves, which only accepts the
        allowed domain - so the same restriction applies here."""
        if self._allowed_email_domain and not email.endswith(f"@{self._allowed_email_domain}"):
            return f"Email must be a @{self._allowed_email_domain} address"
        return None

    def _to_summary(self, user: UserEntity) -> AdminUserSummary:
        return AdminUserSummary(
            email=user.email,
            fullName=user.full_name,
            isActive=user.is_active,
            isAdmin=self._is_admin(user.email),
            startDate=user.start_date,
            endDate=user.end_date,
            vendor=user.vendor,
            vendorEmail=user.vendor_email,
            vendorPhone=user.vendor_phone,
            vendorRate=user.vendor_rate,
            sandvikRate=user.sandvik_rate,
            createdAt=user.created_at,
            updatedAt=user.updated_at,
        )

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

    def list_users(self, *, active_only: bool = False) -> list[AdminUserSummary]:
        return [self._to_summary(u) for u in self._repository.list_all(active_only=active_only)]

    def create_user(self, payload: CreateUserRequest) -> AdminUserSummary:
        email = str(payload.email).strip().lower()
        problem = self._domain_problem(email)
        if problem:
            raise AppError(
                status_code=400,
                code="VALIDATION_ERROR",
                message=problem,
                details=[{"field": "email", "issue": problem}],
            )
        try:
            user = self._repository.create(
                email=email, full_name=payload.fullName.strip(), details=_to_details(payload)
            )
        except ResourceExistsError as exc:
            raise AppError(
                status_code=409,
                code="CONFLICT",
                message="A user with this email already exists",
                details=[{"field": "email", "issue": "already exists"}],
            ) from exc
        return self._to_summary(user)

    def update_user(self, email: str, payload: UpdateUserRequest) -> AdminUserSummary:
        updated = self._repository.update_profile(
            email.strip().lower(), payload.fullName.strip(), _to_details(payload)
        )
        if updated is None:
            raise AppError(status_code=404, code="NOT_FOUND", message="User not found")
        return self._to_summary(updated)

    def import_users(self, parsed: UserImportParseResult) -> UserImportResponse:
        """Creates new users and updates existing ones (matched by email). For an existing
        user only the cells filled in the file overwrite their stored values; blank cells
        leave them as they are."""
        errors = list(parsed.errors)
        created = updated = 0

        for row in parsed.rows:
            problem = self._domain_problem(row.email)
            if problem:
                errors.append(UserImportRowError(row=row.row, reason=problem))
                continue

            existing = self._repository.get_by_email(row.email)
            if existing is None:
                self._repository.create(
                    email=row.email, full_name=row.full_name, details=UserDetails(**row.details)
                )
                created += 1
                continue

            merged = {**existing.model_dump(include=set(UserDetails.model_fields)), **row.details}
            if merged["start_date"] and merged["end_date"] and merged["end_date"] < merged["start_date"]:
                errors.append(
                    UserImportRowError(row=row.row, reason="EndDate is before StartDate (after merging with existing values)")
                )
                continue
            self._repository.update_profile(row.email, row.full_name, UserDetails(**merged))
            updated += 1

        errors.sort(key=lambda e: e.row)
        return UserImportResponse(created=created, updated=updated, errors=errors)
