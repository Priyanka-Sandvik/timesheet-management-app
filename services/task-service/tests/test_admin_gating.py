from __future__ import annotations

import io


def test_non_admin_gets_403_on_import(client_factory):
    client = client_factory(email="employee@sandvik.com", is_admin=False)
    files = {"file": ("tasks.csv", io.BytesIO(b"TaskCode,TaskName\nA,B\n"), "text/csv")}
    response = client.post("/admin/tasks/import", files=files)
    assert response.status_code == 403
    body = response.json()
    assert body["error"]["code"] == "FORBIDDEN"


def test_non_admin_gets_403_on_create(client_factory):
    client = client_factory(email="employee@sandvik.com", is_admin=False)
    response = client.post("/admin/tasks", json={"taskCode": "ABC", "taskName": "B"})
    assert response.status_code == 403


def test_non_admin_gets_403_on_assign(client_factory):
    client = client_factory(email="employee@sandvik.com", is_admin=False)
    response = client.post("/admin/tasks/ABC/assign", json={"emails": ["a@sandvik.com"]})
    assert response.status_code == 403


def test_non_admin_gets_403_on_admin_list(client_factory):
    client = client_factory(email="employee@sandvik.com", is_admin=False)
    response = client.get("/admin/tasks")
    assert response.status_code == 403


def test_non_admin_gets_403_on_update(client_factory):
    client = client_factory(email="employee@sandvik.com", is_admin=False)
    response = client.put("/admin/tasks/ABC", json={"status": "OnHold"})
    assert response.status_code == 403


def test_non_admin_gets_403_on_delete_template(client_factory):
    client = client_factory(email="employee@sandvik.com", is_admin=False)
    response = client.delete("/admin/tasks/ABC")
    assert response.status_code == 403


def test_non_admin_gets_403_on_unassign(client_factory):
    client = client_factory(email="employee@sandvik.com", is_admin=False)
    response = client.delete("/admin/tasks/ABC/assign/someone@sandvik.com")
    assert response.status_code == 403


def test_admin_can_reach_import_endpoint(client_factory):
    client = client_factory(email="admin@sandvik.com", is_admin=True)
    files = {"file": ("tasks.csv", io.BytesIO(b"TaskCode,TaskName\nA,B\n"), "text/csv")}
    response = client.post("/admin/tasks/import", files=files)
    assert response.status_code == 200
    body = response.json()
    assert body["imported"] == 1
    assert body["skipped"] == 0


def test_employee_can_reach_my_tasks(client_factory):
    client = client_factory(email="employee@sandvik.com", is_admin=False)
    response = client.get("/api/v1/tasks")
    assert response.status_code == 200
    assert response.json() == {"tasks": []}
