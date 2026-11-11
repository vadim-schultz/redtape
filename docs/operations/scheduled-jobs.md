# Scheduled jobs (platform maintenance)

This project has no GitLab CI — all scheduling runs on **GitHub Actions**. OpenPLZ import and discovery online share one workflow: [`.github/workflows/platform-maintenance.yml`](../../.github/workflows/platform-maintenance.yml).

## Workflow

`Platform maintenance` (`.github/workflows/platform-maintenance.yml`):

- **Triggers:** `schedule` — monthly cron `0 2 28 * *` (02:00 UTC on day 28, which exists in every month), and `workflow_dispatch` with a `job` input: `all` (default), `openplz`, or `discovery`.
- **Jobs on a scheduled run:** `openplz` first, then `discovery` (catalogue ingest: health wait, GovData fetch, PVOG run). `discovery` waits for `openplz` but still runs when it failed or was skipped.
- **No worker drain here.** Draining the task queue is the job of the five `discovery-*.yml` workflows ([`discovery-drain.yml`](../../.github/workflows/discovery-drain.yml), [`discovery-render.yml`](../../.github/workflows/discovery-render.yml), [`discovery-extract.yml`](../../.github/workflows/discovery-extract.yml), [`discovery-llm.yml`](../../.github/workflows/discovery-llm.yml), [`discovery-screenshot.yml`](../../.github/workflows/discovery-screenshot.yml)); see § Worker drains and the budget ledger.
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

Five workflows drain the task queue, one per pipeline stage; a sixth, [`discovery-embed.yml`](../../.github/workflows/discovery-embed.yml), drains the embedding queue and a seventh, [`discovery-translate.yml`](../../.github/workflows/discovery-translate.yml), the translation queue (see below). Chapter 2 of `discovery-throughput` split what used to be
two bundled workflows (`discovery-drain.yml`'s `extract_page` kind, `discovery-render.yml`'s `capture_screenshot` kind)
into their own files and retimed every stage so each hop's consumer runs after its producer on the same UTC day. All
ship with their schedule switched off.

| Workflow | Kinds | Schedule (UTC) | Gate variable | Job timeout |
| --- | --- | --- | --- | --- |
| [`discovery-drain.yml`](../../.github/workflows/discovery-drain.yml) | `fetch_url`, `enrich_metadata`, `harvest_payload` | daily 02:00 | `DISCOVERY_DRAIN_SCHEDULE=enabled` | 30 min |
| [`discovery-render.yml`](../../.github/workflows/discovery-render.yml) | `render_page` | daily 03:00 | `DISCOVERY_RENDER_SCHEDULE=enabled` | 20 min |
| [`discovery-extract.yml`](../../.github/workflows/discovery-extract.yml) | `extract_page` | daily 04:00 | `DISCOVERY_EXTRACT_SCHEDULE=enabled` | 20 min |
| [`discovery-llm.yml`](../../.github/workflows/discovery-llm.yml) | `llm_extract` | daily 04:30 | `DISCOVERY_LLM_SCHEDULE=enabled` | 20 min |
| [`discovery-screenshot.yml`](../../.github/workflows/discovery-screenshot.yml) | `capture_screenshot` | daily 05:00 | `DISCOVERY_SCREENSHOT_SCHEDULE=enabled` | 20 min |

`schedule:` triggers fire only from the default branch, so none of them runs on a schedule before the release reaches `main`.
Manual dispatch always works once the file is on `main`.

**Drain inputs.** `discovery-drain.yml`: `max_tasks` (50), `max_batches` (20), `time_budget_seconds` (empty: the variable
`DISCOVERY_DRAIN_BUDGET_SECONDS`, else 900), `kinds` (`fetch_url,enrich_metadata,harvest_payload`). `discovery-render.yml`:
`max_tasks` (5), `max_batches` (40), `time_budget_seconds` (900), `browser_budget_seconds` (570), `kinds` (`render_page`).
`discovery-extract.yml`: `max_tasks` (50), `max_batches` (20), `time_budget_seconds` (empty: the variable
`DISCOVERY_EXTRACT_BUDGET_SECONDS`, else 900), `kinds` (`extract_page`). `discovery-llm.yml`: `llm_model` (default
`@cf/qwen/qwen3-30b-a3b-fp8`, the X16 choice, decided 2026-10-30), `max_tasks` (5), `max_batches` (20), `time_budget_seconds` (600),
`neuron_budget` (2500), `kinds` (`llm_extract`). `discovery-screenshot.yml`: `max_tasks` (5), `max_batches` (40),
`time_budget_seconds` (900), `browser_budget_seconds` (570), `kinds` (`capture_screenshot`). Browser and LLM drains use
small batches because a limit releases every task of the batch.

