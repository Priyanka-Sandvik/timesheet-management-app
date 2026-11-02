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
   `_authenticate` below. This applies to admins too, since they are Users-table rows.

2. Email comparison is case-insensitive (email local-parts/domains are conventionally
   case-insensitive; Sandvik SSO/email addresses are not case-sensitive in practice). Both
   the Users table PartitionKey (email) and admin-email membership checks normalize to
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
        admin_emails: set[str],
    ) -> None:
        self._repository = repository
        self._jwt_issuer = jwt_issuer
        self._allowed_email_domain = allowed_email_domain.lower().lstrip("@")
        self._admin_emails = {e.lower() for e in admin_emails}

    def _normalize_email(self, email: str) -> str:
        return email.strip().lower()

    def is_admin(self, email: str) -> bool:
        """True iff `email` is configured as an admin (ADMIN_CREDENTIALS). Admins are also
        ordinary Users-table rows with a single password."""
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
        # Admin emails register like any employee: the Users row holds their single password
        # and lists them in User Management; the admin flag comes from the admin email list.
        password_hash = hash_password(payload.password)
        # A user an admin created or imported has no password yet: registering with the same
        # email completes that profile instead of conflicting with it.
        existing = self._repository.get_by_email(email)
        if existing is not None and existing.password_hash is None:
            return self._repository.set_password_hash(email, password_hash)
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
        if user is None or user.password_hash is None or not verify_password(password, user.password_hash):
            raise AppError(status_code=401, code="UNAUTHORIZED", message="Invalid email or password")
        if not user.is_active:
            # See ASSUMPTION 1 above: users past their end date are blocked at login time.
            raise AppError(status_code=401, code="UNAUTHORIZED", message="Invalid email or password")
        return user

    def _issue_pair(self, user: UserEntity) -> tuple[tuple[str, int], tuple[str, int] | None]:
        """(employee token, admin token or None). The employee token never carries
        isAdmin, so an admin in the employee panel gets no admin rights on any service."""
        employee = self._jwt_issuer.issue_token(email=user.email, is_admin=False, full_name=user.full_name)
        admin = None
        # Config admins, plus anyone Task Service currently flags as CoE Responsible of an
        # Open/OnHold task. Either way the flag is read at login, so a change applies from
        # the person's next login.
        if self.is_admin(user.email) or user.is_coe_admin:
            admin = self._jwt_issuer.issue_token(email=user.email, is_admin=True, full_name=user.full_name)
        return employee, admin

    def login(self, email: str, password: str) -> tuple[str, int, str | None]:
        """Returns (access_token, expires_in, alternate_token). access_token is always an
        employee token; alternate_token is the admin token for admins (used by the frontend
        to switch panels without a second login), else None."""
        employee, admin = self._issue_pair(self._authenticate(email, password))
        return employee[0], employee[1], admin[0] if admin else None

    def login_as_admin(self, email: str, password: str) -> tuple[str, int, str]:
        """Returns (access_token, expires_in, alternate_token): admin token first, employee
        token as the alternate."""
        employee, admin = self._issue_pair(self._authenticate(email, password))
        # Same generic message/status for "not an admin" and "wrong password" so we don't
        # leak which accounts are admins, matching _authenticate's rationale.
        if admin is None:
            raise AppError(status_code=401, code="UNAUTHORIZED", message="Invalid email or password")
        return admin[0], admin[1], employee[0]

    def get_jwks(self) -> dict:
        return self._jwt_issuer.get_jwks()
