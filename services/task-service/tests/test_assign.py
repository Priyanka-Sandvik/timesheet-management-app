from __future__ import annotations

import io

import pytest

from app.services import profile_client as profile_client_module


def _import_one(client, task_code="TSK1", task_name="Do the thing", description="Some description"):
    csv_content = f"TaskCode,TaskName,Description\n{task_code},{task_name},{description}\n".encode()
    files = {"file": ("tasks.csv", io.BytesIO(csv_content), "text/csv")}
    response = client.post("/admin/tasks/import", files=files)
    assert response.status_code == 200
    return response


def test_assign_requires_existing_template(client_factory):
    client = client_factory(email="admin@sandvik.com", is_admin=True)
    response = client.post("/admin/tasks/NOPE/assign", json={"emails": ["a@sandvik.com"]})
    assert response.status_code == 404


def test_assign_creates_employee_row_copying_template_fields(client_factory):
    client = client_factory(email="admin@sandvik.com", is_admin=True)
    _import_one(client, "TSK1", "Do the thing", "First description")

    response = client.post("/admin/tasks/TSK1/assign", json={"emails": ["employee@sandvik.com"]})
    assert response.status_code == 200
    body = response.json()
    assert body["assigned"] == ["employee@sandvik.com"]
    assert body["skipped"] == []

    employee_client = client_factory(email="employee@sandvik.com", is_admin=False)
    my_tasks = employee_client.get("/api/v1/tasks").json()["tasks"]
    assert len(my_tasks) == 1
    assert my_tasks[0]["taskCode"] == "TSK1"
    assert my_tasks[0]["taskName"] == "Do the thing"
    assert my_tasks[0]["description"] == "First description"


def test_assign_is_idempotent_upsert(client_factory):
    client = client_factory(email="admin@sandvik.com", is_admin=True)
    _import_one(client, "TSK2", "First name")

    r1 = client.post("/admin/tasks/TSK2/assign", json={"emails": ["employee@sandvik.com"]})
    assert r1.status_code == 200
    assert r1.json()["assigned"] == ["employee@sandvik.com"]

    # Re-assigning the same email again should not error and should still report assigned.
    r2 = client.post("/admin/tasks/TSK2/assign", json={"emails": ["employee@sandvik.com"]})
    assert r2.status_code == 200
    assert r2.json()["assigned"] == ["employee@sandvik.com"]


def test_reassign_overwrites_template_fields_on_employee_row(client_factory):
    client = client_factory(email="admin@sandvik.com", is_admin=True)
    _import_one(client, "TSK3", "Original name")
    client.post("/admin/tasks/TSK3/assign", json={"emails": ["employee@sandvik.com"]})

    # Admin edits the template.
    update = client.put("/admin/tasks/TSK3", json={"taskName": "Renamed task", "sponsor": "New Sponsor"})
    assert update.status_code == 200

    # Re-assign (upsert) should now copy the NEW template fields onto the employee row.
    client.post("/admin/tasks/TSK3/assign", json={"emails": ["employee@sandvik.com"]})

    employee_client = client_factory(email="employee@sandvik.com", is_admin=False)
    my_tasks = employee_client.get("/api/v1/tasks").json()["tasks"]
    assert my_tasks[0]["taskName"] == "Renamed task"
    assert my_tasks[0]["sponsor"] == "New Sponsor"


def test_unassign_removes_only_employee_row(client_factory):
    client = client_factory(email="admin@sandvik.com", is_admin=True)
    _import_one(client, "TSK4", "Some task")
    client.post("/admin/tasks/TSK4/assign", json={"emails": ["employee@sandvik.com"]})

    response = client.delete("/admin/tasks/TSK4/assign/employee@sandvik.com")
    assert response.status_code == 204

    employee_client = client_factory(email="employee@sandvik.com", is_admin=False)
    assert employee_client.get("/api/v1/tasks").json()["tasks"] == []

    # Template row should be untouched (deleting a second time -> 404, not because template
    # is gone, but because the assignment row is already gone). client_factory mutates
    # shared dependency_overrides, so re-acquire the admin client before this call.
    admin_client = client_factory(email="admin@sandvik.com", is_admin=True)
    response2 = admin_client.delete("/admin/tasks/TSK4/assign/employee@sandvik.com")
    assert response2.status_code == 404


def test_delete_template_does_not_cascade_to_assignments(client_factory):
    client = client_factory(email="admin@sandvik.com", is_admin=True)
    _import_one(client, "TSK5", "Cascade check")
    client.post("/admin/tasks/TSK5/assign", json={"emails": ["employee@sandvik.com"]})

    response = client.delete("/admin/tasks/TSK5")
    assert response.status_code == 204

    employee_client = client_factory(email="employee@sandvik.com", is_admin=False)
    my_tasks = employee_client.get("/api/v1/tasks").json()["tasks"]
    assert len(my_tasks) == 1  # assignment row untouched despite template deletion


def test_search_filter(client_factory):
    client = client_factory(email="admin@sandvik.com", is_admin=True)
    _import_one(client, "TSK6", "Alpha project work")
    _import_one(client, "TSK7", "Beta project work")
    client.post("/admin/tasks/TSK6/assign", json={"emails": ["employee@sandvik.com"]})
    client.post("/admin/tasks/TSK7/assign", json={"emails": ["employee@sandvik.com"]})

    employee_client = client_factory(email="employee@sandvik.com", is_admin=False)

    search_resp = employee_client.get("/api/v1/tasks", params={"search": "alpha"})
    tasks = search_resp.json()["tasks"]
    assert len(tasks) == 1
    assert tasks[0]["taskCode"] == "TSK6"


def test_create_task_manually(client_factory):
    client = client_factory(email="admin@sandvik.com", is_admin=True)
    response = client.post(
        "/admin/tasks",
        json={
            "taskCode": "MANUAL1",
            "taskName": "Manually created task",
            "description": "A manual task",
            "sponsor": "Jane Sponsor",
            "costCentre": "CC001",
            "coeResponsible": "CoE Team",
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["taskCode"] == "MANUAL1"
    assert body["taskName"] == "Manually created task"
    assert body["status"] == "Open"


def test_create_task_conflict_on_duplicate_code(client_factory):
    client = client_factory(email="admin@sandvik.com", is_admin=True)
    payload = {"taskCode": "DUPE1", "taskName": "First"}
    r1 = client.post("/admin/tasks", json=payload)
    assert r1.status_code == 201

    r2 = client.post("/admin/tasks", json=payload)
    assert r2.status_code == 409
