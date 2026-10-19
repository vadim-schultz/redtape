# Discovery online (scheduled production ingest)

Production catalogue refetch and worker drain run on **GitHub Actions** against the live Render
machine API. Staging rows are updated on a fixed calendar; **machine emit to suggestions stays manual**
(see [discovery-layer.md](discovery-layer.md) § Machine emit).

Chief-of-staff orchestration (loop branch, release PR): [loops/discovery-online.md](loops/discovery-online.md).

**First-time production setup** (Render, GitHub secrets, issue API key from another machine,
manual smoke test): [discovery-online-production-setup.md](discovery-online-production-setup.md).

Data sources and field mapping: [government-data-sources.md](../discovery/government-data-sources.md).

## Primary path — GitHub Actions

Workflow: [`.github/workflows/platform-maintenance.yml`](../../.github/workflows/platform-maintenance.yml)
(**Platform maintenance**). Schedule, secrets, and the 6-day calendar are documented in
[scheduled-jobs.md](scheduled-jobs.md).

### What runs on discovery days (`days % 6 == 3`)

1. **Wake API** — `discovery_ingest.health.wait_for_api` retries `GET /health` on cold Render.
2. **GovData OZG fetch** — `python -m discovery_ingest govdata fetch` (bounded pages) →
   `POST /api/v1/discovery/machine/catalogue/batch`.
3. **PVOG Suchdienst** — `python -m discovery_ingest pvog run` → same machine batch endpoint.
4. **Worker drain** — `python -m discovery_ingest worker drain --max-tasks 50` claims `fetch_url`
   tasks, fetches portal pages, logs events, completes or fails tasks.

Discovery jobs use **`DISCOVERY_API_URL`** (Render **host root**), **`DISCOVERY_API_KEY`**, and
**`FEDERAL_JURISDICTION_ID`** only — never `DATABASE_URL`. OpenPLZ uses the database path on
alternate days (`days % 6 == 0`).

### Manual dispatch (debugging)

GitHub → **Actions** → **Platform maintenance** → **Run workflow**, or:

```bash
gh workflow run platform-maintenance.yml -f job=discovery
gh workflow run platform-maintenance.yml -f job=openplz
gh workflow run platform-maintenance.yml -f job=skip
```

`workflow_dispatch` with `job=discovery` or `job=openplz` **ignores the calendar** for that run.

### Repository secrets

| Secret | Discovery job | Notes |
| --- | --- | --- |
| `DISCOVERY_API_URL` | yes | Host root, e.g. `https://redtape-api.onrender.com` — client adds `/api/v1/discovery/machine/...` |
| `DISCOVERY_API_KEY` | yes | `rt_…` from `python -m scripts.issue_api_key --name discovery-scheduled-gha` in `apps/api` |
| `FEDERAL_JURISDICTION_ID` | yes | Must equal live `jurisdiction.id` for `kind=COUNTRY`, `code=DE` (see triage below) — not always the seed UUID after OpenPLZ. Resolve: production SQL below, or `python -m scripts.print_federal_jurisdiction_id` in `apps/api` against the same DB |
| `DATABASE_URL` | **no** | OpenPLZ job only |

