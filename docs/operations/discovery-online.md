# Discovery online (scheduled production ingest)

Production catalogue refetch (monthly, platform maintenance) and the worker drains (`discovery-drain.yml` for
HTTP kinds, `discovery-render.yml` for browser kinds) run on **GitHub Actions** against the live Render machine API.
Both drain schedules ship switched off; dispatch them by hand or run the same command on a laptop.
**Machine emit to suggestions stays manual** (see [discovery-layer.md](discovery-layer.md) § Machine emit).
Manual steps that unlock live verification are in
[crawlers-operator-checklist.md](crawlers-operator-checklist.md).

Chief-of-staff orchestration (loop branch, release PR): [loops/discovery-online.md](loops/discovery-online.md),
[loops/pvog-v7-ingest.md](loops/pvog-v7-ingest.md).

**First-time production setup** (Render, GitHub secrets, issue API key from another machine,
manual smoke test): [discovery-online-production-setup.md](discovery-online-production-setup.md).

Data sources and field mapping: [government-data-sources.md](../discovery/government-data-sources.md).

## Primary path — GitHub Actions

Workflow: [`.github/workflows/platform-maintenance.yml`](../../.github/workflows/platform-maintenance.yml)
(**Platform maintenance**). Schedule (monthly, day 28), secrets, and manual dispatch are documented in
[scheduled-jobs.md](scheduled-jobs.md).

### What the monthly discovery job runs

1. **Wake API** — `discovery_ingest.health.wait_for_api` retries `GET /health` on cold Render.
2. **GovData OZG fetch** — `python -m discovery_ingest govdata fetch` (bounded pages) →
   `POST /api/v1/discovery/machine/catalogue/batch`.
3. **PVOG Suchdienst** — `python -m discovery_ingest pvog run` → same machine batch endpoint.

The worker drains are not part of this job. [`discovery-drain.yml`](../../.github/workflows/discovery-drain.yml)
claims the HTTP kinds (`fetch_url`, `enrich_metadata`, `harvest_payload`, `extract_page`) and
[`discovery-render.yml`](../../.github/workflows/discovery-render.yml) claims the browser kinds
(`render_page`, `capture_screenshot`). See § Bounded drain and § Browser kinds below.

Discovery jobs use **`DISCOVERY_API_URL`** (Render **host root**), **`DISCOVERY_API_KEY`**, and
**`FEDERAL_JURISDICTION_ID`** only — never `DATABASE_URL`. OpenPLZ (the `openplz` job, run before discovery) uses the database path.

## Bounded drain, run reports, and queue metrics