**The LLM drain workflow.** `discovery-llm.yml` runs `worker drain --kinds llm_extract` with `--neuron-budget`. A
scheduled run takes the model from the repository variable `DISCOVERY_LLM_MODEL` and runs only when
`DISCOVERY_LLM_SCHEDULE` is `enabled`; with no model it skips itself and says so in the job summary. It also skips,
without failing, when the ledger has under 20 Actions minutes or under 300 neurons left. It does not claim the browser
kinds. Its four secrets are `DISCOVERY_API_URL`, `DISCOVERY_API_KEY`, `CLOUDFLARE_ACCOUNT_ID` and
`CLOUDFLARE_AI_API_TOKEN`; the Workers AI token is used only by this workflow and the probe, and is not a Render
variable. `discovery-render.yml` sets `LLM_ENQUEUE: "true"` (and `LLM_MODEL`) in its job `env` by default, so scheduled renders
queue `llm_extract` automatically (details in [discovery-online.md](discovery-online.md) § LLM kind).

**The embedding drain workflow.** `discovery-embed.yml` (search-first, chapter 6) runs `embed drain`: it claims the
embedding tasks that the API queues when a candidate's search text changes, embeds them on Workers AI
(`@cf/qwen/qwen3-embedding-0.6b`) and posts the vectors. It is not a `discovery_task` kind, so it has its own queue and
summary route. Schedule: **06:10 and 18:10 UTC**, only when `DISCOVERY_EMBED_SCHEDULE` is `enabled`; manual dispatch
always works. Dispatch inputs: `max_tasks` (50), `max_batches` (60), `time_budget_seconds` (600), `neuron_budget` (3000).
The job skips itself, without failing, in two places: the ledger precheck (under 20 Actions minutes or 100 neurons
left) and the queue precheck (`embed summary --require-pending` exits 3 when `GET /embeddings/summary` reports
`pending_ready = 0`), which saves the drain step. It shares the group `discovery-pipeline`, fails only when the report's
`succeeded` is false, and reports its minutes in an `if: always()` step. Secrets: `DISCOVERY_API_URL`,
`DISCOVERY_API_KEY`, `CLOUDFLARE_ACCOUNT_ID`, `CLOUDFLARE_AI_API_TOKEN` (the Workers AI token is a GitHub secret and is
never printed; the same token serves `discovery-llm.yml`).

**The translation drain workflow.** `discovery-translate.yml` (search-first, chapter 15) runs `translate drain`: it claims
the translation tasks that the API queues for each candidate card (title and description) and target locale, translates
them with the engine in `TRANSLATION_ENGINE` (default `llm`: Workers AI, `@cf/qwen/qwen3-30b-a3b-fp8`, decision D13),
checks them, repairs failures once and posts the text, which the API stores in R2. It has its own queue and summary route
(`GET /translations/summary`). Schedule: **17:10 UTC once a day**, only when `DISCOVERY_TRANSLATE_SCHEDULE` is `enabled`:
after the 06:10 embed drain and the discovery drains of the same day, and an hour before the 18:10 embed drain, which
embeds the fresh translations. Manual dispatch always works. Dispatch inputs: `max_tasks` (10), `max_batches` (60),
`time_budget_seconds` (600), `neuron_budget` (2500). The job skips itself, without failing, in two places: the ledger
precheck (under 20 Actions minutes, or no more than 100 neurons above the query-embedding floor) and the queue precheck
(`translate summary --require-pending` exits 3 when `pending_ready` is 0 in every locale). It shares the group
`discovery-pipeline`, fails only when the report's `succeeded` is false, and reports its minutes in an `if: always()`
step. **The floor.** The drain never takes the day's neuron ledger below `QUERY_EMBED_RESERVE` (repository variable,
default 1000, a whole number), so request-time query embedding (about 0.1 neuron a query) always has neurons; a run
that would breach it stops `llm_budget`. Secrets: the same four as the embed drain (`DISCOVERY_API_URL`,
`DISCOVERY_API_KEY`, `CLOUDFLARE_ACCOUNT_ID`, `CLOUDFLARE_AI_API_TOKEN`; the Workers AI token is never printed). A
different engine is one repository variable (`TRANSLATION_ENGINE`) plus its own secret in the workflow `env`.

