# Scheduled jobs (platform maintenance)

This project has no GitLab CI — all scheduling runs on **GitHub Actions**. OpenPLZ import and discovery online share one workflow: [`.github/workflows/platform-maintenance.yml`](../../.github/workflows/platform-maintenance.yml).

## Workflow

`Platform maintenance` (`.github/workflows/platform-maintenance.yml`):

- **Triggers:** `schedule` — monthly cron `0 2 28 * *` (02:00 UTC on day 28, which exists in every month), and `workflow_dispatch` with a `job` input: `all` (default), `openplz`, or `discovery`.
- **Jobs on a scheduled run:** `openplz` first, then `discovery` (catalogue ingest: health wait, GovData fetch, PVOG run). `discovery` waits for `openplz` but still runs when it failed or was skipped.
- **No worker drain here.** Draining the task queue is the job of [`discovery-drain.yml`](../../.github/workflows/discovery-drain.yml) and [`discovery-render.yml`](../../.github/workflows/discovery-render.yml); see § Worker drains and the budget ledger.
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

The discovery job only fetches the GovData and PVOG catalogues into staging. The bounded worker drains
(`discovery_run` report, see [discovery-online.md](discovery-online.md) § Bounded drain) run in
`discovery-drain.yml` and `discovery-render.yml`. **No scheduled job emits**, neither catalogue claims nor document
candidates; emit to suggestions is manual.

Discovery ingest never uses `DATABASE_URL` in GHA (machine API boundary). Operator runbook:
[`discovery-online.md`](discovery-online.md). Laptop debugging:
[`discovery-layer.md`](discovery-layer.md).

## Worker drains and the budget ledger

Two workflows drain the task queue. Both ship with their schedule switched off.

| Workflow | Kinds | Schedule (UTC) | Gate variable | Job timeout |
| --- | --- | --- | --- | --- |
| [`discovery-drain.yml`](../../.github/workflows/discovery-drain.yml) | `fetch_url`, `enrich_metadata`, `harvest_payload`, `extract_page` | daily 04:00 | `DISCOVERY_DRAIN_SCHEDULE=enabled` | 45 min |
| [`discovery-render.yml`](../../.github/workflows/discovery-render.yml) | `render_page`, `capture_screenshot` | daily 05:00 | `DISCOVERY_RENDER_SCHEDULE=enabled` | 30 min |

`schedule:` triggers fire only from the default branch, so neither runs on a schedule before the release reaches `main`.
Manual dispatch always works once the file is on `main`.

**Drain inputs.** `discovery-drain.yml`: `max_tasks` (50), `max_batches` (20), `time_budget_seconds` (empty: the variable
`DISCOVERY_DRAIN_BUDGET_SECONDS`, else 900), `kinds`. `discovery-render.yml`: `max_tasks` (5), `max_batches` (40),
`time_budget_seconds` (900), `browser_budget_seconds` (570), `kinds`. Browser drains use small batches because a limit
releases every task of the batch.

**Concurrency.** Both drains share the group `discovery-drain` with `cancel-in-progress: false`, so they never overlap.
GitHub keeps one pending run per group, so a third queued run cancels the older pending one.

**Budget ledger.** The API keeps one count per resource and period (UTC), so GitHub runs and laptop runs share it. Each
drain workflow reads the ledger first and skips itself, without failing, when the budget is gone. After the drain, a final
step (`if: always()`) adds the elapsed minutes, rounded up, plus one.

| Resource | Period | Default cap | Who spends it |
| --- | --- | --- | --- |
| `actions_minutes` | month | 400 (1,000 minus the 600 CI reserve) | Drain workflows, through `budget report-minutes`. The drain skips under 45 minutes left, the render under 30 |
| `browser_seconds` | day | 570 | Browser drains. The render skips under 30 seconds left |
| `r2_class_a`, `r2_class_b` | month | 950,000 and 9,500,000 | The metered object store in the API |
| `neurons` | day | 9,500 | Reserved for the extraction suite |

Caps are API settings (`BUDGET_*`, `ACTIONS_CI_RESERVE_MINUTES`, `DB_SOFT_LIMIT_BYTES`), listed in
[deployment-checklist.md](deployment-checklist.md). Show the ledger with `python -m discovery_ingest budget show`
(exit 3 when a `--require-remaining RESOURCE=N` is short, exit 4 with `--strict` when the API is unreachable).

