# Discovery layer operations runbook

GovData and PVOG catalogue ingest, FIM/LeiKa enrich, admin review, and machine emit to `pending`
suggestions. Canon URLs, ingest vs enrich roles, and staging contract pointers:
[`government-data-sources.md`](../discovery/government-data-sources.md).

## Production — scheduled ingest (primary)

**Operators should use GitHub Actions**, not a laptop, for recurring catalogue refetch and worker drain
against production Render.

| Topic | Doc |
| --- | --- |
| Discovery online runbook (dispatch, secrets, triage, idempotency) | [discovery-online.md](discovery-online.md) |
| 6-day OpenPLZ / discovery calendar and secrets | [scheduled-jobs.md](scheduled-jobs.md) |
| Workflow | [platform-maintenance.yml](../../.github/workflows/platform-maintenance.yml) |

Scheduled runs update **staging only** — no automatic emit to suggestions. Emit stays manual (§
Machine emit below).

## Laptop debugging (secondary)

The sections below describe a **local** stack for fixtures, enrich CLIs, admin smoke, and manual emit.

**Chief-of-staff orchestration** (chapter order, loop branch, release) is documented separately in
[`loops/discovery-layer.md`](loops/discovery-layer.md).

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
| `DISCOVERY_API_URL` | Ingest CLIs | API **host root** (no `/api/...` suffix). Local: `http://localhost:8000`. Production: `https://redtape-api.onrender.com`. `discovery-ingest` appends `/api/v1/discovery/machine/...`. |
| `DISCOVERY_API_KEY` | Ingest CLIs | Plaintext crawler key (`X-API-Key`) with access to discovery machine routes |
| `FEDERAL_JURISDICTION_ID` | Ingest CLIs (optional) | Germany country UUID for federal rows; default seed `11111111-1111-1111-1111-111111111101` |
| `DISCOVERY_MACHINE_OPT_IN` | API (optional) | When `1`, enables machine routes even if `DISCOVERY_ADMIN_EMAILS` is empty (dev only) |

### Issue a discovery machine API key

There is no HTTP endpoint for key issuance. From `apps/api`:

```bash
python -m scripts.issue_api_key --name discovery-ingest-local
```

For scheduled GitHub Actions discovery runs, issue a separate key:

```bash
python -m scripts.issue_api_key --name discovery-scheduled-gha
```