`worker drain` is always bounded. It stops on the first of: an empty queue, the batch limit, the
time budget, or a limit that ends the run on purpose (see [Stop reasons](#stop-reasons)).

```bash
python -m discovery_ingest worker drain --max-tasks 50 --max-batches 5 --time-budget-seconds 300
```

| Flag | Default | Meaning |
| --- | --- | --- |
| `--max-tasks` | 50 | Tasks per claim request (1–50). Browser drains use 5: a limit releases the whole batch |
| `--max-batches` | 1 | Maximum claim and process batches (positive) |
| `--time-budget-seconds` | none | Optional positive wall-clock budget for the whole drain |
| `--browser-budget-seconds` | 570 | Browser seconds this run may spend; read only when a browser kind is drained (positive) |
| `--neuron-budget` | none | Workers AI neurons this run may spend; required when `llm_extract` is drained (see § LLM kind) |
| `--kinds` | `fetch_url,enrich_metadata,harvest_payload,extract_page` | Comma separated task kinds to claim; an unknown kind exits 2 before any claim |

Invalid bounds exit with code 2. An API failure exits with code 1. A drain that ends on a limit exits 0.

`discovery-drain.yml` passes its inputs to the same flags. `max_tasks` defaults to 50, `max_batches` to 20 and `kinds`
to `fetch_url,enrich_metadata,harvest_payload` — trimmed from the CLI default above, because `extract_page` now drains
in its own workflow (chapter 2 of `discovery-throughput`'s same-day restructuring). The time budget is the
`time_budget_seconds` input, else the repository variable `DISCOVERY_DRAIN_BUDGET_SECONDS`, else 900 seconds. The
daily 02:00 UTC schedule runs only when the variable `DISCOVERY_DRAIN_SCHEDULE` is `enabled`; the other four stages
each drain on their own daily schedule, same-day: `render_page` at 03:00 UTC (`discovery-render.yml`), `extract_page`
at 04:00 UTC (`discovery-extract.yml`), `llm_extract` at 04:30 UTC (`discovery-llm.yml`) and `capture_screenshot` at
05:00 UTC (`discovery-screenshot.yml`). See [scheduled-jobs.md](scheduled-jobs.md).

### Task kinds and the kind filter

Every kind is a row in `discovery_task`. A worker sends its `kinds` with each claim, so it only leases work it can do.
A claim that names no `kinds` gets only `fetch_url` and `enrich_metadata`, so an old worker never leases a kind it
cannot handle.

| Kind | Network | What the worker does | In the default kinds |
| --- | --- | --- | --- |
| `fetch_url` | yes | Polite GET of the portal URL: robots.txt, 1 s per-host interval, up to five redirects, 5 MiB cap, no private addresses. Logs the attempt. A 200 `text/html` page whose final URL is not a login URL enqueues `render_page` | yes |
| `enrich_metadata` | yes | Reads the FIM steckbrief for a GovData or PVOG row that carries a LeiKa key | yes |
| `harvest_payload` | no | Reads the stored PVOG payload and posts document mentions (roles `required` and `form`) | yes |
| `extract_page` | no | Reads a stored snapshot, runs the matching extractor and posts mentions. Completes with the note `no_extractor` when none matches, `no_mentions` when the page has none | yes |
| `render_page` | Cloudflare | Renders the page and stores the DOM as an `html_snapshot` artifact | no |
| `capture_screenshot` | Cloudflare | Stores a full-page JPEG as a `screenshot` artifact | no |
| `llm_extract` | Cloudflare Workers AI | Cleans a stored snapshot, asks the model for documents, dependencies and tags, grounds the answer and posts mentions, then edges. Budgeted in neurons | no |

No extractor is registered yet (`discovery_ingest/extract/registry.py` is empty; the first one is chapter 18, which is
optional), so every `extract_page` task completes with `no_extractor` and no `capture_screenshot` task is queued.
Document candidates come from `harvest_payload` for now.

### Retry and backoff

A claim consumes one attempt. A task may use three attempts. A failure the worker marks retryable puts the task back to
`pending` with `not_before` set 5 minutes, then 30 minutes, then 3 hours ahead; claims skip tasks that are not yet
due. Other failures stay `failed`.

| Retryable | Permanent |
| --- | --- |
| timeout, connection reset, robots.txt unreachable, HTTP 429 and 5xx, and API 5xx while a handler writes | other 4xx, robots.txt disallow, blocked address, body too large, too many redirects, unknown kind, extractor exception |

A **release** is not a failure. It puts a claimed task back to `pending` and returns the attempt the claim consumed.
Workers release when a limit, not the page, stopped the work.

### Run report

Each drain prints one JSON report and records the run through the machine API (`POST …/runs`, then
`POST …/runs/{id}/finish`) into `discovery_run`. The worker never touches the database directly.

| Field | Meaning |
| --- | --- |
| `batches`, `claimed`, `completed`, `failed`, `skipped` | Counts for the run |
| `remaining` | Tasks of the drained kinds that are ready to claim now (`pending_ready` from `GET /api/v1/discovery/machine/tasks/summary`). Delayed retries are not counted |
| `remaining_unknown` | `true` only when the summary call failed; `remaining` is then `null` |
| `stop_reason` | Why the run ended |
| `succeeded` | `false` only for `error` |
| `released` | Tasks handed back without consuming an attempt |
| `browser_seconds_used` | Browser seconds this run spent |
| `neurons_used`, `llm_calls` | Workers AI neurons this run settled and the model calls it made |
| `llm_enqueue_failed` | `llm_extract` tasks a render drain with `LLM_ENQUEUE=true` could not enqueue; the page itself still completed |
| `render_enqueue_failed`, `capture_enqueue_failed` | Follow-up tasks a fetch or an extraction could not enqueue; the page itself still completed |
| `ledger_unavailable` | The budget ledger could not be read; the run used its own budget |
| `run_id`, `error` | The recorded run, and the failure text if any |

The summary route accepts repeated `?kinds=` and returns `pending_ready`, `pending_delayed`, `claimed`,
`claimed_stale`, `completed` and `failed`.

### Stop reasons

| `stop_reason` | Meaning | Run succeeds |
| --- | --- | --- |
| `queue_empty` | A claim returned no task | yes |
| `batch_limit` | `--max-batches` reached | yes |
| `time_budget` | `--time-budget-seconds` reached after a batch | yes |
| `browser_budget` | Fewer than 30 browser seconds are left in the run budget or in today's ledger | yes |
| `browser_quota` | Cloudflare answered 429 other than its rate limit; the day is marked exhausted | yes |
| `storage_unavailable` | The artifact routes answered 503 or 507 (store unset, quota denied or byte cap reached) | yes |
| `db_limit` | A machine write answered 507 `database_soft_limit` | yes |
| `llm_budget` | `llm_extract`: the run's neuron budget or today's neuron ledger cannot cover the next call | yes |
| `llm_quota` | `llm_extract`: Workers AI answered that the daily allocation is used up; the day is marked exhausted | yes |
| `error` | A rejected Cloudflare token (401 or 403, browser or Workers AI) or an API failure | no, exit 1 |

On every stop except `queue_empty`, `batch_limit`, `time_budget` and `error`, the worker releases the in-flight task
and the tasks it did not start, then ends the run.

The admin Coverage surface (`GET /api/v1/discovery/admin/coverage`) reports task counts (pending,
claimed, completed, failed) in total and by kind, candidate counts, artifact counts and bytes, `fetch_attempts_total`,
`failures_by_source`, `stale_claims` (claimed tasks with an expired 15-minute lease), `stale_runs` (runs still
`running` after one hour), and `last_successful_run`. That last value comes from `discovery_run` rows with status
`succeeded`. A failed or interrupted run is never reported as the last successful run.

**Not verified live:** the multi-batch drain, retry and release paths are covered by tests against fakes. Their
live gates wait for the release to reach `main`, because `workflow_dispatch` needs the workflow file on the default
branch. Run them with step S7 of [crawlers-operator-checklist.md](crawlers-operator-checklist.md).

### Browser kinds (Cloudflare Browser Run)

`render_page` and `capture_screenshot` call Cloudflare Browser Run quick actions over HTTP (`browser-run/content` and
`browser-run/snapshot`). The repository has no browser, no Playwright and no Chromium install. The free plan sets the
rules the worker follows.

| Free-plan limit | Worker behaviour |
| --- | --- |
| 10 browser minutes a day | Run budget is the smaller of `--browser-budget-seconds` (default 570) and what the ledger still has today. Each call reserves 30 seconds, then settles to `X-Browser-Ms-Used`. Under 30 seconds left, the run stops `browser_budget` before it claims |
| One request every 10 seconds | At least 11 seconds between the end of one call and the start of the next, so about 4 pages a minute |
| Three concurrent browsers, 60 s timeout | One call at a time, 60 s request timeout (`BROWSER_REQUEST_TIMEOUT_SECONDS`) |
| `429` | A rate-limit 429 (code 2001) is retried once. Any other 429 marks `browser_seconds` exhausted, releases the batch and stops `browser_quota` |

A 15-minute run (900 s) renders about 55–65 pages, and the 1,423 known pages take about 22 runs. The same run on a
laptop costs no Actions minutes. Older plan text that quotes a higher figure per run predates the
probe; do not use it.

Handler rules, from the live probe (decisions D26 and D27 in [gaps-and-decisions.md](../../.plans/crawlers/gaps-and-decisions.md)):

- The worker checks robots.txt itself before every Cloudflare call and sends the identifying User-Agent.
- Cloudflare answers 200 when the target answered 404. The handler reads `meta.status` and refuses 400 and above (5xx
  retryable, 4xx permanent). It stores `meta.finalUrl` as the artifact's `final_url`.
- A login wall completes the task with the note `login_wall` and no upload. A login-looking task URL or final URL, or a
  password field in the DOM, counts.
- A snapshot above 4 MB or a screenshot above 8 MB completes with `oversize` and stores nothing. Its browser time is
  still settled.
- A rejected token (401 or 403) releases the batch, stops with `error` and exits 1.

A drain of a browser kind exits **2** before claiming when `CLOUDFLARE_ACCOUNT_ID` or `CLOUDFLARE_BROWSER_API_TOKEN` is
missing, and exits **1** when `GET /api/v1/discovery/machine/artifacts/status` shows `storage_enabled: false`.
The token needs only "Browser Run - Edit". It is a GitHub Actions secret and a local variable. It is not a Render
variable, and the API never reads it.

### LLM kind (`llm_extract`, Cloudflare Workers AI)

`llm_extract` calls Workers AI over HTTP, in JSON mode, for one stored snapshot per task. The worker, not the API,
holds the token. Staged output only: mentions, edges and tag codes; nothing is emitted. Settings and commands:
[`apps/discovery-ingest/README.md`](../../apps/discovery-ingest/README.md) § Drain `llm_extract`. What the staging
holds: [discovery-layer.md](discovery-layer.md) § Extracted documents, edges and tags.

| Free-plan fact | Worker behaviour |
| --- | --- |
| 10,000 neurons a day on Workers Free | The ledger resource `neurons` caps the day at 9,500. A run budget (`--neuron-budget`) caps the run, the smaller of the two wins |
| Every call must be paid before it is made | The worker reserves the page's input tokens at the input price plus an answer sized to the page (500 tokens and a quarter of the page, never above `LLM_MAX_TOKENS`, 4000), about 890 neurons for a 30,000-character page on the 70b model. A denial stops the run `llm_budget` before the call |
| The API reports the real cost | After the call the worker settles to `usage.neurons` from the response, falling back to the priced token usage. A real answer above its reserve corrects upward. A call is allowed while the run and the day are below their limits, so the last call may pass the budget by its own cost: the overshoot is at most one call per run, and the ledger can end the day slightly above 9,500 |
| `429` with code 4006 ("daily free allocation") | The provider says the day is used up. The worker marks `neurons` exhausted, releases the batch and stops `llm_quota` |

**The ledger is not the whole meter.** The ledger counts what drains and `llm eval` reserve. Cloudflare's own daily
allocation counts all Workers AI use on the account, including `llm probe` calls and any run that bypasses the ledger.
A `429` code 4006 can therefore arrive while the ledger still shows neurons left. The run then stops `llm_quota`, the
tasks are released, and the next UTC day starts clean. Do not retry the same day.

**Limits release, pages fail.** `llm_budget`, `llm_quota`, `db_limit` and `storage_unavailable` release the in-flight
and unstarted tasks and end the run successfully. A rejected token (401 or 403) stops with `error` and exit 1. An
answer that is not usable JSON is retried once under a second reservation; then the task fails permanently, because the
page, not a limit, was the problem. A ledger that stops answering mid-run falls back to the run budget and the report
says `ledger_unavailable`.

**Result notes** (the task's `note`, shown on `/admin/discovery/tasks`):

| Note | Meaning |
| --- | --- |
| `docs=7 edges=5 dropped=2` | Mentions and edges were posted; `dropped` items failed grounding |
| `no_documents` | The model found no document, or grounding dropped them all |
| `login_wall` | The model judged the page a login or error page; nothing is posted |
| `no_content` | The cleaned text is under 200 characters (usually a client-side shell that needs `render_page` first); no call and no reservation |

The Coverage screen counts completed `llm_extract` tasks by outcome (`extracted`, `no_documents`, `login_wall`,
`no_content`) and shows the neuron meter next to them.

**Optional category codes.** `category_codes` may come back as an empty list; the extraction is still staged and
counted as `extracted`, not dropped, when every other field is usable. The model output has no domain or situation
fields: a payload that still uses the retired fields is rejected. Confirmed at `PageExtraction.category_codes` in
[`apps/discovery-ingest/discovery_ingest/extract/llm/schema.py`](../../apps/discovery-ingest/discovery_ingest/extract/llm/schema.py)
(`default_factory=list`, no `min_length`, at most 5 codes).

**Queueing.** A render drain with `LLM_ENQUEUE=true` and `LLM_MODEL` queues one `llm_extract` task per stored snapshot
(priority 200). `LLM_MODEL` defaults to the X16 choice `@cf/qwen/qwen3-30b-a3b-fp8` (override it with
`LLM_MODEL`; an empty value means no model). `discovery-render.yml` sets `LLM_ENQUEUE: "true"` and `LLM_MODEL` in its
job `env` by default, so scheduled renders queue `llm_extract` work automatically; a laptop render with `LLM_ENQUEUE=true`
exported does the same. `llm requeue` queues the backlog. A task's identity is the catalogue row, the kind, the target URL and the key
`llm:<8 hex>` (model, `PROMPT_VERSION`, `CLEAN_VERSION`), so a re-render of the same page under the same versions never
queues a second task.

### Snapshots, screenshots and the storage limits

- **Snapshot:** the rendered DOM as `text/html`, up to 4 MB, the latest two per catalogue row, deduplicated by sha256.
- **Screenshot:** a full-page JPEG at quality 80 (PNG was 3.4 times slower), up to 8 MB, kept. A screenshot costs about
  1–2.5 seconds of browser time plus the 11 second gap, and 60–300 KB of storage.
- **Follow-ups:** a stored snapshot enqueues `extract_page` (priority 100, `input_key` `<extractor id>@<version>`) only
  when an extractor matches. An extraction that posted a mention enqueues `capture_screenshot` (priority 300,
  `input_key` `shot@1`). A version bump re-extracts but never re-captures.
- **Storage unset:** artifact routes answer **503**; a browser drain refuses to start; a run in flight stops
  `storage_unavailable`.
- **Byte cap:** an upload answers **507** when the stored bytes plus the new file would pass `OBJECT_STORE_MAX_BYTES`
  (default 9.5 GB, 95 percent of the R2 free 10 GB). The cap sums `discovery_artifact` rows, not objects in the bucket.
- **Database soft limit:** machine writes that create rows answer **507** `database_soft_limit` above
  `DB_SOFT_LIMIT_BYTES` (475 MB). Workers stop `db_limit`.

The budget ledger (`GET /api/v1/discovery/machine/budgets`, admin `GET …/admin/budgets`) keeps R2 operations, browser
seconds, neurons and Actions minutes, so GitHub runs and laptop runs share one count. Caps and settings:
[deployment-checklist.md](deployment-checklist.md) and [scheduled-jobs.md](scheduled-jobs.md).

### Run a browser drain on a laptop

This costs no Actions minutes. Export `DISCOVERY_API_URL`, `DISCOVERY_API_KEY` and the two Cloudflare variables, then:

```bash
cd apps/discovery-ingest && pip install -e .
python -m discovery_ingest worker drain --kinds render_page --max-tasks 5 --max-batches 40 \
  --time-budget-seconds 900 --browser-budget-seconds 570
```

To capture the pages that were categorised before any screenshot was queued, run `capture requeue`, then drain
`capture_screenshot` (it needs only `DISCOVERY_API_URL` and `DISCOVERY_API_KEY`; the drain needs the Cloudflare
variables). Use `--dry-run` first to count the pages:

```bash
python -m discovery_ingest capture requeue --limit 50 --dry-run
python -m discovery_ingest capture requeue --limit 50
python -m discovery_ingest worker drain --kinds capture_screenshot --max-tasks 5 --max-batches 40 \
  --time-budget-seconds 900 --browser-budget-seconds 570
```

Run it at most once a day. The check of the Cloudflare credentials needs only the two Cloudflare variables:
`python -m discovery_ingest browser probe --url https://example.com`.

### Triage by task kind

| Kind | Symptom | Check |
| --- | --- | --- |
| any | `stale_claims` above zero | A worker died mid-batch. The next claim reclaims expired leases; re-run a bounded drain |
| any | `stale_runs` above zero | A run never finished. It stays visible as stale and is not counted as successful |
| any | `last_successful_run` old or empty | Check recent `discovery_run` failures and the drain `stop_reason` |
| `fetch_url` | Many `failed` with 4xx | Permanent by design. Open the task on `/admin/discovery/tasks` and check the URL |
| `fetch_url` | Tasks pending with a future retry time | Backoff in progress (5 minutes, 30 minutes, 3 hours). `remaining` does not count them |
| `harvest_payload` | Few candidates | Check `/admin/discovery/documents`; only PVOG modules `08` (required) and `14` (form) are read |
| `render_page` | Run ends `browser_budget` or `browser_quota` | Expected. Tasks were released. Try again tomorrow |
| `render_page` | Notes `login_wall` or `oversize` | The page is skipped on purpose; nothing is stored |
| `render_page`, `capture_screenshot` | Run ends `storage_unavailable` | Check `GET …/artifacts/status` and the Render `OBJECT_STORE_*` variables |
| any | Run ends `db_limit` | Check the database size against 475 MB (checklist S8) |
| `extract_page` | All tasks completed with `no_extractor` | No extractor is registered yet. Expected today |
| `llm_extract` | Run ends `llm_budget` | The run budget or today's neurons cannot cover the next reservation. Expected. A budget under about 900 neurons cannot run a 30,000-character page; use at least 2,500 |
| `llm_extract` | Run ends `llm_quota` | Cloudflare's own allocation is used up (code 4006), possibly by probes the ledger never saw. Tasks were released. Wait for 00:00 UTC |
| `llm_extract` | Many `no_content` notes | Client-side shells. Run `render_page` for the host first (all of `verwaltung.bund.de` is like this) |
| `llm_extract` | Many `no_documents` | Check a sample on `/admin/discovery/tasks`; pages that are lists or navigation pages are correct. A host with real documents and a `no_documents` note is a prompt or cleaner finding for the ledger, not a retry |
| `llm_extract` | Task `failed` with an invalid-answer error | The model returned unusable JSON twice. Permanent for this model and prompt version; try another model through `llm requeue` |
| `llm_extract` | Run exits 1 before claiming | The ledger, artifact storage or `GET /machine/taxonomy` cannot be read. Check the API deploy |
| `llm_extract` | Run exits 2 | `CLOUDFLARE_ACCOUNT_ID`, `CLOUDFLARE_AI_API_TOKEN`, `LLM_MODEL` (empty, or without a price row) or `--neuron-budget` is missing |
| any | `failures_by_source` growing | Inspect failed tasks on `/admin/discovery/tasks` for that source |

### Manual dispatch (debugging)

GitHub → **Actions** → **Platform maintenance** → **Run workflow**, or:

```bash
gh workflow run platform-maintenance.yml -f job=discovery
gh workflow run platform-maintenance.yml -f job=openplz
gh workflow run platform-maintenance.yml -f job=all
```

`workflow_dispatch` runs only the job named in `job` (`all` runs OpenPLZ, then discovery).

### Repository secrets

| Secret | Discovery job | Notes |
| --- | --- | --- |
| `DISCOVERY_API_URL` | yes | Host root, e.g. `https://redtape-api.onrender.com` — client adds `/api/v1/discovery/machine/...` |
| `DISCOVERY_API_KEY` | yes | `rt_…` from `python -m scripts.issue_api_key --name discovery-scheduled-gha` in `apps/api` |
| `FEDERAL_JURISDICTION_ID` | yes | Must equal live `jurisdiction.id` for `kind=COUNTRY`, `code=DE` (see triage below) — not always the seed UUID after OpenPLZ. Resolve: production SQL below, or `python -m scripts.print_federal_jurisdiction_id` in `apps/api` against the same DB |
| `DATABASE_URL` | **no** | OpenPLZ job only |
| `CLOUDFLARE_ACCOUNT_ID`, `CLOUDFLARE_BROWSER_API_TOKEN` | no | `discovery-render.yml` and `discovery-browser-probe.yml` only; never Render |
| `CLOUDFLARE_AI_API_TOKEN` (with `CLOUDFLARE_ACCOUNT_ID`) | no | `discovery-llm.yml` and `discovery-llm-probe.yml` only; the Workers AI permission only; never Render |
| `OBJECT_STORE_*` (five names) | no | `discovery-storage-probe.yml` only; the application reads them from Render |

Issue and rotate keys: [auth-setup.md](auth-setup.md#7-issue-and-revoke-crawler-keys). Render admin
allowlist (`DISCOVERY_ADMIN_EMAILS`) is for the web UI — not used by the GHA discovery job.

### Failure triage

| Symptom | Check |
| --- | --- |
| `discovery` job skipped | Expected when dispatched with `job=openplz`; scheduled runs always run it; see [scheduled-jobs.md](scheduled-jobs.md) |
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
([`seed_jurisdictions.ID_DE`](../../apps/api/scripts/seed_jurisdictions.py)); after **OpenPLZ** import,
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
- A task is not duplicated for the same `(catalogue_service_id, kind, target_url, input_key)` while it is `pending`,
  `claimed` or `completed`. A failed task, a changed `portal_url` or a new `input_key` (an extractor or harvester
  version bump) may enqueue again. A completed `fetch_url` task is therefore not fetched again, and no `render_page`
  follows it, until the operator re-pends it (checklist S14).
- `discovery_claim` rows dedupe by entity, kind, and payload fingerprint.
- Races on unique constraints recover via re-select after `IntegrityError` (same pattern as OpenPLZ).

Re-running **Platform maintenance** with `job=discovery` on the same day is safe for staging data;
it must not multiply tasks or claims without bound.

## Laptop debugging (secondary)

Use [discovery-layer.md](discovery-layer.md) for local Postgres, fixture ingest, FIM/LeiKa enrich,
admin smoke, and **manual** `POST …/catalogue/{id}/emit`. Corporate proxy env for live GovData/PVOG
from a laptop is documented there.

## Related

- Maintenance schedule, drain workflows and secrets: [scheduled-jobs.md](scheduled-jobs.md)
- Operator steps for `llm_extract`: [extraction-operator-checklist.md](extraction-operator-checklist.md); suite and known gaps: [loops/extraction.md](loops/extraction.md)
- Manual steps that unlock live gates: [crawlers-operator-checklist.md](crawlers-operator-checklist.md)
- Actions minutes: [gha-budget.md](gha-budget.md)
- Suite orchestration and known gaps: [loops/crawlers.md](loops/crawlers.md)
- OpenPLZ import (database path): [openplz-import.md](openplz-import.md)
- Architecture and decisions: [`.plans/discovery-online/`](../../.plans/discovery-online/00-architecture.md)
