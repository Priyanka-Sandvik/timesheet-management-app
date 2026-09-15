"""Unit tests: GET /admin/tasks `search` and `status` query params actually filter the
result set (previously silently ignored by the router - see task_service.py history).
"""
from __future__ import annotations

def _seed_tasks(fake_repo):
    import asyncio

    asyncio.run(fake_repo.upsert_template(
        "TASK-A", {"TaskName": "Digital Twin Rollout", "Description": "Project X", "Status": "Open"}
    ))
    asyncio.run(fake_repo.upsert_template(
        "TASK-B", {"TaskName": "Rotary Drills Maintenance", "Description": "Project Y", "Status": "OnHold"}
    ))
    asyncio.run(fake_repo.upsert_template(
        "TASK-C", {"TaskName": "Underground Drilling", "Description": "Project X", "Status": "Closed"}
    ))


def test_admin_list_with_no_filters_returns_everything(client_factory, fake_repo):
    _seed_tasks(fake_repo)
    client = client_factory(email="admin@sandvik.com", is_admin=True)

    response = client.get("/admin/tasks")
    assert response.status_code == 200
    codes = {t["taskCode"] for t in response.json()["tasks"]}
    assert codes == {"TASK-A", "TASK-B", "TASK-C"}


def test_admin_list_search_filters_by_task_name(client_factory, fake_repo):
    _seed_tasks(fake_repo)
    client = client_factory(email="admin@sandvik.com", is_admin=True)

    response = client.get("/admin/tasks", params={"search": "drilling"})
    assert response.status_code == 200
    codes = {t["taskCode"] for t in response.json()["tasks"]}
    assert codes == {"TASK-C"}


def test_admin_list_search_filters_by_description(client_factory, fake_repo):
    _seed_tasks(fake_repo)
    client = client_factory(email="admin@sandvik.com", is_admin=True)

    response = client.get("/admin/tasks", params={"search": "project x"})
    assert response.status_code == 200
    codes = {t["taskCode"] for t in response.json()["tasks"]}
    assert codes == {"TASK-A", "TASK-C"}


def test_admin_list_search_filters_by_task_code(client_factory, fake_repo):
    _seed_tasks(fake_repo)
    client = client_factory(email="admin@sandvik.com", is_admin=True)

    response = client.get("/admin/tasks", params={"search": "task-b"})
    assert response.status_code == 200
    codes = {t["taskCode"] for t in response.json()["tasks"]}
    assert codes == {"TASK-B"}


def test_admin_list_status_filter(client_factory, fake_repo):
    _seed_tasks(fake_repo)
    client = client_factory(email="admin@sandvik.com", is_admin=True)

    response = client.get("/admin/tasks", params={"status": "OnHold"})
    assert response.status_code == 200
    codes = {t["taskCode"] for t in response.json()["tasks"]}
    assert codes == {"TASK-B"}


def test_admin_list_search_and_status_combine(client_factory, fake_repo):
    _seed_tasks(fake_repo)
    client = client_factory(email="admin@sandvik.com", is_admin=True)

    response = client.get("/admin/tasks", params={"search": "project x", "status": "Closed"})
    assert response.status_code == 200
    codes = {t["taskCode"] for t in response.json()["tasks"]}
    assert codes == {"TASK-C"}


def test_admin_list_filtered_results_are_paginated(client_factory, fake_repo):
    import asyncio

    for i in range(5):
        asyncio.run(
            fake_repo.upsert_template(
                f"MATCH-{i}", {"TaskName": "Matching Task", "Description": "P", "Status": "Open"}
            )
        )
    client = client_factory(email="admin@sandvik.com", is_admin=True)

    response = client.get("/admin/tasks", params={"search": "matching", "pageSize": 2})
    assert response.status_code == 200
    body = response.json()
    assert len(body["tasks"]) == 2
    assert body["nextPage"] is not None

    response2 = client.get(
        "/admin/tasks", params={"search": "matching", "pageSize": 2, "continuationToken": body["nextPage"]}
    )
    assert response2.status_code == 200
    body2 = response2.json()
    assert len(body2["tasks"]) == 2
    first_page_codes = {t["taskCode"] for t in body["tasks"]}
    second_page_codes = {t["taskCode"] for t in body2["tasks"]}
    assert first_page_codes.isdisjoint(second_page_codes)
