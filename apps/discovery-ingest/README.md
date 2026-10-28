# discovery-ingest

CLI workers that upsert discovery catalogue rows, drain the crawl task queue and emit reviewed document candidates via
the RedTape machine API (`X-API-Key`). The workers use HTTP only: they never receive `DATABASE_URL`.
There is no browser in this package. Rendering and screenshots are HTTP calls to Cloudflare Browser Run.

## Commands

Run `python -m discovery_ingest <command> --help` for every flag.

| Command | Purpose |
| --- | --- |
| `govdata run`, `govdata fetch`, `pvog run` | Catalogue ingest into staging |
| `fim enrich`, `leika enrich` | Upsert entity and claims from a saved steckbrief or stammtext |
| `fim probe --keys K1,K2` | Report status and top-level keys of live steckbriefe; exit 1 when the gate fails, 2 for a malformed key |
| `worker drain` | Claim, process and settle tasks; see below |
| `candidates emit` | Emit staged document candidates as pending suggestions; see below |
| `browser probe` | Call every Cloudflare quick action the worker uses and print a table |
| `llm probe --model <id> --fixture <html>` | Send one cleaned page to each Workers AI model and print envelope, usage, cost and quality tables |
| `llm eval --model <id>` | Run the gold set through the cleaner, a model and grounding; print precision, recall, grounded rate, tag agreement and neurons per page |
| `artifacts list`, `artifacts download` | List stored snapshots of a host and write one to a file |
| `budget show`, `budget report-minutes` | Show the budget ledger; add Actions minutes to it |

### Drain tasks

```bash
python -m discovery_ingest worker drain --kinds fetch_url,harvest_payload --max-tasks 50 --max-batches 5 \
  --time-budget-seconds 300
```

| Flag | Default | Meaning |
| --- | --- | --- |
| `--kinds` | `fetch_url,enrich_metadata,harvest_payload,extract_page` | Task kinds to claim; an unknown kind exits 2 before any claim |
| `--max-tasks` | 50 (5 for `llm_extract`) | Tasks per claim request (1–50) |
| `--max-batches` | 1 | Maximum batches |
| `--time-budget-seconds` | none | Wall-clock budget for the whole drain |
| `--browser-budget-seconds` | 570 | Browser seconds for `render_page` and `capture_screenshot` |
| `--neuron-budget` | none | Workers AI neurons for `llm_extract`; required for that kind |

The command prints one JSON report with `stop_reason`, `remaining`, `released`, `browser_seconds_used`, `neurons_used`
and `llm_calls`. Kinds,
retry rules, stop reasons and the free-plan limits are in
[`docs/operations/discovery-online.md`](../../docs/operations/discovery-online.md).

### Emit document candidates

```bash
python -m discovery_ingest candidates emit --all-staged --min-mentions 3 --limit 5 --dry-run
python -m discovery_ingest candidates emit --id <candidate-uuid>
```

`--dry-run` calls the read-only preview and writes nothing. `--limit` is 1–50 (default 10). Emit is manual and
idempotent per candidate. See [`docs/operations/discovery-layer.md`](../../docs/operations/discovery-layer.md)
§ Manual candidate emit.

## Environment

`DISCOVERY_API_URL` is the **API host root** — not the machine path. The client appends
`/api/v1/discovery/machine/...` (see [`api_client.py`](discovery_ingest/api_client.py)).

| Variable | Required | Example |
| --- | --- | --- |
| `DISCOVERY_API_URL` | yes | `http://localhost:8000` or `https://redtape-api.onrender.com` |
| `DISCOVERY_API_KEY` | yes | `rt_…` from `python -m scripts.issue_api_key` in `apps/api` |
| `GOVDATA_CKAN_BASE_URL` | no | Default in [`config.py`](discovery_ingest/config.py) |
| `PVOG_API_BASE_URL` | no | Default in `config.py` |
| `FIM_PORTAL_BASE_URL` | no | Default in `config.py` |
| `BOT_CONTACT_URL` | no | Contact URL in the `RedtapeBot/1.0 (+<url>)` User-Agent; defaults to the repository URL |
| `CLOUDFLARE_ACCOUNT_ID`, `CLOUDFLARE_BROWSER_API_TOKEN` | only for browser kinds and `browser probe` | Cloudflare account and a custom token with only "Browser Run - Edit". Never a Render variable; never commit them |
| `CLOUDFLARE_AI_API_TOKEN` | only for `llm probe` and `llm_extract` | A custom token with only the Workers AI permission, next to `CLOUDFLARE_ACCOUNT_ID`. Never a Render variable; never commit it |
| `LLM_MODEL`, `LLM_MAX_TOKENS`, `LLM_INPUT_CHARS`, `LLM_REQUEST_TIMEOUT_SECONDS` | no | Model id (chosen by the eval), output cap (1500), page characters sent (12000) and per-call timeout (60) |
| `BROWSER_MIN_INTERVAL_SECONDS`, `BROWSER_REQUEST_TIMEOUT_SECONDS` | no | Seconds between the end of one Cloudflare call and the start of the next (default 11) and the per-call timeout (default 60) |

