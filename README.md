# Timesheet Management Application

Internal Sandvik tool: employees log weekly hours against tasks assigned to them; admins
manage the task catalog and export monthly timesheets to Excel.

Built per the three attached specification documents (architecture, UI/UX, workflows) as
literally as possible. Three independent Python/FastAPI microservices (Profile, Task,
Timelog), each owning its own Azure Table Storage table, called directly by a React +
TypeScript SPA with **no API gateway** in front. See `01-architecture-and-data-design.md`
for the full rationale.

```
timesheet-app/
├── docker-compose.yml        # azurite + all 3 services, for local dev
├── scripts/smoke_test.py     # end-to-end smoke test across all 3 services
├── services/
│   ├── profile-service/      # owns Users table: register/login/JWKS/me/admin user mgmt
│   ├── task-service/         # owns Tasks table: employee task list, admin import/assign/manage
│   └── timelog-service/      # owns Timesheet table: weekly grid, generate/copy/submit, monthly export
├── shared/py-common/         # JWT issue+verify, error envelope, table client factory, rate limiter, logging
├── frontend/                 # React + TypeScript + Vite SPA
└── infra/README.md           # Azure resources reference for deployment
```

---

## Quick start (local dev)

**Prerequisites:** Docker Desktop, Node.js 18+, Python 3.12 (only needed if you want to run
a service outside its container).

1. Copy each `.env.example` to `.env` in every `services/*/` folder (defaults work as-is for
   local dev against Azurite; only `ADMIN_EMAILS` is worth editing if you want a specific
   admin login).
2. From the repo root:

   ```bash
   docker-compose up --build
   ```

   This starts Azurite (Table Storage emulator) and all three services:
   - Profile Service → http://localhost:8001 (docs at `/docs`)
   - Task Service → http://localhost:8002
   - Timelog Service → http://localhost:8003

   Each service creates its own Table Storage table automatically on startup — no manual
   setup step beyond the `.env` files.

3. Run the end-to-end smoke test (registers a user, logs in as admin, imports+assigns a
   task, logs+submits an hour entry, exports a month) to confirm the whole chain works:

   ```bash
   pip install requests
   python scripts/smoke_test.py
   ```

4. Frontend:

   ```bash
   cd frontend
   cp .env.example .env.local   # points at localhost:8001/8002/8003 by default
   npm install
   npm run dev
   ```

   Open the printed local URL (typically http://localhost:5173). Register an account,
   or use "Login as Admin" with an email listed in Profile Service's `ADMIN_EMAILS`
   (default in `docker-compose.yml`: `admin1@sandvik.com` / any password you registered
   it with) to land on the Admin Console's Task Import screen.

---

## Running tests

Each service has its own virtualenv-friendly `pytest` suite (unit tests always run;
integration tests against Azurite auto-skip with a clear message if Azurite isn't reachable
on `127.0.0.1:10002`, rather than failing the whole suite):

```bash
cd shared/py-common && python -m venv .venv && .venv/Scripts/pip install -e ".[dev]" && .venv/Scripts/python -m pytest -q
cd services/profile-service && python -m venv .venv && .venv/Scripts/pip install -r requirements.txt && .venv/Scripts/python -m pytest -q
cd services/task-service     && python -m venv .venv && .venv/Scripts/pip install -r requirements.txt && .venv/Scripts/python -m pytest -q
cd services/timelog-service  && python -m venv .venv && .venv/Scripts/pip install -r requirements.txt && .venv/Scripts/python -m pytest -q
```

(`.venv/Scripts/...` is the Windows path; use `.venv/bin/...` on macOS/Linux.) To run the
integration tests for real, start Azurite first: `docker-compose up azurite`.

Frontend: `cd frontend && npm run build` (runs `tsc --noEmit` + `vite build`).

**Status as of this build:** all four Python test suites pass locally (unit tests green;
Azurite-dependent integration tests skip gracefully without a running emulator). Frontend
`npm install`, `tsc --noEmit`, and `npm run build` all pass cleanly.

---

## Building & pushing Docker images

Every service's `Dockerfile` must be built **from the repo root** (not from inside the
service folder), because each image needs `shared/py-common` inside its build context:

```bash
docker build -f services/profile-service/Dockerfile -t <registry>/profile-service:latest .
docker build -f services/task-service/Dockerfile     -t <registry>/task-service:latest .
docker build -f services/timelog-service/Dockerfile  -t <registry>/timelog-service:latest .
docker push <registry>/profile-service:latest
docker push <registry>/task-service:latest
docker push <registry>/timelog-service:latest
```

`docker-compose.yml` already does this correctly (`context: .`, `dockerfile: services/<name>/Dockerfile`).

---

## Deployment

See `infra/README.md` for the Azure resource list (Container Apps ×3, Static Web Apps,
Table Storage, Key Vault, Managed Identity, Application Insights — no Azure SQL, no Blob
Storage, no API Management). Each Container App reads `PORT` at runtime per Azure Container
Apps convention (already wired in each Dockerfile's `CMD`).

Environment variable reference: see `01-architecture-and-data-design.md` §11, and each
service's own `.env.example` for the authoritative, currently-implemented list (a few small
additive/tuning vars beyond §11 are called out inline there — see Assumptions below).

---

## Assumptions Made

This build was produced by two parallel AI build passes (backend, frontend) against the
same three specification documents, then reconciled by a follow-up pass. Everything below
was a genuine ambiguity in the source documents or a gap between the two passes — nothing
here silently diverges from the specs without being called out.

