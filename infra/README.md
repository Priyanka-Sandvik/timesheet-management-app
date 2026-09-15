# Infrastructure Notes

This app is deploy-ready for the Azure resources below (see
`01-architecture-and-data-design.md` §10 for the canonical table). Bicep/Terraform
templates are not included — this is a reference for manual or scripted provisioning.

| Resource | Purpose | Notes |
|---|---|---|
| Azure Static Web Apps | Hosts the `frontend/` React SPA | Build command `npm run build`, output dir `dist`. `staticwebapp.config.json` is already in `frontend/`. |
| Azure Container Apps ×3 (Consumption plan, scale-to-zero, public HTTPS ingress) | Profile Service, Task Service, Timelog Service | Each reads `PORT` at runtime (Container Apps convention); each Dockerfile already respects this. No gateway/reverse-proxy in front — each app gets its own public ingress. |
| Azure Container Registry | Stores the 3 Docker images | Build from repo root per each service's Dockerfile comment (`shared/py-common` must be in the build context). |
| Azure Table Storage (1 Storage Account, 3 tables: `Users`, `Tasks`, `Timesheet`) | Data layer | One table per service; each service only ever touches its own table. |
| Azure Key Vault | JWT RSA signing key (Profile Service only) | `KeyVaultKeySource` in `shared/py-common/py_common/core/jwt_issue.py` is currently a stub (raises `NotImplementedError`) — implement it, then flip `USE_LOCAL_KEY=false` and set `KEY_VAULT_URL`/`JWT_KEY_NAME` in Profile Service's env. This is documented as a one-line change by design. |
| Managed Identity ×3 (system-assigned) | One per Container App | RBAC scoped to: its own Table Storage table (`Storage Table Data Contributor` or narrower), and — Profile Service only — read access to the Key Vault secret/key. |
| Application Insights | Logging/observability | Wire the connection string into each service's env; `shared/py-common`'s structured logging helper emits JSON logs suitable for ingestion. |

**Not provisioned, by design:** Azure SQL Database, Azure Blob Storage, Microsoft Entra ID
app registration, any email-sending service, Azure API Management or any other API gateway.

## Environment variables per Container App

Set from each service's `.env.example` as a starting point; in Azure, these become
Container App environment variables/secrets (secrets for anything sensitive — though at
this design, the only real secret is the JWT signing key, which lives in Key Vault, not an
env var). See the root README's "Assumptions Made" section for a couple of small env vars
added beyond the architecture doc's exact §11 list (documented inline in each
`.env.example` under an "extra" heading).

## CORS

Each service's `CORS_ALLOWED_ORIGIN` must be set to the deployed Static Web App's origin.
There is no gateway to centralize this — it is enforced independently per service.

## Admin allow-list

`ADMIN_EMAILS` (Profile Service only) is an operational/ops-runbook concern, not a
code-deploy concern: adding/removing an admin = update the Container App's environment
variable + restart Profile Service (zero-downtime rolling restart on Container Apps).

## Scaling notes

- Profile Service's auth-route rate limiter is per-replica and in-memory — pin
  `minReplicas`/`maxReplicas` to 1 if a hard global rate limit matters, or revisit with a
  shared store later (see root README).
- The monthly export endpoint is synchronous and builds the whole workbook in memory before
  streaming it. Fine at low-hundreds active-employee scale; if that count exceeds ~500,
  revisit toward an async job+poll pattern (deliberately not built for v1).