Copy [`.env.example`](.env.example) to `.env` for local runs.

### Issue a machine API key

From `apps/api` (venv active, migrations applied):

```bash
python -m scripts.issue_api_key --name discovery-ingest-local
```

GitHub Actions scheduled discovery uses `discovery-scheduled-gha` — store the printed key in the
`DISCOVERY_API_KEY` repository secret. See [`docs/operations/scheduled-jobs.md`](../../docs/operations/scheduled-jobs.md).

## GovData OZG

```bash
export DISCOVERY_API_URL=http://localhost:8000
export DISCOVERY_API_KEY=rt_<your-key>
python -m discovery_ingest govdata run \
  --input path/to/ozg-export.json \
  --jurisdiction-id 11111111-1111-1111-1111-111111111101
```

Federal rows (`ars` `000000000000`) use `--jurisdiction-id` as the Germany country jurisdiction UUID.

Operations runbook: [`docs/operations/discovery-layer.md`](../../docs/operations/discovery-layer.md).

## Render pages through Cloudflare Browser Run

`render_page` and `capture_screenshot` tasks spend Cloudflare browser time, so they are never in the default kinds. The
free plan allows 10 browser minutes a day and one request every 10 seconds. Every run also shares one daily budget
ledger (`GET /machine/budgets`) with every other run, so a laptop run and a GitHub run never overspend together.

```bash
# Check the quick actions and the credentials (prints a table, never the token; needs only the two Cloudflare variables):
python -m discovery_ingest browser probe --url https://example.com --variant content

# Drain the render queue; fails before claiming without the Cloudflare variables or artifact storage:
python -m discovery_ingest worker drain --kinds render_page --max-tasks 5 --max-batches 40 \
  --time-budget-seconds 900 --browser-budget-seconds 570
```

`browser probe` takes `--url` (repeatable), `--error-url`, `--variant` (repeatable) and `--max-browser-seconds`
(default 240). It exits 2 when a Cloudflare variable is missing and 1 when Cloudflare refused.

### Probe Workers AI

The free plan allows 10,000 neurons a day. `llm probe` sends one cleaned page to each model and prints a table per
model: the response envelope, token usage, whether `response_format` is accepted, the cost in neurons by the price
table, a grounded sample of the answer and the cleaner against `toMarkdown`. It never prints the token and needs only
`CLOUDFLARE_ACCOUNT_ID` and `CLOUDFLARE_AI_API_TOKEN`.

```bash
python -m discovery_ingest llm probe --model @cf/meta/llama-3.3-70b-instruct-fp8-fast \
  --model @cf/meta/llama-3.1-8b-instruct --fixture tests/fixtures/pages/table_page.html
```

`--max-neurons` (default 900) stops the probe before the next model once the computed spend reaches it. It exits 2 when
a variable, the fixture or a model is missing and 1 when Cloudflare rejected the token or the daily allowance is gone.
The manual workflow `discovery-llm-probe.yml` runs the same command.

### Evaluate a model on the gold set

`llm eval` measures one model and prompt version on the 20 real pages of `tests/fixtures/gold/` (see its README: the
labels are drafted and need a human review). Each page is cleaned, sent to the model and grounded, and the table shows
the pooled precision and recall of documents, the same for edges, the grounded rate (the share of raw model items that
quote the page), the tag agreement, the cleaner recall, the neurons per page and the pages per day that follows from
it. Next to each metric the table prints the starting target of decision X14.

```bash
python -m discovery_ingest llm eval --model @cf/meta/llama-3.1-8b-instruct --neuron-budget 4000 --out /tmp/eval-1.json
```

It needs `DISCOVERY_API_URL` and `DISCOVERY_API_KEY` (the budget ledger and `GET /machine/taxonomy`) next to the two
Cloudflare variables, and it never prints the token. Every call reserves neurons from the ledger first, so an eval
cannot spend more than the day has left.

- `--neuron-budget` (default 4000) ends the run before the page that would pass it. The pages done so far are
  printed and written, and the exit code is 1. A spent day, a provider quota error (the ledger is told) or a rejected
  token end the run the same way. An unreadable ledger or a spent day refuses to start (exit 1).
