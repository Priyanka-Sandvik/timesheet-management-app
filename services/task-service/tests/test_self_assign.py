from __future__ import annotations

import io


def _import_one(admin_client, task_code="TSK1", task_name="Do the thing", status="Open"):
    csv_content = f"TaskCode,TaskName,Status\n{task_code},{task_name},{status}\n".encode()
    files = {"file": ("tasks.csv", io.BytesIO(csv_content), "text/csv")}
    response = admin_client.post("/admin/tasks/import", files=files)
    assert response.status_code == 200
    return response


def test_catalog_lists_open_templates_not_yet_assigned(client_factory):
    admin_client = client_factory(email="admin@sandvik.com", is_admin=True)
    _import_one(admin_client, "TSK1", "Alpha project")
    _import_one(admin_client, "TSK2", "Beta project")

    employee_client = client_factory(email="employee@sandvik.com", is_admin=False)
    catalog = employee_client.get("/api/v1/tasks/catalog").json()["tasks"]
    assert {t["taskCode"] for t in catalog} == {"TSK1", "TSK2"}

    # Assign one, then it should drop out of the catalog.
    employee_client.post("/api/v1/tasks/TSK1/assign-self")
    catalog_after = employee_client.get("/api/v1/tasks/catalog").json()["tasks"]
    assert {t["taskCode"] for t in catalog_after} == {"TSK2"}


def test_catalog_excludes_non_open_templates(client_factory):
    admin_client = client_factory(email="admin@sandvik.com", is_admin=True)
    _import_one(admin_client, "TSK3", "On hold project", status="OnHold")
    _import_one(admin_client, "TSK4", "Closed project", status="Closed")
    _import_one(admin_client, "TSK5", "Open project", status="Open")

    employee_client = client_factory(email="employee@sandvik.com", is_admin=False)
    catalog = employee_client.get("/api/v1/tasks/catalog").json()["tasks"]
    assert {t["taskCode"] for t in catalog} == {"TSK5"}


def test_self_assign_creates_own_assignment_row(client_factory):
    admin_client = client_factory(email="admin@sandvik.com", is_admin=True)
    _import_one(admin_client, "TSK6", "Gamma project")

    employee_client = client_factory(email="employee@sandvik.com", is_admin=False)
    response = employee_client.post("/api/v1/tasks/TSK6/assign-self")
    assert response.status_code == 201
    body = response.json()
    assert body["taskCode"] == "TSK6"
    assert body["taskName"] == "Gamma project"

    my_tasks = employee_client.get("/api/v1/tasks").json()["tasks"]
    assert len(my_tasks) == 1
    assert my_tasks[0]["taskCode"] == "TSK6"


def test_self_assign_rejects_unknown_task(client_factory):
    employee_client = client_factory(email="employee@sandvik.com", is_admin=False)
    response = employee_client.post("/api/v1/tasks/NOPE/assign-self")
    assert response.status_code == 404


def test_self_assign_rejects_non_open_task(client_factory):
    admin_client = client_factory(email="admin@sandvik.com", is_admin=True)
    _import_one(admin_client, "TSK7", "On hold project", status="OnHold")

    employee_client = client_factory(email="employee@sandvik.com", is_admin=False)
    response = employee_client.post("/api/v1/tasks/TSK7/assign-self")
    assert response.status_code == 409


def test_self_assign_rejects_duplicate_assignment(client_factory):
    admin_client = client_factory(email="admin@sandvik.com", is_admin=True)
    _import_one(admin_client, "TSK8", "Delta project")

    employee_client = client_factory(email="employee@sandvik.com", is_admin=False)
    first = employee_client.post("/api/v1/tasks/TSK8/assign-self")
    assert first.status_code == 201

    second = employee_client.post("/api/v1/tasks/TSK8/assign-self")
    assert second.status_code == 409


def test_self_assign_does_not_require_admin(client_factory):
    """Confirms self-assign is on the employee-facing router (require_user), not gated by
    require_admin - an employee's own assignment must not need admin privileges.
    """
    admin_client = client_factory(email="admin@sandvik.com", is_admin=True)
    _import_one(admin_client, "TSK9", "Epsilon project")

    employee_client = client_factory(email="employee@sandvik.com", is_admin=False)
    response = employee_client.post("/api/v1/tasks/TSK9/assign-self")
    assert response.status_code == 201


def test_self_unassign_removes_own_assignment(client_factory):
    admin_client = client_factory(email="admin@sandvik.com", is_admin=True)
    _import_one(admin_client, "TSK10", "Zeta project")

    employee_client = client_factory(email="employee@sandvik.com", is_admin=False)
    employee_client.post("/api/v1/tasks/TSK10/assign-self")

    response = employee_client.delete("/api/v1/tasks/TSK10/assign-self")
    assert response.status_code == 204

    my_tasks = employee_client.get("/api/v1/tasks").json()["tasks"]
    assert my_tasks == []


def test_self_unassign_reappears_in_catalog(client_factory):
    admin_client = client_factory(email="admin@sandvik.com", is_admin=True)
    _import_one(admin_client, "TSK11", "Eta project")

    employee_client = client_factory(email="employee@sandvik.com", is_admin=False)
    employee_client.post("/api/v1/tasks/TSK11/assign-self")
    employee_client.delete("/api/v1/tasks/TSK11/assign-self")

    catalog = employee_client.get("/api/v1/tasks/catalog").json()["tasks"]
    assert {t["taskCode"] for t in catalog} == {"TSK11"}


def test_self_unassign_rejects_when_not_assigned(client_factory):
    admin_client = client_factory(email="admin@sandvik.com", is_admin=True)
    _import_one(admin_client, "TSK12", "Theta project")

    employee_client = client_factory(email="employee@sandvik.com", is_admin=False)
    response = employee_client.delete("/api/v1/tasks/TSK12/assign-self")
    assert response.status_code == 404


def test_self_unassign_only_removes_caller_own_row(client_factory):
    admin_client = client_factory(email="admin@sandvik.com", is_admin=True)
    _import_one(admin_client, "TSK13", "Iota project")
    admin_client.post("/admin/tasks/TSK13/assign", json={"emails": ["coworker@sandvik.com"]})

    employee_client = client_factory(email="employee@sandvik.com", is_admin=False)
    employee_client.post("/api/v1/tasks/TSK13/assign-self")
    employee_client.delete("/api/v1/tasks/TSK13/assign-self")

    coworker_client = client_factory(email="coworker@sandvik.com", is_admin=False)
    my_tasks = coworker_client.get("/api/v1/tasks").json()["tasks"]
    assert len(my_tasks) == 1
    assert my_tasks[0]["taskCode"] == "TSK13"


def test_self_unassign_does_not_require_admin(client_factory):
    admin_client = client_factory(email="admin@sandvik.com", is_admin=True)
    _import_one(admin_client, "TSK14", "Kappa project")

    employee_client = client_factory(email="employee@sandvik.com", is_admin=False)
    employee_client.post("/api/v1/tasks/TSK14/assign-self")

    response = employee_client.delete("/api/v1/tasks/TSK14/assign-self")
    assert response.status_code == 204
