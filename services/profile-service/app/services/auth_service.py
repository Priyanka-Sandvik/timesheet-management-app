"""Business logic for registration, login and login-as-admin.

ASSUMPTIONS (documented per task spec, since the contract is ambiguous on a few points):

1. Inactive-user login behavior: the contract only says GET /api/v1/me returns `isActive`
   "so the frontend can react", and does not explicitly say whether login itself should be
   blocked for a deactivated user. This implementation BLOCKS login (401, generic
   "invalid credentials" message so we don't leak account existence/state to a caller who
   doesn't already know the password) for deactivated users on /auth/login. Rationale: an
   admin who deactivates a user almost certainly wants to revoke access immediately, not
   just have the frontend passively show a banner after the fact; blocking at issuance time
   is the safer default for an internal HR-adjacent system. If literal "allow login, let the
   frontend react" behavior is desired instead, remove the `is_active` check in
   `_authenticate` below. This does not apply to /auth/login-as-admin: fixed admin accounts
   (ADMIN_CREDENTIALS) are never Users-table rows, so there is no `is_active` to check.

2. Email comparison is case-insensitive (email local-parts/domains are conventionally
   case-insensitive; Sandvik SSO/email addresses are not case-sensitive in practice). Both
   the Users table PartitionKey (email) and ADMIN_CREDENTIALS membership checks normalize to
   lowercase before comparison.

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
        admin_credentials: dict[str, str],
    ) -> None:
        self._repository = repository
        self._jwt_issuer = jwt_issuer
        self._allowed_email_domain = allowed_email_domain.lower().lstrip("@")
        self._admin_credentials = {e.lower(): h for e, h in admin_credentials.items()}

    def _normalize_email(self, email: str) -> str:
        return email.strip().lower()

    def is_admin(self, email: str) -> bool:
        """True iff `email` is one of the fixed admin accounts (never a Users-table row)."""
        return self._normalize_email(email) in self._admin_credentials

    def register(self, payload: RegisterRequest) -> UserEntity:
        email = self._normalize_email(payload.email)
        if not email.endswith(f"@{self._allowed_email_domain}"):
            raise AppError(
                status_code=400,
                code="VALIDATION_ERROR",
                message=f"Email must be a @{self._allowed_email_domain} address",
                details=[{"field": "email", "issue": f"must end in @{self._allowed_email_domain}"}],
            )
        if self.is_admin(email):
            # Admin accounts are fixed config entries, not employee registrations - see
            # is_admin() docstring. Reject registration to avoid a confusing identity clash
            # between an employee row and the admin login path for the same address.
            raise AppError(
                status_code=409,
                code="CONFLICT",
                message="A user with this email already exists",
                details=[{"field": "email", "issue": "already registered"}],
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
        # Admins are never Users-table rows (see is_admin() docstring), so a regular
        # employee login can never resolve to is_admin=True - that only happens via
        # login_as_admin below.
        user = self._authenticate(email, password)
        return self._jwt_issuer.issue_token(email=user.email, is_admin=False, full_name=user.full_name)

    def login_as_admin(self, email: str, password: str) -> tuple[str, int]:
        normalized_email = self._normalize_email(email)
        stored_password = self._admin_credentials.get(normalized_email)
        # Same generic message/status for "unknown admin email" and "wrong password" so we
        # don't leak which admin accounts exist, matching _authenticate's rationale.
        if stored_password is None or password != stored_password:
            raise AppError(status_code=401, code="UNAUTHORIZED", message="Invalid email or password")
        return self._jwt_issuer.issue_token(email=normalized_email, is_admin=True, full_name=None)

    def get_jwks(self) -> dict:
        return self._jwt_issuer.get_jwks()