- `--limit N` runs the first N pages by name. `--prompt-version` must match the checkout (`ext-1`); the option names
  the version a result belongs to, it does not select a wording. Exit 2 means a missing variable, an unpriced model or
  a gold label outside the taxonomy.
- `--out FILE` writes the per-page results and, for every item grounding dropped, its reason (`quote`, `duplicate`,
  `noise`, `dependency_endpoint`, `dependency_quote`, `dependency_duplicate`, or `page_kind` for a login page).
- Answers are cached in `--cache-dir` (default `.llm-eval-cache/`, ignored by git) by model, prompt version, cleaner
  version, vocabulary and page text, so a re-run of an unchanged page costs nothing. The cached cost is still reported.
- A page whose cleaned text is empty (a client-side shell) is not sent and scores as nothing found.

### Drain `llm_extract`

`llm_extract` reads a stored snapshot, cleans it, asks the model for documents, dependencies and tags, grounds the
answer against the page and stages mentions, then edges. It is never in the default kinds. Name it explicitly, with a
neuron budget:

```bash
python -m discovery_ingest worker drain --kinds llm_extract --max-tasks 5 --max-batches 1 --neuron-budget 800
```

The drain exits before claiming anything when a requirement is missing: exit 2 for `CLOUDFLARE_ACCOUNT_ID`,
`CLOUDFLARE_AI_API_TOKEN`, `LLM_MODEL` (a model with a price row), or `--neuron-budget`; exit 1 when the neuron ledger
(`GET /machine/budgets`), artifact storage or the taxonomy (`GET /machine/taxonomy`) cannot be read. An llm drain claims
5 tasks per batch unless `--max-tasks` says otherwise.

Every model call reserves its estimated neurons first and settles to the token usage afterwards. A page whose cleaned
text is under 200 characters (a client-side shell) completes as `no_content` without a reservation or a call. Other
completion notes are `login_wall`, `no_documents` and the counts of a posted page, for example `docs=7 edges=5
dropped=2`. An unusable model answer is retried once under a second reservation, then the task fails permanently.

A spent run budget or day (`llm_budget`), a provider quota error (`llm_quota`, the ledger is told), the database soft
limit (`db_limit`) and unavailable storage release the in-flight and unstarted tasks and end the run successfully. A
rejected token ends it as `error` (exit 1). A ledger that stops answering falls back to the run budget and the report
says `ledger_unavailable`.

### Run a browser drain on your machine

This costs no GitHub Actions minutes. Export `DISCOVERY_API_URL`, `DISCOVERY_API_KEY`, `CLOUDFLARE_ACCOUNT_ID` and
`CLOUDFLARE_BROWSER_API_TOKEN`, then run the drain above. The worker needs artifact storage on the API: it exits 1
before claiming when `GET /machine/artifacts/status` shows `storage_enabled: false`, and 2 when a Cloudflare variable is
missing. Run it at most once a day. The pace is about 4 pages a minute, because the worker leaves 11 seconds between
calls (`BROWSER_MIN_INTERVAL_SECONDS`).

A browser limit (`browser_budget`, `browser_quota`), unavailable storage (`storage_unavailable`) or the database soft
limit (`db_limit`) releases the in-flight and unstarted tasks and ends the run successfully. Only a rejected token or
an API failure fails it. The manual workflows are `discovery-browser-probe.yml` and `discovery-render.yml`.

A stored snapshot queues `extract_page` when an extractor matches it. An extraction that posts at least one mention
queues `capture_screenshot` (see the next section). No extractor is registered yet.

## Extract mentions from stored snapshots

After a snapshot is stored, the render worker queues an `extract_page` task, but only when a registered extractor
matches the page (`discovery_ingest/extract/registry.py`; empty until the first host extractor ships). `extract_page`
needs no network and is in the default kinds. When it posts at least one mention, the worker also queues a
`capture_screenshot` task for the page (priority 300, `input_key` `shot@1`, so a later re-extraction never queues a
second capture). An extractor implements `matches(url, content_type)` and
`extract(html, ctx)`; the task's `input_key` is `<id>@<version>`, so a version bump queues a new task for the same
snapshot. A task whose extractor is gone completes with the note `no_extractor`; a page without mentions completes with
`no_mentions`.

Real markup for extractor tests comes from the stored snapshots:

```bash
python -m discovery_ingest artifacts list --host verwaltung.bund.de --limit 5
python -m discovery_ingest artifacts download --id <artifact-id> --out tests/fixtures/verwaltung/page.html
# Or without credentials on a laptop: run the manual workflow, then fetch its files.
gh workflow run discovery-fixture-capture.yml -f host=verwaltung.bund.de -f limit=5
gh run download <run-id> --name snapshot-fixtures
```
