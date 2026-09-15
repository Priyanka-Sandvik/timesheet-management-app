"""FastAPI dependency wiring: JWT verification deps + per-request TaskService construction.

Kept separate from app/main.py so routers can `from app.core.deps import require_user,
require_admin, get_task_service` and tests can override these via
`app.dependency_overrides[...]` without needing a running Table Storage / JWKS endpoint.
"""
from __future__ import annotations

from fastapi import Request

from app.config import Settings, get_settings
from app.core.jwt import build_jwt_verifier_dependencies
from app.repositories.task_repository import TaskRepository
from app.services.task_service import TaskService

settings: Settings = get_settings()
verifier, require_user, require_admin = build_jwt_verifier_dependencies(settings)


def get_task_service(request: Request) -> TaskService:
    """Builds a TaskService backed by the TableClient created once at app startup
    (see app/main.py) and stored on `app.state.table_client`.
    """
    table_client = request.app.state.table_client
    repository = TaskRepository(table_client)
    return TaskService(repository, settings)


def get_bearer_token(request: Request) -> str | None:
    """Extracts the raw bearer token from the Authorization header, for forwarding
    unchanged to Profile Service during assign-time email validation.
    """
    auth_header = request.headers.get("authorization") or request.headers.get("Authorization")
    if not auth_header or not auth_header.lower().startswith("bearer "):
        return None
    return auth_header.split(" ", 1)[1].strip()