Issue and rotate keys: [auth-setup.md](auth-setup.md#7-issue-and-revoke-crawler-keys). Render admin
allowlist (`DISCOVERY_ADMIN_EMAILS`) is for the web UI — not used by the GHA discovery job.

### Failure triage

| Symptom | Check |
| --- | --- |
| Workflow skipped / `skip` job | Expected on `days % 6` in `1,2,4,5`; see [scheduled-jobs.md](scheduled-jobs.md) |
| Health wait timeout | Render service up; `DISCOVERY_API_URL` is host root without `/api` suffix |
| Machine 401 / 403 | `DISCOVERY_API_KEY` matches a valid crawler key on production API |
| GovData / PVOG step failed | GHA logs; API logs on Render; page caps in workflow may need tuning |
| GovData step: `discovery machine API 500` on batch POST | **Catalogue batch 500 triage** (below); health may still be 200 |
| GovData `no mappable GovData rows` or mass `skip row: … no title` | OZG schema drift (`leika_name` vs legacy `leistungsname`) or unscoped national feed; confirm federal path `open-pvog/000000000000` and [OpenAPI](https://api.ozg-umsetzung.de/api/v3/api-docs/dashboard-digitale-verwaltung) |
| Drain exits non-zero | Stuck `claimed` tasks — lease reclaim (API); re-run after fixing target URLs |
| Duplicate tasks after re-run | Should not grow without bound — see idempotency below |

Admin review after a scheduled run: `/admin/discovery/catalogue` and `/admin/discovery/tasks` on the
production web app (allowlisted email).

### Catalogue batch 500 triage

Use when GHA **GovData OZG catalogue fetch** fails with `discovery machine API 500` while
**Wait for Render API health** succeeded. Auth or discovery-off usually returns **401**, **403**, or
**503**, not **500**.

**Leading hypothesis:** `FEDERAL_JURISDICTION_ID` in GitHub Secrets does not match any
`jurisdiction` row in production (FK on `catalogue_service.jurisdiction_id`). Docs and fresh local
seeds often cite `11111111-1111-1111-1111-111111111101`
([`seed_documents.ID_DE`](../../apps/api/scripts/seed_documents.py)); after **OpenPLZ** import,
Germany is keyed by `(kind, code)` and gets a deterministic UUID from
[`import_openplz_locations`](../../apps/api/scripts/import_openplz_locations.py) — **always confirm
with SQL**, do not assume the seed placeholder.

1. **Render** — In the same window as the failed GHA step, open **Logs** for `redtape-api` and find
   the Python traceback immediately above the uvicorn line for
   `POST /api/v1/discovery/machine/catalogue/batch`. `IntegrityError` / foreign key → jurisdiction
   mismatch; `relation "catalogue_service" does not exist` → migrations not at head.
2. **Minimal curl** — From a machine with repository secrets (never log `DISCOVERY_API_KEY`):

```bash
curl -sS -w "\nHTTP %{http_code}\n" -X POST "$DISCOVERY_API_URL/api/v1/discovery/machine/catalogue/batch" \
  -H "Content-Type: application/json" -H "X-API-Key: $DISCOVERY_API_KEY" \
  -d "{\"items\":[{\"source\":\"govdata\",\"external_id\":\"smoke:govdata:triage\",\"jurisdiction_id\":\"$FEDERAL_JURISDICTION_ID\",\"title_i18n\":{\"de\":\"Smoke\"},\"portal_url\":\"https://example.gov/test\",\"raw_payload\":{\"id\":\"test\"}}]}"
```

| HTTP | Meaning |
| --- | --- |
| 201 | Secret jurisdiction likely OK; if full GovData fetch still fails, inspect live payload shape |
| 500 on minimal body | Config/DB (FK, missing table, unhandled DB error) — use traceback + SQL |
| 401 / 403 / 503 | Key or `DISCOVERY_ADMIN_EMAILS` — not the primary batch-500 hypothesis |

3. **SQL** (production `DATABASE_URL`, read-only) — compare `id` to GitHub secret
   `FEDERAL_JURISDICTION_ID`:

```sql
SELECT id, kind, code FROM jurisdiction WHERE kind = 'COUNTRY' AND code = 'DE';
```

4. **Migrations** — On production DB: `alembic current` at head; table `catalogue_service` exists.

**Remediation:** Update `FEDERAL_JURISDICTION_ID` to the SQL `id`, re-run minimal curl → **201**, then
`gh workflow run platform-maintenance.yml -f job=discovery`. See
[discovery-online-production-setup.md](discovery-online-production-setup.md) §4.4.

## Idempotency and safe re-runs

Scheduled runs re-fetch the same government APIs. Behavior matches **OpenPLZ parity**
([openplz-import.md](openplz-import.md) § Idempotency & cache refresh):

- Catalogue rows upsert by unique keys; batch payloads collapse duplicate `(source, external_id)`.
- `fetch_url` tasks are not duplicated for the same `(catalogue_service_id, kind, target_url)` while
  `pending` or `claimed`; failed tasks or changed `portal_url` may enqueue again.
- `discovery_claim` rows dedupe by entity, kind, and payload fingerprint.
- Races on unique constraints recover via re-select after `IntegrityError` (same pattern as OpenPLZ).

Re-running **Platform maintenance** with `job=discovery` on the same day is safe for staging data;
it must not multiply tasks or claims without bound.

## Laptop debugging (secondary)

Use [discovery-layer.md](discovery-layer.md) for local Postgres, fixture ingest, FIM/LeiKa enrich,
admin smoke, and **manual** `POST …/catalogue/{id}/emit`. Corporate proxy env for live GovData/PVOG
from a laptop is documented there.

## Related

- Unified maintenance calendar: [scheduled-jobs.md](scheduled-jobs.md)
- OpenPLZ import (database path): [openplz-import.md](openplz-import.md)
- Architecture and decisions: [`.plans/discovery-online/`](../../.plans/discovery-online/00-architecture.md)
