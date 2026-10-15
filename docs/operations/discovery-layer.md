# Discovery layer operations runbook

How to run GovData and PVOG catalogue ingest, FIM/LeiKa enrich, admin review, and machine emit to
`pending` suggestions on a laptop. Canon URLs, ingest vs enrich roles, and staging contract pointers:
[`government-data-sources.md`](../discovery/government-data-sources.md).

**Chief-of-staff orchestration** (chapter order, loop branch, release) is documented separately in
[`loops/discovery-layer.md`](loops/discovery-layer.md) — use this runbook for hands-on operations only.

External portals and proxy notes:
[`docs/discovery/government-data-sources.md`](../discovery/government-data-sources.md).

## Prerequisites

- Local stack per [`local-development.md`](local-development.md) (Postgres, API on port 8000, web on 5173).
- Discovery staging migration applied: `cd apps/api && alembic upgrade head`.
- Germany country jurisdiction available for federal ingest — the MVP seed includes
  `11111111-1111-1111-1111-111111111101` (`python -m scripts.seed_documents` after migrations).

## Environment variables

Set these in `apps/api/.env` (API + admin) and export the same `DISCOVERY_API_*` values for
`apps/discovery-ingest` CLI runs. See also [`apps/api/.env.example`](../../apps/api/.env.example).

| Variable | Where | Purpose |
| --- | --- | --- |
| `DISCOVERY_ADMIN_EMAILS` | API | Comma-separated emails allowed to call `/api/v1/discovery/admin/*` and open `/admin/discovery/*` in the web app |
| `DISCOVERY_API_URL` | Ingest CLIs | Machine API base, e.g. `http://localhost:8000/api/v1/discovery/machine` |
| `DISCOVERY_API_KEY` | Ingest CLIs | Plaintext crawler key (`X-API-Key`) with access to discovery machine routes |
| `DISCOVERY_MACHINE_OPT_IN` | API (optional) | When `1`, enables machine routes even if `DISCOVERY_ADMIN_EMAILS` is empty (dev only) |

### Issue a discovery machine API key

There is no HTTP endpoint for key issuance. From `apps/api`:

```bash
python -m scripts.issue_api_key --name discovery-ingest-local
```

Copy the printed `rt_…` value into `DISCOVERY_API_KEY`. Revocation and rotation follow
[`auth-setup.md` §7](auth-setup.md#7-issue-and-revoke-crawler-keys).

### Admin allowlist

Add operator emails to `DISCOVERY_ADMIN_EMAILS` (lowercase is normalized). Sign in to the web app with
Supabase using one of those addresses before visiting admin routes.

## Corporate network (ingest only)

GovData CKAN, PVOG, and FIM/LeiKa calls from your laptop usually need the corporate HTTP proxy.
The local Redtape API stays direct via `NO_PROXY`.

Export before live ingest or `curl` checks (values from
[corporate-build-env.md](../../.cursor/skills/chief-of-staff/corporate-build-env.md)):

```bash
export HTTP_PROXY=http://185.46.212.88:9480/
export HTTPS_PROXY=http://185.46.212.88:9480/
export NO_PROXY=localhost,127.0.0.1,.rsint.net,.rsext.net
```

CI and unit tests use fixtures only — they do not call GovData, FITKO, or `fimportal.de`.

## Manual sequence

Run steps in order for a full local pass. Fixture paths and field names:
[`government-data-sources.md`](../discovery/government-data-sources.md).

### 1. Migrate and seed

```bash
docker compose up -d --wait db
cd apps/api
source .venv/bin/activate
alembic upgrade head
python -m scripts.seed_documents   # if jurisdictions are not already present
```

### 2. GovData OZG ingest (fixture or export file)

From `apps/discovery-ingest` with venv and deps installed (`uv pip install -e ".[dev]"`):

```bash
export DISCOVERY_API_URL=http://localhost:8000/api/v1/discovery/machine
export DISCOVERY_API_KEY=rt_<your-key>

python -m discovery_ingest govdata run \
  --input path/to/ozg-leistungen-page.json \
  --jurisdiction-id 11111111-1111-1111-1111-111111111101
```

Live CKAN export: see canon § GovData; verify connectivity with proxy env set.

### 3. PVOG Suchdienst ingest

```bash
python -m discovery_ingest pvog run \
  --jurisdiction-id 11111111-1111-1111-1111-111111111101
```

Uses `PVOG_API_BASE_URL` when overridden; default host is in
[`discovery_ingest/config.py`](../../apps/discovery-ingest/discovery_ingest/config.py).

### 4. FIM / LeiKa enrich

Save an admin catalogue JSON snapshot (array of rows from
`GET /api/v1/discovery/admin/catalogue`, or a test fixture under
`apps/discovery-ingest/tests/fixtures/`). Then:

```bash
python -m discovery_ingest fim enrich \
  --catalogue-service-id <uuid> \
  --catalogue-export path/to/catalogue_export.json \
  --input path/to/steckbrief.json

python -m discovery_ingest leika enrich \
  --catalogue-service-id <uuid> \
  --catalogue-export path/to/catalogue_export.json \
  --input path/to/stammtext.json
```

### 5. Admin review (smoke)

With `./scripts/dev-up.sh` or manual API + web:

| Surface | URL / route |
| --- | --- |
| Crawler queue | Web: [`/admin/discovery/tasks`](http://localhost:5173/admin/discovery/tasks) |
| Catalogue index | `/admin/discovery/catalogue` |
| Pipeline + emit preview | `/admin/discovery/pipeline/<catalogue-service-id>` |

Confirm tasks list loads, catalogue rows appear after ingest, and pipeline shows events/claims for a row
you enriched.

Admin JSON API (session JWT, allowlisted email): prefix
`http://localhost:8000/api/v1/discovery/admin` — e.g. `GET …/catalogue`, `GET …/coverage`.

### 6. Machine emit to suggestions

Requires the machine `POST …/catalogue/{id}/emit` route (discovery layer chapter 18) on your API
build. Emit creates **`pending`** suggestions only (no voting or promotion). From any directory:

```bash
curl -s -X POST \
  "http://localhost:8000/api/v1/discovery/machine/catalogue/<catalogue-service-id>/emit" \
  -H "X-API-Key: rt_<your-key>" | python -m json.tool
```

Unresolved requirement claims are skipped; idempotent replays return the same suggestion ids. Admin
emit preview (`GET …/emit-preview`) shows the mapped payload before you call machine emit; see
[`emit_preview.py`](../../apps/api/app/features/discovery/emit_preview.py).

Verify in admin emit preview or `GET /api/v1/suggestions` (public list).

## Troubleshooting

| Symptom | Check |
| --- | --- |
| Admin UI forbidden | `DISCOVERY_ADMIN_EMAILS` includes your signed-in email; discovery feature enabled |
| Machine routes 401 | Valid `DISCOVERY_API_KEY`; or `DISCOVERY_MACHINE_OPT_IN=1` for local dev |
| Ingest TLS timeout / reset | Corporate `HTTP_PROXY` / `HTTPS_PROXY`; `NO_PROXY` includes `localhost` |
| GovData/PVOG CLI exits 1 | API logs; machine batch errors; jurisdiction UUID exists |

Scheduled GitHub Actions ingest is out of scope for this runbook (deferred).
