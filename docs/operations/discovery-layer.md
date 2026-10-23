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
| Monthly OpenPLZ / discovery schedule and secrets | [scheduled-jobs.md](scheduled-jobs.md) |
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

Under **Documents**, an allowlisted user sees icon controls for **Catalogue** (`FaList`), **Coverage**
(`FaTasks`), and **Tasks** (`FaClipboard`) after the admin probe returns `200`. Each control keeps a
translated `aria-label` and a title, and the routes are unchanged. Non-admin and anonymous sessions do not see those links,
and direct navigation remains guarded. The menu also keeps these application links:

| Menu action | Route and behavior |
| --- | --- |
| **Home** | Full-width link to `/`. |
| **Browse Documents** | Icon-only, labelled link to `/documents`. |
| **Suggest** | Icon-only, labelled link to `/suggest`. |

## Staging vocabulary and the T4 handoff

Four kinds of state exist. Do not mix them up.

| State | Where it lives | Meaning |
| --- | --- | --- |
| Catalogue state | `catalogue_service`, keyed by `(source, external_id)` | Current imported row. It is not a canonical document. |
| Task history | `discovery_task` and `discovery_fetch_log` | Durable queue work (pending, claimed, completed, failed) and append-only fetch attempts. |
| Claims | `discovery_entity` and `discovery_claim` | Staged assertions that can become suggestions. |
| Canonical documents | the document tables | Reached only through a future moderation and promotion suite. |

The admin pipeline derives a stage for each catalogue row:

| Stage | Meaning |
| --- | --- |
| T0 | Row imported, no portal task. |
| T1 | Row has a portal task. |
| T2 | At least one fetch attempt is logged. |
| T3 | Entities and claims exist. |
| T4 | Claims are eligible for emit. |

T4 is an emit-readiness milestone, not a canonical-document state. The handoff stops at a pending
suggestion:

```text
T4 -> inspect emit preview -> manual machine emit -> pending suggestion
```

This process does not vote, promote, attach evidence, capture screenshots, or emit automatically.

### Representative smoke status

The chapter 1 smoke of the discovery-operations suite is **partial**. It covered T0, T1, and T2 plus
fixture-backed downstream contract tests. It did **not** verify a persisted T4 row or a manual emit
against a running API: the fixture row has no `fim_id`, and no authorized API session was available.
Treat the full row-to-pending-suggestion path as unverified until an operator runs it with a row
that has a `fim_id`. Evidence and gaps:
[`.plans/discovery-operations/chapters/01-representative-row-smoke.md`](../../.plans/discovery-operations/chapters/01-representative-row-smoke.md).

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

Emit is a machine API operation. It creates **`pending`** suggestions only (no voting or promotion):

```text
POST /api/v1/discovery/machine/catalogue/<catalogue-service-id>/emit
```

```bash
curl -s -X POST \
  "http://localhost:8000/api/v1/discovery/machine/catalogue/<catalogue-service-id>/emit" \
  -H "X-API-Key: rt_<your-key>" | python -m json.tool
```

The admin emit preview (`GET …/emit-preview`, shown on the pipeline page) is read-only and does not
emit. Use it first; mapping code is in
[`emit_preview.py`](../../apps/api/app/features/discovery/emit_preview.py).

| Claim kind | Emit behavior |
| --- | --- |
| `new_document` | Eligible only when the title and official URL fields are present. |
| `metadata` | Preview-only (`metadata_not_emitted`); not emitted. |
| `new_requirement` | Skipped (`unresolved_requirement_documents`) until both document UUIDs resolve. |

Emit is idempotent by claim identity. A replay returns the existing suggestion and creates no
duplicate. The suggestion stays `pending` until a future moderation suite acts on it.