**Concurrency.** All seven drains share the group `discovery-pipeline` with `cancel-in-progress: false`, so they never
overlap. GitHub keeps one pending run per group, so a later queued run cancels the older pending one.

**Budget ledger.** The API keeps one count per resource and period (UTC), so GitHub runs and laptop runs share it. Each
drain workflow reads the ledger first and skips itself, without failing, when the budget is gone. After the drain, a final
step (`if: always()`) adds the elapsed minutes, rounded up, plus one.

| Resource | Period | Default cap | Who spends it |
| --- | --- | --- | --- |
| `actions_minutes` | month | 1,000 (2,000 minus the 1,000 CI reserve) | Drain workflows, through `budget report-minutes`. `discovery-drain.yml` skips under 30 minutes left; the other four skip under 20 |
| `browser_seconds` | day | 570 | Browser drains (`discovery-render.yml`, `discovery-screenshot.yml`). Both skip under 30 seconds left |
| `r2_class_a`, `r2_class_b` | month | 950,000 and 9,500,000 | The metered object store in the API |
| `neurons` | day | 9,500 | `llm_extract` drains, `embed drain` (1,075 neurons per million input tokens, reserved at characters / 3), `translate drain` (about 10 to 13 neurons per card, never below the `QUERY_EMBED_RESERVE` floor) and `llm eval`, through reserve and settle. `llm probe` bypasses the ledger, and Cloudflare's own 10,000-neuron allocation counts every use on the account, so a provider 429 can come before the ledger is spent. The drain skips under 300 neurons left |

Caps are API settings (`BUDGET_*`, `ACTIONS_CI_RESERVE_MINUTES`, `DB_SOFT_LIMIT_BYTES`), listed in
[deployment-checklist.md](deployment-checklist.md). Show the ledger with `python -m discovery_ingest budget show`
(exit 3 when a `--require-remaining RESOURCE=N` is short, exit 4 with `--strict` when the API is unreachable).

**Actions minutes.** The account is on the GitHub Free plan: 2,000 Linux minutes a month shared by every repository.
This repository's cap (`BUDGET_ACTIONS_MINUTES_MONTHLY`) moved to **2,000** (revised 2026-11; this assumes the
account-wide pool has grown to cover this repository alone, or other repositories' usage dropped — unverified, see
[`discovery-throughput/gaps-and-decisions.md`](../../.plans/discovery-throughput/gaps-and-decisions.md) D1). A CI
reserve of 1,000 (`ACTIONS_CI_RESERVE_MINUTES`) is not for drains, so the drains above (and the embedding and translation drains) share 1,000. The monthly
comparison of the ledger with GitHub's usage report and the plan for the minutes are in [gha-budget.md](gha-budget.md).
Prefer a drain on a laptop: it costs no Actions minutes.

Set these under **Settings → Secrets and variables → Actions → Variables**:

| Variable | Purpose |
| --- | --- |
| `DISCOVERY_DRAIN_BUDGET_SECONDS` | Wall-clock budget of one scheduled `discovery-drain.yml` run in seconds. Unset means 900. Raise it when other repositories on the account use fewer minutes. |
| `DISCOVERY_EXTRACT_BUDGET_SECONDS` | Wall-clock budget of one scheduled `discovery-extract.yml` run in seconds. Unset means 900. |
| `DISCOVERY_DRAIN_SCHEDULE` | Set to `enabled` to turn on the daily seed drain (`fetch_url`, `enrich_metadata`, `harvest_payload`). Any other value leaves only manual dispatch. Keep it unset until the checklist step S13. |
| `DISCOVERY_RENDER_SCHEDULE` | Set to `enabled` to turn on the daily `render_page` drain. Because `discovery-render.yml`'s job `env` sets `LLM_ENQUEUE: "true"` by default (chapter 2 of `discovery-throughput`), enabling this schedule also turns on the `llm_extract` fan-out, not rendering alone. Keep it unset until there is budget; run the drain on a laptop instead. |
| `DISCOVERY_EXTRACT_SCHEDULE` | Set to `enabled` to turn on the daily `extract_page` drain. Any other value leaves only manual dispatch. |
| `DISCOVERY_LLM_SCHEDULE` | Set to `enabled` to turn on the daily `llm_extract` drain. Keep it unset until the extraction live gate passed and the monthly Actions allowance has room; delete it to pause (manual dispatch keeps working). |
| `DISCOVERY_EMBED_SCHEDULE` | Set to `enabled` to turn on the twice-daily `embed drain`. Set it only after the search-text backfill (chapter 4) has queued the tasks and the API has `EMBEDDING_MODEL` at its default or the same value as the workers. Any other value leaves only manual dispatch. |
| `DISCOVERY_TRANSLATE_SCHEDULE` | Set to `enabled` to turn on the daily `translate drain`. Set it only after the C14 backfill has queued tasks, `TRANSLATION_TARGET_LOCALES` is narrowed on Render and in the plan, and the API has its R2 object-store variables (without them every `complete` answers `unavailable`). Any other value leaves only manual dispatch. |
| `QUERY_EMBED_RESERVE` | Neurons of the day's ledger the translate drain leaves for query embedding (a whole number; unset means 1000). |
| `TRANSLATION_ENGINE` | The registered engine the translate drain uses; unset means `llm`. |
| `DISCOVERY_SCREENSHOT_SCHEDULE` | Set to `enabled` to turn on the daily `capture_screenshot` drain. Any other value leaves only manual dispatch. |
| `DISCOVERY_LLM_MODEL` | The Workers AI model id a scheduled run extracts with (a model with a price row). Unset means a scheduled run skips. |

