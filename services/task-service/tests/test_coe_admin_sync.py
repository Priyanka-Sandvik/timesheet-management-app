from __future__ import annotations

import pytest

from app.config import Settings
from app.core.deps import get_task_service
from app.main import app
from app.services import task_service as task_service_module
from app.services.task_service import TaskService


@pytest.fixture
def sync_calls(monkeypatch, fake_repo):
    """Turns the CoE-admin sync on and records what would be sent to Profile Service."""
    calls: list[list[str]] = []

    async def _fake_sync(*, emails, bearer_token, base_url, timeout_seconds):
        assert bearer_token == "fake-token"
        calls.append(emails)
        return True

    monkeypatch.setattr(task_service_module, "sync_coe_admins", _fake_sync)
    return calls


@pytest.fixture
def admin_client(client_factory, fake_repo, sync_calls):
    client = client_factory(email="admin@sandvik.com", is_admin=True)
    service = TaskService(fake_repo, Settings(_env_file=None, SYNC_COE_ADMINS_WITH_PROFILE_SERVICE=True))
    app.dependency_overrides[get_task_service] = lambda: service
    return client


def _create(client, code, coe, status="Open"):
    response = client.post(
        "/admin/tasks", json={"taskCode": code, "taskName": code, "coeResponsible": coe, "status": status}
    )
    assert response.status_code == 201
    return response


def test_create_task_syncs_coe_email_lowercased(admin_client, sync_calls):
    _create(admin_client, "T1", "Coe.One@Sandvik.com")
    assert sync_calls == [["coe.one@sandvik.com"]]


def test_only_open_and_onhold_tasks_count(admin_client, sync_calls):
    _create(admin_client, "T1", "open@sandvik.com", "Open")
    _create(admin_client, "T2", "hold@sandvik.com", "OnHold")
    _create(admin_client, "T3", "closed@sandvik.com", "Closed")
    assert sync_calls[-1] == ["hold@sandvik.com", "open@sandvik.com"]


def test_free_text_coe_is_ignored(admin_client, sync_calls):
    _create(admin_client, "T1", "CoE Team")
    assert sync_calls[-1] == []


def test_changing_coe_removes_old_person_and_adds_new(admin_client, sync_calls):
    _create(admin_client, "T1", "old@sandvik.com")
    admin_client.put("/admin/tasks/T1", json={"coeResponsible": "new@sandvik.com"})
    assert sync_calls[-1] == ["new@sandvik.com"]


def test_person_stays_admin_while_another_active_task_remains(admin_client, sync_calls):
    _create(admin_client, "T1", "coe@sandvik.com")
    _create(admin_client, "T2", "coe@sandvik.com")
    admin_client.put("/admin/tasks/T1", json={"status": "Closed"})
    assert sync_calls[-1] == ["coe@sandvik.com"]
    admin_client.put("/admin/tasks/T2", json={"status": "Closed"})
    assert sync_calls[-1] == []


def test_delete_and_import_resync(admin_client, sync_calls):
    _create(admin_client, "T1", "coe@sandvik.com")
    admin_client.delete("/admin/tasks/T1")
    assert sync_calls[-1] == []

    csv_content = b"TaskCode,TaskName,CoE Responsible\nT9,Imported,Imp@Sandvik.com\n"
    response = admin_client.post("/admin/tasks/import", files={"file": ("t.csv", csv_content, "text/csv")})
    assert response.status_code == 200
    assert sync_calls[-1] == ["imp@sandvik.com"]


def test_profile_service_failure_does_not_fail_task_save(monkeypatch, client_factory, fake_repo):
    async def _boom(**_kwargs):
        raise RuntimeError("profile service down")

    monkeypatch.setattr(task_service_module, "sync_coe_admins", _boom)
    client = client_factory(email="admin@sandvik.com", is_admin=True)
    service = TaskService(fake_repo, Settings(_env_file=None, SYNC_COE_ADMINS_WITH_PROFILE_SERVICE=True))
    app.dependency_overrides[get_task_service] = lambda: service
    assert _create(client, "T1", "coe@sandvik.com").status_code == 201
