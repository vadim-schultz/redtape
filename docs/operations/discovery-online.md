# Discovery online (scheduled production ingest)

Production catalogue refetch and worker drain run on **GitHub Actions** against the live Render
machine API. Staging rows are updated on a fixed calendar; **machine emit to suggestions stays manual**
(see [discovery-layer.md](discovery-layer.md) § Machine emit).

Chief-of-staff orchestration (loop branch, release PR): [loops/discovery-online.md](loops/discovery-online.md),
[loops/pvog-v7-ingest.md](loops/pvog-v7-ingest.md).

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

## Bounded drain, run reports, and queue metrics

`worker drain` is always bounded. It stops on the first of: an empty queue, the batch limit, or the
time budget.

```bash
python -m discovery_ingest worker drain --max-tasks 50 --max-batches 5 --time-budget-seconds 300
```

| Flag | Default | Meaning |
| --- | --- | --- |
| `--max-tasks` | 50 | Tasks per claim request (1–50) |
| `--max-batches` | 1 | Maximum claim and process batches (positive) |
| `--time-budget-seconds` | none | Optional positive wall-clock budget for the whole drain |

Invalid bounds exit with code 2. An API failure exits with code 1. The scheduled workflow uses the
defaults (`--max-tasks 50`, one batch), so each scheduled run is one batch.

Each drain prints one JSON report with `batches`, `claimed`, `completed`, `failed`, `skipped`,
`stop_reason` (`queue_empty`, `batch_limit`, `time_budget`, or `error`), `run_id`, and `succeeded`.
The worker records the run through the machine API (`POST …/runs`, then `POST …/runs/{id}/finish`)
into the `discovery_run` table. The worker never touches the database directly.

**`remaining` is unknown.** No queue-summary route is available to the worker, and the worker must not
claim an extra task to estimate backlog. The report therefore sets `remaining_unknown` to true. Read
the backlog on the admin Coverage page instead.

The admin Coverage surface (`GET /api/v1/discovery/admin/coverage`) reports task counts (pending,
claimed, completed, failed), `fetch_attempts_total`, `failures_by_source`, `stale_claims` (claimed tasks
with an expired 15-minute lease), `stale_runs` (runs still `running` after one hour), and
`last_successful_run`. That last value comes from `discovery_run` rows with status `succeeded`, not
from fetch timestamps. A failed or interrupted run is never reported as the last successful run.

**Not verified:** a manual multi-batch drain and an interrupted-claim lease-reclaim check were not
performed during the discovery-operations suite. Run both against a non-production stack before relying
on them.

### Triage for queue state

| Symptom | Check |
| --- | --- |
| `stale_claims` above zero | A worker died mid-batch. The next claim reclaims expired leases; re-run a bounded drain. |
| `stale_runs` above zero | A run never finished. It stays visible as stale and is not counted as successful. |
| `last_successful_run` old or empty | Check recent `discovery_run` failures and the drain `stop_reason`. |
| `failures_by_source` growing | Inspect failed tasks on `/admin/discovery/tasks` for that source. |

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
| PVOG step: `400` / HTTPStatusError, API code **1901** | **PVOG v7 search triage** (below) — bare list URL without `personalMatters`, `q`, or LeiKa |
| GovData step: `discovery machine API 500` on batch POST | **Catalogue batch 500 triage** (below); health may still be 200 |
| GovData `no mappable GovData rows` or mass `skip row: … no title` | OZG schema drift (`leika_name` vs legacy `leistungsname`) or unscoped national feed; confirm federal path `open-pvog/000000000000` and [OpenAPI](https://api.ozg-umsetzung.de/api/v3/api-docs/dashboard-digitale-verwaltung) |
| Drain exits non-zero | Stuck `claimed` tasks — lease reclaim (API); re-run after fixing target URLs |
| Duplicate tasks after re-run | Should not grow without bound — see idempotency below |

Scheduled runs never emit. Manual emit follows [discovery-layer.md](discovery-layer.md) § Machine emit.

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

### PVOG v7 search triage

Use when **PVOG Suchdienst catalogue run** fails immediately with `httpx.HTTPStatusError: 400` and ingest logs or
response JSON mention code **1901** (search must include terms, LeiKa ids, or Lebenslagen). GovData may have
succeeded in the same workflow run.

**Leading hypothesis:** ingest still calls v7 without required search parameters (for example bare
`GET …/v7/servicedescriptions/000000000000`). Current federal path uses a **Lebenslagen tree walk**
(`personalMatters` bootstrap + per-leaf pagination) — see [government-data-sources.md § Federal ingest](../discovery/government-data-sources.md#federal-ingest-pvog-run-v7).

1. **GHA log** — Confirm the failing URL includes `personalMatters=` and `facades=` query parameters. A path with only
   `{ars}` and no search criteria matches the 1901 failure mode.
2. **Deployed ingest** — Ensure production runs a build that includes the v7 client from
   [`.plans/pvog-v7-ingest/`](../../.plans/pvog-v7-ingest/00-architecture.md) (merged via release PR), not an older
   chapter-13 list client.
3. **Partial catalogue under page cap** — Workflow passes `--max-pages 50` (global GET budget including bootstrap).
   Step may exit **0** while only a subset of Lebenslagen codes were crawled; raise the cap in
   [platform-maintenance.yml](../../.github/workflows/platform-maintenance.yml) when operators need fuller
   `source=pvog` coverage (open seam in [gaps-and-decisions](../../.plans/pvog-v7-ingest/gaps-and-decisions.md)).
4. **Manual repro (corporate proxy)** — Export proxy vars from
   [corporate-build-env.md](../../.cursor/skills/chief-of-staff/corporate-build-env.md), then:

```bash
curl -fsS "${PVOG_API_BASE_URL:-https://pvog.fitko.net/suchdienst/api}/v7/servicedescriptions/000000000000?personalMatters=Geburt&facades=true&size=1" | head -c 400
```

| Outcome | Meaning |
| --- | --- |
| 400 / JSON code 1901 on bootstrap curl | Search params rejected — check URL encoding and proxy |
| 200 with `facades` JSON | Suchdienst OK; if GHA still fails, inspect ingest build and `DISCOVERY_API_*` batch POST on Render |
| Connection reset / timeout | Corporate proxy not exported — see corporate-build-env |

**Remediation:** Merge and deploy the v7 ingest fix, re-run `gh workflow run platform-maintenance.yml -f job=discovery`.
Admin check: `/admin/discovery/catalogue` filtered by `source=pvog`.

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