**Actions minutes.** The account is on the GitHub Free plan: 2,000 Linux minutes a month shared by every repository,
and this repository is capped at **1,000**. A CI reserve of 600 is not for drains, so the drains have 400. The monthly
comparison of the ledger with GitHub's usage report and the plan for the minutes are in [gha-budget.md](gha-budget.md).
Prefer a drain on a laptop: it costs no Actions minutes.

Set these under **Settings → Secrets and variables → Actions → Variables**:

| Variable | Purpose |
| --- | --- |
| `DISCOVERY_DRAIN_BUDGET_SECONDS` | Wall-clock budget of one scheduled drain in seconds. Unset means 900. Raise it when other repositories on the account use fewer minutes. |
| `DISCOVERY_DRAIN_SCHEDULE` | Set to `enabled` to turn on the daily drain. Any other value leaves only manual dispatch. Keep it unset until the checklist step S13. |
| `DISCOVERY_RENDER_SCHEDULE` | Set to `enabled` to turn on the daily render drain. Keep it unset until there is budget; run the drain on a laptop instead. |

## Probe and fixture workflows (manual only)

| Workflow | Needs | Purpose |
| --- | --- | --- |
| [`discovery-storage-probe.yml`](../../.github/workflows/discovery-storage-probe.yml) | the five `OBJECT_STORE_*` secrets | Proves the R2 bucket end to end (put, get, presigned GET, delete) and recommends the checksum variant |
| [`discovery-browser-probe.yml`](../../.github/workflows/discovery-browser-probe.yml) | `CLOUDFLARE_ACCOUNT_ID`, `CLOUDFLARE_BROWSER_API_TOKEN` | Calls each Cloudflare quick action once and records the response shape and browser time |
| [`discovery-fim-probe.yml`](../../.github/workflows/discovery-fim-probe.yml) | none | Checks that live steckbrief keys return `leistungsschluessel` |
| [`discovery-fixture-capture.yml`](../../.github/workflows/discovery-fixture-capture.yml) | `DISCOVERY_API_URL`, `DISCOVERY_API_KEY` | Downloads stored snapshots of one host as a 7-day Actions artifact for extractor tests |

**Secrets.** Storage credentials reach GitHub only as the probe's five secrets; no drain workflow receives them, and
the API reads the same values from Render. The Cloudflare secrets are used only by the render workflow and the browser
probe. The Cloudflare token is not a Render variable, and the API never reads it.

**`gh workflow run` answers 404 for a workflow file that is not on `main` yet.** Until the release, run the probes on a
laptop:

```bash
# Storage: the Render values exported (never committed); reads OBJECT_STORE_* from the environment
cd apps/api && set -a; source <env file>; set +a; .venv/bin/python -m scripts.object_store_probe
# Browser: only the two Cloudflare variables are needed
python -m discovery_ingest browser probe --url https://example.com --variant content
# FIM keys: public portal, no credentials
python -m discovery_ingest fim probe --keys 99154021000000,99070016261000
```

## Manually triggering a run

GitHub → **Actions** → **Platform maintenance** → **Run workflow**, or via the CLI:

```bash
# Run one job
gh workflow run platform-maintenance.yml -f job=openplz
gh workflow run platform-maintenance.yml -f job=discovery

# Run both, OpenPLZ first
gh workflow run platform-maintenance.yml -f job=all

# Drain the HTTP kinds, a short run
gh workflow run discovery-drain.yml -f max_batches=3 -f time_budget_seconds=600

# Render a few pages (spends Cloudflare browser time; see the budget table above)
gh workflow run discovery-render.yml -f max_tasks=5 -f max_batches=2 -f time_budget_seconds=300
```

## Related

- Manual steps that unlock live gates: [crawlers-operator-checklist.md](crawlers-operator-checklist.md)
- Actions minute budget and operator checklist: [gha-budget.md](gha-budget.md)
- Discovery online operations: [discovery-online.md](discovery-online.md)
- Import script details: [openplz-import.md](openplz-import.md)
- Import script: [`apps/api/scripts/import_openplz_locations.py`](../../apps/api/scripts/import_openplz_locations.py)