Store the printed `rt_…` in `DISCOVERY_API_KEY` (local shell or GitHub repository secret — see
[`scheduled-jobs.md`](scheduled-jobs.md)). Revocation and rotation follow
[`auth-setup.md` §7](auth-setup.md#7-issue-and-revoke-crawler-keys).

### Admin allowlist

Add operator emails to `DISCOVERY_ADMIN_EMAILS` (lowercase is normalized). Sign in to the web app with
Supabase using one of those addresses before visiting admin routes.

## Web admin route surface

The discovery admin UI is available only after the server admin probe succeeds. The server remains the
authorization boundary; the browser does not contain an email allowlist.

| Web route | Behavior |
| --- | --- |
| `/admin/discovery` | Redirects to the catalogue page. |
| `/admin/discovery/catalogue` | Shows catalogue rows and the coverage summary. |
| `/admin/discovery/coverage` | Shows the dedicated coverage summary. |
| `/admin/discovery/tasks` | Shows the crawler task queue. |
| `/admin/discovery/pipeline/<catalogue-service-id>` | Shows pipeline stages and row details. |
| `/admin/discovery/unknown` | Shows the explicit Page not found fallback; it must not leave an empty outlet. |

The emit preview is a subview of the pipeline page, not a top-level route. Every discovery page has
visible loading, success, empty, and error feedback. A `401` sends the session to login, a `403` shows
the forbidden view, a `503` explains that discovery is disabled, and network/API failures offer the
existing retry action.

If the probe fails with `503`, a 5xx status, or a network error, the app retries it twice. If it still
fails, the menu shows a muted **Discovery unavailable** hint instead of the links. A `401` or `403`
shows no hint, because that case looks the same as a non-admin session.

Under **Documents**, an allowlisted user sees readable links for **Catalogue**, **Coverage**, and
**Tasks** after the admin probe returns `200`. Non-admin and anonymous sessions do not see those links,
and direct navigation remains guarded. The menu also keeps these application links:

| Menu action | Route and behavior |
| --- | --- |
| **Home** | Full-width link to `/`. |
| **Browse Documents** | Icon-only, labelled link to `/documents`. |
| **Suggest** | Icon-only, labelled link to `/suggest`. |

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

## Manual sequence (local)

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
export DISCOVERY_API_URL=http://localhost:8000
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

Unit tests are not a live smoke. They show that the route tree and the guard outcomes work in a test
renderer; they do not show that the deployed API, auth configuration, and web proxy work. Run the
sequence below against the target environment and record each result.

1. **Worker-origin check.** Send `GET /api/v1/discovery/admin/tasks?limit=1` with a valid bearer token
   to the web origin. Expect `200` for an allowlisted user. Compare with the direct API origin if the
   status differs (see section 7). Do not paste or commit the token.
2. **Sign-in check.** Sign in with an email that is on `DISCOVERY_ADMIN_EMAILS`. Open the menu and
   confirm that **Catalogue**, **Coverage**, and **Tasks** appear under **Documents**. A muted
   **Discovery unavailable** hint means the probe failed with 503, 5xx, or a network error.
3. **Page checks.** Open each page and confirm content or a deliberate loading, empty, or error state.
   The browser console must show no `No routes matched location` warning.

| Surface | URL / route |
| --- | --- |
| Discovery admin root | Web: [`/admin/discovery`](http://localhost:5173/admin/discovery), redirects to the catalogue |
| Crawler queue | Web: [`/admin/discovery/tasks`](http://localhost:5173/admin/discovery/tasks) |
| Catalogue index and coverage chips | [`/admin/discovery/catalogue`](http://localhost:5173/admin/discovery/catalogue) |
| Dedicated coverage summary | [`/admin/discovery/coverage`](http://localhost:5173/admin/discovery/coverage) |
| Pipeline + emit preview | `/admin/discovery/pipeline/<catalogue-service-id>` |

Also confirm that an unknown discovery route shows **Page not found**, that a non-allowlisted user sees
no discovery links and the forbidden view on direct navigation, and that Home, Browse Documents, and
Suggest keep their menu routes. Locally, use `./scripts/dev-up.sh` or a manual API and web start.

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

### 7. Admin probe triage (blank admin page or missing menu links)

A blank admin page body with the shell visible, and the browser console warning
`No routes matched location "/admin/discovery/..."`, means a route-nesting defect (fixed by relative
child paths under the `/admin/discovery/*` mount). Missing menu links mean the probe below did not
return `200`.

The menu shows the discovery admin links only when
`GET /api/v1/discovery/admin/tasks?limit=1` succeeds for the signed-in user. Read the HTTP status
of that request (browser devtools, then curl against the web origin and
`https://redtape-api.onrender.com`; never paste or commit tokens) and use this table.

| Probe status | Cause | Fix |
| --- | --- | --- |
| 200 | Probe works | Inspect the deployed bundle and menu code |
| 401 | `SUPABASE_JWKS_URL` / `SUPABASE_JWT_ISSUER` unset on Render (auth disabled), JWKS/issuer wrong, or no valid bearer token reached the API (worker proxy or client dropped it) | Set both Supabase variables on Render (`auth_enabled` needs both); compare web-origin and direct-API curl |
| 403 | Email not on `DISCOVERY_ADMIN_EMAILS` (compared lowercase) | Add the exact login email on Render |
| 503 | Discovery disabled, or cold start / proxy 503 (menu shows **Discovery unavailable** after two retries) | Enable discovery; repeat after `/health` is warm |
| 5xx / timeout | Cold start or API fault (menu shows **Discovery unavailable** after two retries) | Check Render logs |

Triage record (operator-reported, 2026-10):

- Probe returned **401** `{"status_code":401,"detail":"Not authenticated"}` while signed in. Whether
  this was browser or curl, and which origin, is **unconfirmed**.
- Render: `DISCOVERY_ADMIN_EMAILS` holds the operator email, so 403 is ruled out;
  `DISCOVERY_MACHINE_OPT_IN` is false (irrelevant to admin routes). Auth-enabled state was not reported.
- Admin pages render blank in the browser, consistent with the route-nesting defect; whether the
  `No routes matched location` console warning appears was not reported.
- Cloudflare serves deployment `59339dfc-06e3-4470-bbf8-0cd27e6e8dce` (not yet verified against `main`).

Reading of the 401: `require_discovery_admin` raises "Not authenticated" when `auth_enabled` is false
(`SUPABASE_JWKS_URL` or `SUPABASE_JWT_ISSUER` missing) and also when the bearer token is missing or
fails verification, so the body alone does not separate them. Most likely cause: Supabase JWT
verification is not configured on Render (`render.yaml` carries no Supabase auth variables, they live
in the dashboard). Next operator checks: confirm both variables are set on the API service; repeat the
curl with a fresh token against the direct Render origin; if that returns 200 but the web origin
returns 401, the worker proxy or client drops the `Authorization` header. A Render config fix is likely
needed but is unconfirmed until those checks run.

## Troubleshooting

| Symptom | Check |
| --- | --- |
| Admin page blank, console warns `No routes matched location` | Section 7; confirm the deployed build includes the relative-route fix |
| Admin UI forbidden | `DISCOVERY_ADMIN_EMAILS` includes your signed-in email; discovery feature enabled |
| Machine routes 401 | Valid `DISCOVERY_API_KEY`; or `DISCOVERY_MACHINE_OPT_IN=1` for local dev |
| Ingest TLS timeout / reset | Corporate `HTTP_PROXY` / `HTTPS_PROXY`; `NO_PROXY` includes `localhost` |
| GovData/PVOG CLI exits 1 | API logs; machine batch errors; jurisdiction UUID exists |

Scheduled GitHub Actions ingest uses the same host-root `DISCOVERY_API_URL` and repository secrets
documented in [`scheduled-jobs.md`](scheduled-jobs.md).
