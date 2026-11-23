# Crawlers: human steps after the release deploys

What a person still has to do once Render has redeployed the crawlers release (PR #217 merged to `main`). Everything
else is in the code, tested against fakes. Nothing here is automated, because each step needs a console, a database
editor, a billing page or human judgement.

This page is the short path. The full step list, the SQL and the rationale are in
[crawlers-operator-checklist.md](crawlers-operator-checklist.md). The commands that only dispatch a workflow and read
its log (the live gates) are the table under step S7 of that checklist; any session with `gh` access can run them, so
they are not repeated here. Tick the boxes in the checklist as you go and write the date and run ID in the ledger
([`run-ledger.md`](../../.plans/crawlers/run-ledger.md)).

Never paste a secret, a token or an access key into the repository, a commit or a chat.

## 0. Before you start

- [ ] **GitHub Actions minutes work again.** The monthly quota resets around 2026-11-01. Dispatching a workflow before
  that fails in seconds with no steps. Check: Settings, Billing and plans, Usage.
- [ ] **Browser time.** Cloudflare's free plan allows 10 browser minutes a day. Run at most one browser drain a day.

## 1. Confirm the deploy came up (Render dashboard)

- [ ] **The deploy succeeded** and `/health` answers. The API applies `alembic upgrade head` and the seed scripts on
  every boot, so a failed boot is almost always a migration or a seed error: read the deploy log.
- [ ] **The log shows the two new migrations applied:** `20261027_artifacts` and `20261028_budget_ledger`
  (`alembic upgrade head` is the last migration line). Both are additive: new tables, nullable columns and new enum
  labels.
- [ ] **If the deploy failed, roll back in Render** (Deploys, previous deploy, Rollback). The new schema does not break
  the previous code, because nothing existing was renamed or dropped, so a rollback needs no database change. Then ask
  for the log to be read before retrying.

## 2. Make the new routes and workflows usable

- [ ] **The workflows are registered.** `gh workflow list` shows `discovery-render.yml`, `discovery-browser-probe.yml`,
  `discovery-storage-probe.yml`, `discovery-fim-probe.yml` and `discovery-fixture-capture.yml`. Until the release was on
  `main`, `gh workflow run <file>` answered 404.
- [ ] **S17: storage is ready.** From a shell with your Discovery API key and host (a person must hold the key, it is not
  recoverable from GitHub):

  ```bash
  curl -s -w "\nHTTP %{http_code}\n" -H "X-API-Key: $DISCOVERY_API_KEY" \
    "$DISCOVERY_API_URL/api/v1/discovery/machine/artifacts/status"
  ```

  | Result | Meaning |
  | --- | --- |
  | 404 | The old API is still deployed. |
  | 401 or 403 | The key or `DISCOVERY_API_URL` (host root, no path) is wrong. |
  | 200 with `"storage_enabled": false` | New code is live, but the Render `OBJECT_STORE_*` variables are missing or wrong. |
  | 200 with `"storage_enabled": true` | Done. |

- [ ] **S6: storage probe passes.** Needs the R2 secrets, so a person triggers it (the workflow reads the five GitHub
  secrets) or runs it from a laptop with the values exported:

  ```bash
  gh workflow run discovery-storage-probe.yml && gh run watch
  # or: cd apps/api && set -a; source <env file>; set +a; .venv/bin/python -m scripts.object_store_probe
  ```

  Every step must pass, including the unauthenticated GET of the presigned URL. Record the run ID and the recommended
  checksum variant. The code ships `when_required`; if only `when_supported` passes, ask for the default to be changed.
  If the presigned GET fails, stop and ask for the plan to be revised: chapters 14 and 16 change.
- [ ] **`GET /api/v1/discovery/machine/budgets` lists five resources with caps** (same `X-API-Key` header). It confirms
  migration `20261028_budget_ledger` and your Render cap variables.

## 3. Database steps (Supabase SQL editor)

These change production rows, so a person runs them after reading the dry-run count. The statements are in the
checklist; this is only the order.

- [ ] **S11: repair mis-recorded fetch tasks.** Run the count query first, then the two updates (redirects recorded as
  completed, and the two transport failures). The updates also reset `attempt_count` and `not_before`.
- [ ] **Run the chapter 2 to 5 live gates** (dispatch `discovery-drain.yml`, checklist S7 table), then the chapter 7 and
  12 gates. Any session can do this part.
- [ ] **S14: re-pend completed fetches so each page gets a render task.** Only after the drain gates above pass and
  `GET /machine/artifacts/status` is `storage_enabled: true`. Run the count first (about a hundred pages).

## 4. Repository variables (GitHub settings)

Both schedules ship switched off. A person decides when to enable them.

- [ ] **`DISCOVERY_DRAIN_SCHEDULE=enabled`** only after S14 is done and a render run has produced snapshots. Otherwise
  the backlog is fetched without enqueuing any render.
- [ ] **`DISCOVERY_RENDER_SCHEDULE=enabled`** only after the render live gate. A
  render run is about 15 runner minutes, which D17 leaves unmetered for this repository.
  Leaving it unset and dispatching by hand (or running the drain on a laptop, S18) is a valid choice. To pause a
  schedule, delete its variable; manual dispatch keeps working.

## 5. Judgement calls and visual checks (only a person can do these)

- [ ] **Open the admin as an allowlisted admin and look.** Tasks (kind filter, `render_page`, the result-note chips,
  retry columns), Coverage (kind chips, artifact bytes and the 80 percent warning, budget meters), Documents (list and
  detail, evidence panel, emit preview), the single row of menu icons. Check light and dark, `de` and `en`, and a
  360 px wide window.
- [ ] **S10: review the first candidates, then emit.** Read excerpts and evidence for a handful of candidates. Dry run
  with `--all-staged --min-mentions 3 --limit 5 --dry-run`, emit five, inspect the pending suggestions, record counts and
  ids. Never bulk-emit before the first five are reviewed.
- [ ] **Check one enriched GovData row (chapter 12).** In the admin pipeline view it should show an entity **with a label** (taken from the steckbrief `title`), claims and stage T3. A row has no `metadata` claim: the real steckbrief carries no `kurztext`.
- [ ] **Spot-check harvest quality (chapter 7).** Open ten candidates and compare each against its source procedure.
  Record the precision you see. Also check that form links really carry `title` and `uri` and that the language code is
  read correctly (both were assumed from documentation).
- [ ] **Read one rendered snapshot against its plain fetch** before the roughly 22-run backlog starts, to confirm the
  rendered page is richer (the "plain first" open seam in [gaps-and-decisions.md](../../.plans/crawlers/gaps-and-decisions.md)).
- [ ] **Download one HTML snapshot from the admin** within five minutes of opening the page and confirm the link stops
  working after it expires.
- [ ] **Native review of the German strings.** About 88 keys, machine-written, listed at the end of the checklist.

## 6. Cloudflare and billing consoles

- [ ] **Browser usage.** Cloudflare dashboard, Browser Run usage: note the minutes a render run used. About 26 of the 600
  daily seconds went on probing on 2026-10-27, which resets daily.
- [ ] **R2 and billing.** Confirm the account is still on the Workers Free plan, the billing notifications from S19 are
  active, and R2 operations and storage are far below the free allowance after the first render run.
- [ ] **Finish the browser probe when you have a quiet day** (optional): the daily-limit 429 body, a real login page and
  the pixel size of a full-page JPEG were not probed. The first live run will also reveal them.

## 7. Monthly and ongoing

- [ ] **S20: Actions usage (retired by D17).** Nothing to compare. This repository is public, and its standard runners
  are not metered. `python -m discovery_ingest budget show` still prints `actions_minutes` for the stage prechecks.
- [ ] **S8: watch the limits** monthly or when an alert arrives: Supabase database size (500 MB, soft limit 475 MB),
  R2 bytes and operations, browser minutes.
- [ ] **S9: rotation.** Rotate the R2 key and the Cloudflare token when needed; the steps are in the checklist.

## 8. Tell the plan what you found

- [ ] Record, in the ledger, the run ID of each live gate you ran, the observed browser seconds per page and pages per
  run, the artifact ids you checked, and anything that differed from the docs.
- [ ] If a render run ends on `browser_quota`, `browser_budget`, `storage_unavailable` or `db_limit`, that is a limit
  working as designed, not a failure: tasks were released, not failed. Report only if tasks were marked failed.
