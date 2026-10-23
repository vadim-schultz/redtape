# Scheduled jobs (platform maintenance)

This project has no GitLab CI — all scheduling runs on **GitHub Actions**. OpenPLZ import and discovery online share one workflow: [`.github/workflows/platform-maintenance.yml`](../../.github/workflows/platform-maintenance.yml).

## Workflow

`Platform maintenance` (`.github/workflows/platform-maintenance.yml`):

- **Triggers:** `schedule` — monthly cron `0 2 28 * *` (02:00 UTC on day 28, which exists in every month), and `workflow_dispatch` with a `job` input: `all` (default), `openplz`, or `discovery`.
- **Jobs on a scheduled run:** `openplz` first, then `discovery` (catalogue ingest: health wait, GovData fetch, PVOG run). `discovery` waits for `openplz` but still runs when it failed or was skipped.
- **No worker drain here.** Draining the task queue is the job of [`discovery-drain.yml`](../../.github/workflows/discovery-drain.yml), which runs daily on its own budget.
- **OpenPLZ job steps:** checkout → Python 3.12 → `pip install -e .` in `apps/api` → `alembic upgrade head` → verify `uq_jurisdiction_kind_code` on `jurisdiction` → `python scripts/import_openplz_locations.py --language de`.

A manual dispatch runs only the job named in `job` (`all` runs both, in order).

## Repository secrets (GitHub Actions)

Configure these under **Settings → Secrets and variables → Actions** for the repo.

| Secret | OpenPLZ job | Discovery job | Notes |
| --- | --- | --- | --- |
| `DATABASE_URL` | yes | **no** | Supabase pooler URL; migrations + OpenPLZ import only |
| `DISCOVERY_API_URL` | no | yes | Render **host root**, e.g. `https://redtape-api.onrender.com` — ingest client adds `/api/v1/discovery/machine/...` |
| `DISCOVERY_API_KEY` | no | yes | `rt_…` from `python -m scripts.issue_api_key --name discovery-scheduled-gha` (`apps/api`) |
| `FEDERAL_JURISDICTION_ID` | no | yes | Live `jurisdiction.id` for `kind=COUNTRY`, `code=DE` — resolve with SQL or `python -m scripts.print_federal_jurisdiction_id` in `apps/api` (see [discovery-online.md](discovery-online.md) § Repository secrets). Local seed-only DBs often use `11111111-1111-1111-1111-111111111101`; after **OpenPLZ** import Germany is keyed by `(kind, code)` with a deterministic UUID (commonly `44107a34-a8d3-53f9-8dc2-da5b133c12bd` — **confirm on your DB**, do not assume). |

Optional workflow environment variables (defaults in [`discovery_ingest/config.py`](../../apps/discovery-ingest/discovery_ingest/config.py)):

| Variable | Purpose |
| --- | --- |
| `GOVDATA_CKAN_BASE_URL` | GovData CKAN API base |
| `PVOG_API_BASE_URL` | PVOG Suchdienst API base |
| `FIM_PORTAL_BASE_URL` | FIM portal base for enrich |

The discovery job only fetches the GovData and PVOG catalogues into staging. The bounded worker drain
(`discovery_run` report, see [discovery-online.md](discovery-online.md) § Bounded drain) runs in
`discovery-drain.yml`. Scheduled jobs do **not** auto-emit; emit to suggestions is manual.

Discovery ingest never uses `DATABASE_URL` in GHA (machine API boundary). Operator runbook:
[`discovery-online.md`](discovery-online.md). Laptop debugging:
[`discovery-layer.md`](discovery-layer.md).

## Crawl budget

The crawler is [`discovery-drain.yml`](../../.github/workflows/discovery-drain.yml). It runs daily at 04:00 UTC and gets the largest share of this repository's Actions minutes. The account is on the GitHub Free plan with 2,000 Linux minutes a month shared by every repository. The monthly budget table and the operator checklist are in [gha-budget.md](gha-budget.md).

The drain time budget resolves in this order: the `time_budget_seconds` dispatch input, then the repository variable `DISCOVERY_DRAIN_BUDGET_SECONDS`, then 900 seconds. The dispatch input defaults to empty so the variable takes effect. The job timeout is 45 minutes and the pip install is cached.

Set these under **Settings → Secrets and variables → Actions → Variables**:

| Variable | Purpose |
| --- | --- |
| `DISCOVERY_DRAIN_BUDGET_SECONDS` | Wall-clock budget of one scheduled drain in seconds. Unset means 900. Raise it when other repositories on the account use fewer minutes. |
| `DISCOVERY_DRAIN_SCHEDULE` | Set to `enabled` to turn on the daily schedule. Any other value leaves only manual dispatch. |

## Manually triggering a run

GitHub → **Actions** → **Platform maintenance** → **Run workflow**, or via the CLI:

```bash
# Run one job
gh workflow run platform-maintenance.yml -f job=openplz
gh workflow run platform-maintenance.yml -f job=discovery

# Run both, OpenPLZ first
gh workflow run platform-maintenance.yml -f job=all
```

## Related

- Actions minute budget and operator checklist: [gha-budget.md](gha-budget.md)
- Discovery online operations: [discovery-online.md](discovery-online.md)
- Import script details: [openplz-import.md](openplz-import.md)
- Import script: [`apps/api/scripts/import_openplz_locations.py`](../../apps/api/scripts/import_openplz_locations.py)
