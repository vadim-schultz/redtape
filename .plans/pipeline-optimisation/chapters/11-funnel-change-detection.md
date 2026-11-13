---
name: "Chapter 11 — Funnel: change detection, refresh and ingest split"
overview: "Re-render only pages whose fetched HTML has changed (or whose refresh epoch has passed), and move the catalogue ingest out of the monthly OpenPLZ job into its own weekly run with higher caps."
todos:
  - id: body-hash
    content: "Store a hash of each fetched body on the fetch log"
    status: pending
  - id: change-gate
    content: "Enqueue render_page only when the body changed or the page is older than the refresh age"
    status: pending
  - id: epoch
    content: "Key refresh tasks by an epoch so a completed render does not block the next one"
    status: pending
  - id: ingest-split
    content: "Split catalogue ingest from OpenPLZ and run it weekly with higher page caps"
    status: pending
  - id: retention
    content: "Prune fetch logs and events beyond a retention window"
    status: pending
isProject: false
---

# Chapter 11 — Funnel: change detection, refresh and ingest split

**Repo:** `redtape` · **Branch:** `feat/pipeline-optimisation-funnel` · **Status:** planned
**Depends on:** [2](02-observability-run-hygiene.md), [4](04-queue-hardening.md) · **Architecture:** [../00-architecture.md](../00-architecture.md) (section 3, items 2 and 5) · **Decisions:** D4

**Loop branch:** `feat/plans-pipeline-optimisation` · **Release branch:** `main`

## Goal

A completed render blocks any later render of the same page, so the funnel can only feed new pages, and the catalogue is ingested once a month. Refresh stale pages on a cadence, re-render only what changed, and ingest the catalogue weekly. Plain HTTP fetches cost no Cloudflare allowance, so detect change before paying for a browser call.

## Design

- **Body hash.** `fetch_url` (`worker/fetch_url.py`) already logs the body length (`FetchLogAppendRequest`). Add `body_sha256` to the fetch log (a nullable column, populated from now on) and to the request body.
- **Change gate.** `render_enqueue._earns_a_render` (`worker/render_enqueue.py`) enqueues `render_page` only when the hash differs from the last stored one, or when the last render is older than `REFRESH_MAX_AGE_DAYS` (default 30).
- **Epoch identity.** Refresh renders use an `input_key` of `rr:<ISO week>`, so a completed render does not block the next epoch. Renders for a new page keep the empty key and the old identity.
- **Weekly catalogue ingest.** `platform-maintenance.yml` keeps the monthly OpenPLZ import. The GovData and PVOG steps move to a new weekly workflow, `discovery-catalogue.yml`, with `--max-pages` raised from 15 and 50 to values set by a variable (`CATALOGUE_GOVDATA_MAX_PAGES`, `CATALOGUE_PVOG_MAX_PAGES`). Concurrency group `discovery-pipeline`, `cancel-in-progress: false`.
- **Retention.** A pruning job in the API deletes fetch-log rows and events older than `EVENT_RETENTION_DAYS` (default 180) in batches. It never deletes a row that is the latest fetch of its target.

## Files

**Edit**

- `apps/discovery-ingest/discovery_ingest/worker/fetch_url.py`
- `apps/discovery-ingest/discovery_ingest/worker/render_enqueue.py`
- `apps/discovery-ingest/discovery_ingest/schemas.py` (the fetch request)
- `apps/api/app/features/discovery/` (the fetch-log write path and the enqueue of renders)
- `apps/api/app/config.py` (`REFRESH_MAX_AGE_DAYS`, `EVENT_RETENTION_DAYS`)
- `.github/workflows/platform-maintenance.yml` (remove the GovData and PVOG steps)

**Create**

- `.github/workflows/discovery-catalogue.yml`
- one Alembic revision adding `body_sha256` to the fetch log

**Do not edit**

- The completeness order (discovery-throughput D5, D6).

## Red tests

| Test | Asserts |
| --- | --- |
| `an unchanged body enqueues no render` | Negative: same hash, age under the limit. |
| `a changed body enqueues a render` | Happy: different hash. |
| `a page older than the refresh age is re-rendered even when unchanged` | Happy: the max-age rule. |
| `a refresh render does not block the next week's refresh` | Happy: epoch keys differ by week. |
| `a new page keeps the empty input key` | Negative: the identity of first renders is unchanged. |
| `the retention job keeps the latest fetch of every target` | Negative: the latest row survives a prune. |
| `the weekly workflow runs GovData and PVOG with the variable caps` | Happy: YAML parse and the cap variables. |

## Green

1. Write the change-gate tests, then add the hash to the fetch path and the gate.
2. Write the epoch test, then the identity change.
3. Create the weekly workflow and remove the two steps from the monthly one. Parse and run `actionlint` on both.
4. Add the retention job last, with its own test.

## Refactor gate

`render_enqueue.py` keeps one decision per function: change, age, epoch. The retention job is one repository method called from one service method.

## Verification

```bash
cd apps/api && PYTHONPATH=. .venv/bin/python -m pytest -q tests/ -k "fetch or render or retention" && cd ../..
cd apps/discovery-ingest && .venv/bin/python -m pytest -q && cd ../..
actionlint .github/workflows/discovery-catalogue.yml .github/workflows/platform-maintenance.yml
./ci.sh
```

Live gate: after the merge, dispatch `discovery-catalogue.yml` once and record its run ID and the rows it added. Confirm the next day's render count against the change-gate rate.

## Commits

`test(ingest): define change detection on fetched bodies`, `feat(ingest): hash fetched bodies and render only changes`, `test(api): define epoch keys for refresh renders`, `feat(api): key refresh renders by week`, `ci: run the catalogue ingest weekly`, `feat(api): prune fetch logs and events past retention`.

## Out of scope

The OpenPLZ import itself, the render stage's browser code (chapter 8), and the scheduling of the orchestrator (chapter 12).

## Git workflow

```bash
git checkout feat/plans-pipeline-optimisation && git pull
git checkout -b feat/pipeline-optimisation-funnel
```

Open the chapter PR into `feat/plans-pipeline-optimisation`.
