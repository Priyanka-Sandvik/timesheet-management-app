"""Composition root: builds singletons (table client, repository, JWT issuer/verifier,
service instances) and exposes them as FastAPI dependencies.
"""
from __future__ import annotations

from functools import lru_cache

from py_common.core.jwt_issue import JwtIssuer
from py_common.core.jwt_verify import AuthenticatedUser
from py_common.core.rate_limit import SlidingWindowRateLimiter
from py_common.core.table_client import get_table_service_client

from app.config import Settings, get_settings
from app.core.jwt import build_jwt_issuer, build_jwt_verifier_dependencies
from app.repositories.user_repository import UserRepository
from app.services.auth_service import AuthService
from app.services.user_service import UserService


@lru_cache
def get_table_service_client_singleton():
    settings = get_settings()
    return get_table_service_client(connection_string=settings.AZURE_STORAGE_CONNECTION_STRING or None)


@lru_cache
def get_table_client_for_users():
    settings = get_settings()
    return get_table_service_client_singleton().get_table_client(settings.USERS_TABLE_NAME)


@lru_cache
def get_user_repository() -> UserRepository:
    return UserRepository(get_table_client_for_users())


@lru_cache
def get_jwt_issuer() -> JwtIssuer:
    return build_jwt_issuer(get_settings())


@lru_cache
def _jwt_dependencies():
    return build_jwt_verifier_dependencies(get_settings())


def get_require_user():
    _, require_user, _ = _jwt_dependencies()
    return require_user


def get_require_admin():
    _, _, require_admin = _jwt_dependencies()
    return require_admin


@lru_cache
def get_auth_service() -> AuthService:
    settings = get_settings()
    return AuthService(
        repository=get_user_repository(),
        jwt_issuer=get_jwt_issuer(),
        allowed_email_domain=settings.ALLOWED_EMAIL_DOMAIN,
        admin_credentials=settings.admin_credentials_map,
    )


@lru_cache
def get_user_service() -> UserService:
    settings = get_settings()
    return UserService(repository=get_user_repository(), admin_emails=set(settings.admin_credentials_map.keys()))


@lru_cache
def get_auth_rate_limiter() -> SlidingWindowRateLimiter:
    settings = get_settings()
    return SlidingWindowRateLimiter(calls_per_minute=settings.AUTH_RATE_LIMIT_PER_MINUTE)


__all__ = [
    "get_table_service_client_singleton",
    "get_table_client_for_users",
    "get_user_repository",
    "get_jwt_issuer",
    "get_require_user",
    "get_require_admin",
    "get_auth_service",
    "get_user_service",
    "get_auth_rate_limiter",
    "AuthenticatedUser",
]