## Probe and fixture workflows (manual only)

| Workflow | Needs | Purpose |
| --- | --- | --- |
| [`discovery-storage-probe.yml`](../../.github/workflows/discovery-storage-probe.yml) | the five `OBJECT_STORE_*` secrets | Proves the R2 bucket end to end (put, get, presigned GET, delete) and recommends the checksum variant |
| [`discovery-browser-probe.yml`](../../.github/workflows/discovery-browser-probe.yml) | `CLOUDFLARE_ACCOUNT_ID`, `CLOUDFLARE_BROWSER_API_TOKEN` | Calls each Cloudflare quick action once and records the response shape and browser time |
| [`discovery-llm-probe.yml`](../../.github/workflows/discovery-llm-probe.yml) | `CLOUDFLARE_ACCOUNT_ID`, `CLOUDFLARE_AI_API_TOKEN` | Sends one cleaned fixture page to each listed Workers AI model and records envelope, usage and neurons (inputs `models`, `fixture`, `max_neurons` 900). Bypasses the ledger |
| [`discovery-fim-probe.yml`](../../.github/workflows/discovery-fim-probe.yml) | none | Checks that live steckbrief keys return `leistungsschluessel` |
| [`discovery-fixture-capture.yml`](../../.github/workflows/discovery-fixture-capture.yml) | `DISCOVERY_API_URL`, `DISCOVERY_API_KEY` | Downloads stored snapshots of one host as a 7-day Actions artifact for extractor tests |

**Secrets.** Storage credentials reach GitHub only as the probe's five secrets; no drain workflow receives them, and
the API reads the same values from Render. The Cloudflare secrets are used only by the render workflow and the browser
probe. The Workers AI secret `CLOUDFLARE_AI_API_TOKEN` is used only by `discovery-llm.yml`, `discovery-embed.yml`, `discovery-translate.yml` and `discovery-llm-probe.yml`.
The Cloudflare tokens are not Render variables, and the API never reads them.

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

# Drain extract_page from stored snapshots, a short run
gh workflow run discovery-extract.yml -f max_batches=3 -f time_budget_seconds=600

# Extract from stored snapshots (spends Workers AI neurons; the model is required)
gh workflow run discovery-llm.yml -f llm_model=<model id> -f max_batches=2 -f neuron_budget=2500

# Capture a few screenshots (spends Cloudflare browser time; see the budget table above)
gh workflow run discovery-screenshot.yml -f max_tasks=5 -f max_batches=2 -f time_budget_seconds=300
```

## Related

- Manual steps that unlock live gates: [crawlers-operator-checklist.md](crawlers-operator-checklist.md) and [extraction-operator-checklist.md](extraction-operator-checklist.md)
- Actions minute budget and operator checklist: [gha-budget.md](gha-budget.md)
- Discovery online operations: [discovery-online.md](discovery-online.md)
- Import script details: [openplz-import.md](openplz-import.md)
- Import script: [`apps/api/scripts/import_openplz_locations.py`](../../apps/api/scripts/import_openplz_locations.py)
