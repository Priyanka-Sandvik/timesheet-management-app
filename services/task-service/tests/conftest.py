from __future__ import annotations

import datetime as dt
from typing import Any

import pytest
from fastapi.testclient import TestClient

from py_common.core.jwt_verify import AuthenticatedUser

from app.config import Settings
from app.core.deps import get_bearer_token, get_task_service, require_admin, require_user
from app.main import app
from app.services.task_service import TaskService

UNASSIGNED = "UNASSIGNED"


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class FakeTaskRepository:
    """In-memory stand-in for TaskRepository, mirroring its async interface exactly."""

    def __init__(self) -> None:
        # keyed by (partition_key, row_key) -> entity dict
        self.store: dict[tuple[str, str], dict[str, Any]] = {}

    async def get_template(self, task_code: str):
        return self.store.get((UNASSIGNED, task_code))

    async def upsert_template(self, task_code: str, fields: dict[str, Any]):
        return await self._upsert(UNASSIGNED, task_code, fields)

    async def delete_template(self, task_code: str) -> bool:
        return self._delete(UNASSIGNED, task_code)

    async def get_assignment(self, email: str, task_code: str):
        return self.store.get((email, task_code))

    async def upsert_assignment(self, email: str, task_code: str, fields: dict[str, Any]):
        return await self._upsert(email, task_code, fields)

    async def delete_assignment(self, email: str, task_code: str) -> bool:
        return self._delete(email, task_code)

    async def list_by_partition(self, partition_key: str):
        return [e for (pk, _rk), e in self.store.items() if pk == partition_key]

    async def list_all(self, page_size: int, continuation_token: str | None):
        items = list(self.store.values())
        start = int(continuation_token) if continuation_token else 0
        page = items[start : start + page_size]
        next_token = str(start + page_size) if start + page_size < len(items) else None
        return page, next_token

    async def list_all_unpaged(self, status: str | None = None):
        items = list(self.store.values())
        if status:
            items = [e for e in items if e.get("Status") == status]
        return items

    async def _upsert(self, partition_key: str, row_key: str, fields: dict[str, Any]):
        key = (partition_key, row_key)
        existing = self.store.get(key)
        now = _now()
        entity: dict[str, Any] = {
            "PartitionKey": partition_key,
            "RowKey": row_key,
            "CreatedAt": existing["CreatedAt"] if existing and existing.get("CreatedAt") else now,
            "UpdatedAt": now,
        }
        entity.update(fields)
        self.store[key] = entity
        return entity

    def _delete(self, partition_key: str, row_key: str) -> bool:
        key = (partition_key, row_key)
        if key in self.store:
            del self.store[key]
            return True
        return False


@pytest.fixture
def fake_repo() -> FakeTaskRepository:
    return FakeTaskRepository()


@pytest.fixture
def settings() -> Settings:
    # Unit tests disable the optional Profile Service email-validation call on assign so
    # they never make real network requests; that behavior is covered by mocking
    # profile_client directly where needed (see test_assign.py).
    return Settings(_env_file=None, VALIDATE_ASSIGN_EMAILS_WITH_PROFILE_SERVICE=False)


def _override_user(email: str, is_admin: bool):
    async def _dep():
        return AuthenticatedUser(email=email, is_admin=is_admin, full_name=None, raw_claims={})

    return _dep


@pytest.fixture
def client_factory(fake_repo, settings):
    """Returns a function that builds a TestClient acting as a given user, backed by the
    shared in-memory fake_repo (so state persists across calls within one test).
    """

    def _make(email: str = "employee@sandvik.com", is_admin: bool = False) -> TestClient:
        service = TaskService(fake_repo, settings)

        app.dependency_overrides[get_task_service] = lambda: service
        app.dependency_overrides[require_user] = _override_user(email, is_admin)
        app.dependency_overrides[get_bearer_token] = lambda: "fake-token"
        if is_admin:
            app.dependency_overrides[require_admin] = _override_user(email, is_admin)
        else:

            async def _forbidden():
                from fastapi import HTTPException, status

                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={"code": "FORBIDDEN", "message": "Admin privileges required"},
                )

            app.dependency_overrides[require_admin] = _forbidden

        return TestClient(app)

    yield _make
    app.dependency_overrides.clear()
