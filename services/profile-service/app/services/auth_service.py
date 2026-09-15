"""Business logic for registration, login and login-as-admin.

ASSUMPTIONS (documented per task spec, since the contract is ambiguous on a few points):

1. Inactive-user login behavior: the contract only says GET /api/v1/me returns `isActive`
   "so the frontend can react", and does not explicitly say whether login itself should be
   blocked for a deactivated user. This implementation BLOCKS login (401, generic
   "invalid credentials" message so we don't leak account existence/state to a caller who
   doesn't already know the password) for deactivated users on both /auth/login and
   /auth/login-as-admin. Rationale: an admin who deactivates a user almost certainly wants
   to revoke access immediately, not just have the frontend passively show a banner after
   the fact; blocking at issuance time is the safer default for an internal HR-adjacent
   system. If literal "allow login, let the frontend react" behavior is desired instead,
   remove the `is_active` check in `_authenticate` below.

2. ADMIN_EMAILS / email comparison is case-insensitive (email local-parts/domains are
   conventionally case-insensitive; Sandvik SSO/email addresses are not case-sensitive in
   practice). Both the Users table PartitionKey (email) and ADMIN_EMAILS membership checks
   normalize to lowercase before comparison.

3. Email domain validation on registration (`ALLOWED_EMAIL_DOMAIN`) is likewise a
   case-insensitive suffix check.
"""
from __future__ import annotations

from py_common.core.errors import AppError
from py_common.core.jwt_issue import JwtIssuer

from app.core.security import hash_password, verify_password
from app.models.schemas import RegisterRequest
from app.models.user import UserEntity
from app.repositories.user_repository import ResourceExistsError, UserRepository


class AuthService:
    def __init__(
        self,
        *,
        repository: UserRepository,
        jwt_issuer: JwtIssuer,
        allowed_email_domain: str,
        admin_emails: set[str],
    ) -> None:
        self._repository = repository
        self._jwt_issuer = jwt_issuer
        self._allowed_email_domain = allowed_email_domain.lower().lstrip("@")
        self._admin_emails = {e.lower() for e in admin_emails}

    def _normalize_email(self, email: str) -> str:
        return email.strip().lower()

    def is_admin(self, email: str) -> bool:
        return self._normalize_email(email) in self._admin_emails

    def register(self, payload: RegisterRequest) -> UserEntity:
        email = self._normalize_email(payload.email)
        if not email.endswith(f"@{self._allowed_email_domain}"):
            raise AppError(
                status_code=400,
                code="VALIDATION_ERROR",
                message=f"Email must be a @{self._allowed_email_domain} address",
                details=[{"field": "email", "issue": f"must end in @{self._allowed_email_domain}"}],
            )

        password_hash = hash_password(payload.password)
        try:
            return self._repository.create(email=email, full_name=payload.fullName, password_hash=password_hash)
        except ResourceExistsError as exc:
            raise AppError(
                status_code=409,
                code="CONFLICT",
                message="A user with this email already exists",
                details=[{"field": "email", "issue": "already registered"}],
            ) from exc

    def _authenticate(self, email: str, password: str) -> UserEntity:
        normalized_email = self._normalize_email(email)
        user = self._repository.get_by_email(normalized_email)
        if user is None or not verify_password(password, user.password_hash):
            raise AppError(status_code=401, code="UNAUTHORIZED", message="Invalid email or password")
        if not user.is_active:
            # See ASSUMPTION 1 above: deactivated users are blocked at login time.
            raise AppError(status_code=401, code="UNAUTHORIZED", message="Invalid email or password")
        return user

    def login(self, email: str, password: str) -> tuple[str, int]:
        user = self._authenticate(email, password)
        is_admin = self.is_admin(user.email)
        return self._jwt_issuer.issue_token(email=user.email, is_admin=is_admin, full_name=user.full_name)

    def login_as_admin(self, email: str, password: str) -> tuple[str, int]:
        user = self._authenticate(email, password)
        if not self.is_admin(user.email):
            raise AppError(status_code=403, code="FORBIDDEN", message="This account does not have admin privileges")
        return self._jwt_issuer.issue_token(email=user.email, is_admin=True, full_name=user.full_name)

    def get_jwks(self) -> dict:
        return self._jwt_issuer.get_jwks()