**Emit one verified row first.** Open its pipeline page, confirm T4 and the preview, emit that single
row, and check the response counts (`created_count`, `skipped_count`, `replayed_count`) and the
suggestion ID. Do not bulk emit until that smoke is clean. Verify in the admin preview or
`GET /api/v1/suggestions` (public list).

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
| 401 | No or invalid bearer token, or `auth_enabled` is false. A curl request without a token always returns 401 | Send a fresh bearer token; if a valid token still gets 401, check both Supabase variables on Render |
| 403 | Email not on `DISCOVERY_ADMIN_EMAILS` (compared lowercase) | Add the exact login email on Render |
| 503 | Discovery disabled, or cold start / proxy 503 (menu shows **Discovery unavailable** after two retries) | Enable discovery; repeat after `/health` is warm |
| 500 | Authenticated, but the guard or handler crashed. `/api/v1/me` 200 with `/discovery/admin/*` 500 is a code fault, not config: read the traceback in Render logs (e.g. `DetachedInstanceError`) | Check Render logs; see "Logging gap" below |
| 5xx / timeout | Cold start or API fault (menu shows **Discovery unavailable** after two retries) | Check Render logs |

Triage record (operator-reported, 2026-10):

- Probe returned **401** `{"status_code":401,"detail":"Not authenticated"}` while signed in. Whether
  this was browser or curl, and which origin, is **unconfirmed**.
- Render: `DISCOVERY_ADMIN_EMAILS` holds the operator email, so 403 is ruled out;
  `DISCOVERY_MACHINE_OPT_IN` is false (irrelevant to admin routes). Auth-enabled state was not reported.
- Admin pages render blank in the browser, consistent with the route-nesting defect; whether the
  `No routes matched location` console warning appears was not reported.
- Cloudflare serves deployment `59339dfc-06e3-4470-bbf8-0cd27e6e8dce` (not yet verified against `main`).

Correction (2026-10-22): the earlier theory that Supabase variables were unset on Render was wrong. The
401 came from a request that carried no bearer token. Verified facts:

- `/api/v1/me` returned 200, so JWT auth and the Supabase variables work.
- `/discovery/admin/tasks`, `/coverage` and `/catalogue` returned 500 every time.
- Alembic was at head (`20261015_claim_fingerprint`), all six discovery tables, the
  `payload_fingerprint` column and five enum types existed, and 1413 catalogue rows were present.
- Root cause: `require_discovery_admin_allowlist` read `user.email` after its session closed
  (`DetachedInstanceError`). Fixed by reading the email inside the session block.

### Verifying the schema

Run these in the Supabase SQL editor when triaging a 5xx:

```sql
select version_num from alembic_version;
select table_name from information_schema.tables
  where table_schema = 'public' and (table_name like '%discovery%' or table_name like 'catalogue%');
select column_name from information_schema.columns where column_name = 'payload_fingerprint';
select typname from pg_type where typtype = 'e' order by typname;
```

### Logging gap

Render logs showed only access lines for the 500s, with no traceback. The Litestar app in
`apps/api/app/main.py` sets no `logging_config`, and Litestar logs unhandled exceptions only in debug
mode by default. Until that is changed (follow-up), reproduce locally to see the traceback.

## Troubleshooting

| Symptom | Check |
| --- | --- |
| Admin page blank, console warns `No routes matched location` | Section 7; confirm the deployed build includes the relative-route fix |
| Discovery links missing but `/me` is 200 | Check the probe status (section 7); on 500 read the Render logs traceback |
| Admin UI forbidden | `DISCOVERY_ADMIN_EMAILS` includes your signed-in email; discovery feature enabled |
| Machine routes 401 | Valid `DISCOVERY_API_KEY`; or `DISCOVERY_MACHINE_OPT_IN=1` for local dev |
| Ingest TLS timeout / reset | Corporate `HTTP_PROXY` / `HTTPS_PROXY`; `NO_PROXY` includes `localhost` |
| GovData/PVOG CLI exits 1 | API logs; machine batch errors; jurisdiction UUID exists |

Scheduled GitHub Actions ingest uses the same host-root `DISCOVERY_API_URL` and repository secrets
documented in [`scheduled-jobs.md`](scheduled-jobs.md).
