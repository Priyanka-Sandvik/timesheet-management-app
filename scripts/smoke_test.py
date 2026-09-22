#!/usr/bin/env python3
"""End-to-end smoke test for the Timesheet Management Application.

Exercises the full chain across all three services, running against `docker-compose up`
(default base URLs below assume the host-mapped ports 8001/8002/8003):

  1. Register an employee, log in.
  2. Log in as admin (fixed credentials, must be in Profile Service's ADMIN_CREDENTIALS -
     never registered as a user).
  3. Admin imports a task (in-memory CSV), assigns it to the employee.
  4. Employee generates the current week's time cards, logs an hour entry, submits.
  5. Admin exports the current month and confirms a non-empty .xlsx comes back.

Usage:
    python scripts/smoke_test.py

Exit code 0 on success, non-zero (with a clear message) on the first failing step.
Requires only the standard library + `requests` (see requirements.txt at repo root, or
`pip install requests` ad hoc).
"""
from __future__ import annotations

import io
import sys
import time
import uuid
from datetime import date, timedelta

try:
    import requests
except ImportError:  # pragma: no cover
    print("This script requires the `requests` package: pip install requests", file=sys.stderr)
    sys.exit(1)

PROFILE_BASE = "http://localhost:8001"
TASK_BASE = "http://localhost:8002"
TIMELOG_BASE = "http://localhost:8003"

# Must match an entry in Profile Service's ADMIN_CREDENTIALS env var (see docker-compose.yml
# / .env). Default docker-compose.yml value includes admin1@sandvik.com / "Admin@123".
ADMIN_EMAIL = "admin1@sandvik.com"
ADMIN_PASSWORD = "Admin@123"  # plaintext, acceptable since stored in Key Vault

PASSWORD = "abcdefgh"


def _fail(step: str, response: requests.Response) -> None:
    print(f"\n[FAIL] {step}: HTTP {response.status_code}\n{response.text}", file=sys.stderr)
    sys.exit(1)


def _ok(step: str) -> None:
    print(f"[OK]   {step}")


def wait_for(url: str, name: str, timeout_s: int = 60) -> None:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            r = requests.get(url, timeout=3)
            if r.status_code < 500:
                _ok(f"{name} is reachable")
                return
        except requests.RequestException:
            pass
        time.sleep(2)
    print(f"[FAIL] {name} did not become reachable within {timeout_s}s at {url}", file=sys.stderr)
    sys.exit(1)


def monday_of_current_week() -> date:
    today = date.today()
    return today - timedelta(days=today.weekday())


def main() -> None:
    print("== Timesheet Management Application: end-to-end smoke test ==\n")

    wait_for(f"{PROFILE_BASE}/.well-known/jwks.json", "Profile Service")
    wait_for(f"{TASK_BASE}/docs", "Task Service")
    wait_for(f"{TIMELOG_BASE}/docs", "Timelog Service")

    # --- 1. Register + login as a plain employee ---
    employee_email = f"smoketest.{uuid.uuid4().hex[:8]}@sandvik.com"
    r = requests.post(
        f"{PROFILE_BASE}/auth/register",
        json={"email": employee_email, "fullName": "Smoke Test Employee", "password": PASSWORD},
    )
    if r.status_code != 201:
        _fail("register employee", r)
    _ok(f"registered employee {employee_email}")

    r = requests.post(f"{PROFILE_BASE}/auth/login", json={"email": employee_email, "password": PASSWORD})
    if r.status_code != 200:
        _fail("login employee", r)
    employee_token = r.json()["access_token"]
    _ok("logged in as employee")

    # --- 2. Log in as admin (fixed credentials, no registration) ---
    r = requests.post(
        f"{PROFILE_BASE}/auth/login-as-admin", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    )
    if r.status_code != 200:
        _fail(
            "login-as-admin (is ADMIN_EMAIL:ADMIN_PASSWORD in the Profile Service's "
            "ADMIN_CREDENTIALS env var?)",
            r,
        )
    admin_token = r.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    _ok(f"logged in as admin ({ADMIN_EMAIL})")

    # --- 3. Admin imports a task, assigns it to the employee ---
    task_code = f"SMOKE{uuid.uuid4().hex[:6].upper()}"
    csv_body = (
        "TaskCode,TaskName,Description,Sponsor,CostCentre,CoEResponsible,Status\n"
        f"{task_code},Smoke Test Task,Smoke test description,Jane Sponsor,CC001,CoE Team,Open\n"
    ).encode("utf-8")
    r = requests.post(
        f"{TASK_BASE}/admin/tasks/import",
        headers=admin_headers,
        files={"file": ("smoke_test_tasks.csv", io.BytesIO(csv_body), "text/csv")},
    )
    if r.status_code != 200 or r.json().get("imported", 0) < 1:
        _fail("import task", r)
    _ok(f"imported task {task_code}")

    r = requests.post(
        f"{TASK_BASE}/admin/tasks/{task_code}/assign",
        headers=admin_headers,
        json={"emails": [employee_email]},
    )
    if r.status_code != 200:
        _fail("assign task", r)
    _ok(f"assigned {task_code} to {employee_email}")

    # --- 4. Employee generates the week, logs an hour entry, submits ---
    week_start = monday_of_current_week().isoformat()
    employee_headers = {"Authorization": f"Bearer {employee_token}"}

    r = requests.post(
        f"{TIMELOG_BASE}/api/v1/timesheet/generate",
        headers=employee_headers,
        params={"weekStart": week_start},
    )
    if r.status_code != 200:
        _fail("generate time cards", r)
    _ok(f"generated time cards for week {week_start}")

    r = requests.put(
        f"{TIMELOG_BASE}/api/v1/timesheet/entries",
        headers=employee_headers,
        json={
            "weekStart": week_start,
            "entries": [{"taskCode": task_code, "entryDate": week_start, "hours": 4.5}],
        },
    )
    if r.status_code != 200:
        _fail("log hour entry", r)
    _ok("logged 4.5 hours against the task on Monday")

    r = requests.post(
        f"{TIMELOG_BASE}/api/v1/timesheet/submit",
        headers=employee_headers,
        params={"weekStart": week_start},
    )
    if r.status_code != 200:
        _fail("submit week", r)
    _ok("submitted the week")

    # --- 5. Admin exports the current month ---
    month = date.today().strftime("%Y-%m")
    r = requests.get(
        f"{TIMELOG_BASE}/admin/timesheet/export/monthly",
        headers=admin_headers,
        params={"month": month},
    )
    if r.status_code != 200 or len(r.content) < 100:
        _fail("monthly export", r)
    _ok(f"exported {month} ({len(r.content)} bytes of .xlsx)")

    print("\n== All smoke-test steps passed. ==")


if __name__ == "__main__":
    main()