### Cross-service contract reconciliation
- **Task Service's assign-time email validation** originally assumed a
  `GET /api/v1/users/{email}` lookup route on Profile Service. That route doesn't exist in
  the architecture doc's §8.1 contract — only `GET /admin/users` (admin-only, optional
  `activeOnly` filter) does. **Fixed**: `services/task-service/app/services/profile_client.py`
  now calls `GET /admin/users` and matches the target email in-process. Behavior is
  unchanged (fail-open on Profile Service errors/unreachability, so assignment isn't
  blocked by a Profile Service outage — flip `fail_open=False` there if fail-closed is
  preferred).
- **Docker build context for `task-service`/`timelog-service`**: their `requirements.txt`
  files contain a `-e ../../shared/py-common` line for local dev venvs, which doesn't
  resolve inside a Docker build context. **Fixed**: both Dockerfiles now install
  `shared/py-common` explicitly as a first layer and strip the `-e` line before installing
  the rest of `requirements.txt` (mirroring how `profile-service`'s Dockerfile already did
  it) — this was caught during reconciliation, before it could break `docker-compose up`.

### Backend
- **Inactive-user login**: Profile Service blocks login (401) for deactivated users on both
  `/auth/login` and `/auth/login-as-admin`, rather than allowing login and relying on the
  frontend to react to `isActive`. See the comment at the top of
  `services/profile-service/app/services/auth_service.py` to flip this if the literal
  "deactivation only affects future admin exports" reading is preferred instead.
- **Email/admin-list comparisons are case-insensitive** throughout Profile Service.
- **`GET /admin/tasks` pagination** uses `pageSize` + an opaque `continuationToken` (Azure
  Table Storage SDK's native continuation token), echoed back as `nextPage`.
- **Task search filter** (`GET /api/v1/tasks?search=`) matches TaskName, TaskCode, or
  Description, case-insensitive substring, applied in-process (Table Storage has no native
  substring filter).
- **`DELETE /admin/tasks/{taskCode}/assign/{email}`** 404s if the assignment doesn't exist,
  rather than silently 204-ing, since the doc only specified the happy path.
- **Non-admin requesting another user's timesheet** (`GET`/`PUT` with a foreign `userId`) is
  rejected with `403`.
- **Editing a submitted week as a non-admin** returns `409 CONFLICT` (a state conflict, not
  an auth failure) rather than `403`.
- **Week status** on the grid response is derived from row data (any row `Status=Submitted`
  for that week ⇒ week is `Submitted`) — there's no separate week-status entity in the data
  model, so this couldn't be stored directly.
- **Monthly export sheet layout**: columns are `Task | 1 | 2 | ... | N | Total` (day-of-month
  headers), with weekly-subtotal rows inserted between task rows and a final grand-total
  row; zero-hour active employees still get a sheet with a placeholder row, per the UI
  spec's explicit requirement not to skip them.
- Both `task-service` and `timelog-service` were built and tested against **Python 3.14**
  (only version available in the build sandbox), not the specified 3.12. Everything ran
  cleanly; re-verify on 3.12 before shipping if that matters for your deployment target — no
  3.13+-only syntax was used deliberately, but worth a CI check.

### Frontend
- **Token storage**: `sessionStorage` (not pure in-memory) so a page reload doesn't
  silently log the user out — documented in `frontend/src/auth/tokenStorage.ts`. This is a
  pragmatic trade-off against the JWT's own short lifetime; there's still no refresh-token
  mechanism, so a session still ends when the token expires.
- **Remove-task-from-week**: the Timelog contract (§8.3) has no dedicated delete-entries
  route — only the bulk-upsert `PUT /entries`. Rather than invent an undocumented DELETE
  endpoint, the frontend's row-remove icon zeroes all 7 days for that task via the existing
  `PUT /entries` and hides all-zero rows client-side. This still only ever touches Timesheet
  rows for the current week, never the Tasks table, matching the UI spec's ownership rule.
- **"Project time category" / "Resource plan" columns** in the Logged Time Cards table
  aren't part of the Timesheet data model (§6), so they render as static "None" placeholders
  to match the mockup's layout without inventing new backend fields.
- Styling: plain CSS Modules throughout (no Tailwind mixed in), generic amber/gray palette
  and a placeholder wordmark — the Sandvik logo and exact brand colors were deliberately not
  reproduced, per the build prompt's instruction.
- The reference mockups show an "Add unassigned tasks to Time Sheet" link. The written UI
  spec (§4.4 v1-scope note) explicitly says not to build this mechanism in v1 and states
  that the written spec overrides the screenshot — so it was omitted entirely rather than
  rendered as a disabled affordance.

### Known scope boundaries (intentionally not built — see build prompt §9)
No Azure SQL/ORM, no Blob Storage, no forgot-password/MFA/account lockout/refresh tokens, no
API gateway, no async job/polling pattern for exports, no database-level admin-role column,
no mid-week "add a task not yet on this sheet" helper, no bulk group-assignment mechanism.

### Scaling note (per architecture doc §3 item 4)
The monthly export is a single synchronous request built entirely in memory. This is fine at
the assumed low-hundreds active-employee scale. If active employees exceed ~500, revisit
toward an async job+poll pattern — not built now, by design.

### Rate limiting caveat (per architecture doc §3 item 6)
Profile Service's in-process sliding-window rate limiter on `/auth/login`,
`/auth/login-as-admin`, and `/auth/register` is per-replica. If Profile Service ever scales
beyond a single Container Apps replica, the effective limit becomes
`AUTH_RATE_LIMIT_PER_MINUTE × replica_count`. Pin `minReplicas`/`maxReplicas` to 1 for
Profile Service if this must stay a hard global limit, or revisit with a shared store later.
