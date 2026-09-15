"""Integration tests against a real Azurite Table Storage emulator.

Skips gracefully (does not fail the suite) if Azurite isn't reachable at
127.0.0.1:10002, per the Azurite well-known connection string in .env.example.
"""
from __future__ import annotations

import socket
import uuid

import pytest

AZURITE_HOST = "127.0.0.1"
AZURITE_PORT = 10002
AZURITE_CONNECTION_STRING = (
    "DefaultEndpointsProtocol=http;AccountName=devstoreaccount1;"
    "AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;"
    "TableEndpoint=http://127.0.0.1:10002/devstoreaccount1;"
)


def _azurite_reachable() -> bool:
    try:
        with socket.create_connection((AZURITE_HOST, AZURITE_PORT), timeout=0.5):
            return True
    except OSError:
        return False


pytestmark = pytest.mark.integration


@pytest.fixture
def user_repository():
    if not _azurite_reachable():
        pytest.skip("Azurite not reachable at 127.0.0.1:10002")

    from py_common.core.table_client import ensure_table_exists, get_table_service_client

    from app.repositories.user_repository import UserRepository

    table_name = f"UsersTest{uuid.uuid4().hex[:8]}"
    service_client = get_table_service_client(environment="local", connection_string=AZURITE_CONNECTION_STRING)
    ensure_table_exists(service_client, table_name)
    table_client = service_client.get_table_client(table_name)
    try:
        yield UserRepository(table_client)
    finally:
        service_client.delete_table(table_name)


def test_create_and_get_by_email_roundtrip(user_repository):
    created = user_repository.create(
        email="integration.user@sandvik.com", full_name="Integration User", password_hash="fakehash"
    )
    fetched = user_repository.get_by_email("integration.user@sandvik.com")

    assert fetched is not None
    assert fetched.email == created.email
    assert fetched.full_name == "Integration User"
    assert fetched.password_hash == "fakehash"
    assert fetched.is_active is True


def test_create_duplicate_raises_resource_exists_error(user_repository):
    from azure.core.exceptions import ResourceExistsError

    user_repository.create(email="dup@sandvik.com", full_name="Dup", password_hash="h")
    with pytest.raises(ResourceExistsError):
        user_repository.create(email="dup@sandvik.com", full_name="Dup", password_hash="h")


def test_update_active_status(user_repository):
    user_repository.create(email="toggle@sandvik.com", full_name="Toggle", password_hash="h")
    updated = user_repository.update_active_status("toggle@sandvik.com", False)
    assert updated is not None
    assert updated.is_active is False

    fetched = user_repository.get_by_email("toggle@sandvik.com")
    assert fetched.is_active is False


def test_update_active_status_unknown_user_returns_none(user_repository):
    assert user_repository.update_active_status("nobody@sandvik.com", False) is None


def test_list_all_and_active_only(user_repository):
    user_repository.create(email="active1@sandvik.com", full_name="Active One", password_hash="h")
    user_repository.create(email="inactive1@sandvik.com", full_name="Inactive One", password_hash="h")
    user_repository.update_active_status("inactive1@sandvik.com", False)

    all_users = user_repository.list_all(active_only=False)
    active_users = user_repository.list_all(active_only=True)

    assert len(all_users) == 2
    assert len(active_users) == 1
    assert active_users[0].email == "active1@sandvik.com"
