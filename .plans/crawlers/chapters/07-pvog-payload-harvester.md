---
name: "Chapter 7 — PVOG payload harvester"
overview: "Harvest document candidates from the structured PVOG payload already stored on each catalogue row, as a network-free task kind."
todos:
  - id: census
    content: "Fix the module selection table from a census of real PVOG modules"
    status: pending
  - id: parser
    content: "Pure harvester from raw_payload.details to mention items, with a noise filter"
    status: pending
  - id: fanout
    content: "Fanout rule enqueues harvest_payload for PVOG rows, keyed by harvester version"
    status: pending
  - id: handler
    content: "harvest_payload handler posts mentions and completes the task"
    status: pending
isProject: false
---

# Chapter 7 — PVOG payload harvester

**Repo:** `redtape` (`apps/discovery-ingest`, `apps/api` fanout) · **Branch:** `feat/crawlers-pvog-harvester` · **Status:** planned

**Depends on:** [06](06-candidate-staging-model-and-api.md) · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/crawlers`

## Goal

All 520 stored PVOG rows carry `details[]`: xZufi text modules with `code`, `title`, `text` (HTML), `links[]`, `filled` and `xZufiCategory`. A census on 2026-10-23 found "unterlage" in every payload, "formular" in 390 and "nachweis" in 253. Those matches may be module titles rather than content, so the first step of this chapter is to measure what is actually filled. This is the cheapest and most reliable route to document names: no HTTP request and no scraping.

## Step 0 — Census (blocking)

The operator runs the census queries from [chapter 22](22-operator-manual-steps.md) (S12) in the Supabase SQL editor and pastes the result into the chapter's ledger entry:

- F1: module `title`, `code`, `xZufiCategory` with counts of total, `filled`, and non-empty `links`;
- F2: eight filled modules whose title matches `unterlage`, with a text excerpt and their links;
- F3: sample `leika_key` / `leikakeys` next to `portal_url` (used by chapter 12).

From F1 and F2 the implementer commits `MODULE_SELECTORS`, a small table mapping a module's `code`/title pattern to a role (`required` or `form`) and to a splitting strategy (list items, paragraphs, link titles). Anonymised excerpts from F2 become fixtures under `apps/discovery-ingest/tests/fixtures/pvog/`. If F1 shows that the relevant modules are almost never filled, stop and record the finding in [gaps-and-decisions.md](../gaps-and-decisions.md); the page extractors (chapters 17 and 18) become the primary source and this chapter shrinks to what the data supports.

## Contract

**Pure harvester.** `harvest_pvog_payload(raw_payload) -> list[MentionItem]` in a new `discovery_ingest/harvest/pvog.py`:

- considers only modules chosen by `MODULE_SELECTORS`; skips `filled == false`, empty text and the literal "nicht angegeben";
- splits HTML into items (list items first, then line-separated paragraphs), strips tags and entities, collapses whitespace, removes leading bullets and numbering;
- noise filter in one place: drop items shorter than 3 or longer than 200 characters, items that are sentences ending in a full stop or colon, and items that match a small stop-list ("siehe unten", "keine");
- for `form` modules, each link yields an item with the link title as title and the link URI as `official_url`;
- title locale comes from the payload's `languageCode` (default `de`);
- `excerpt` is the surrounding text (truncated to 500 characters) and `source_field` records the module (for example `details[code=12]`);
- `extractor = "pvog-payload"`, `extractor_version` is a constant bumped on any rule change.

The HTML parsing dependency (`selectolax`, or `lxml` if wheels fail on the runner; the chapter PR's CI settles it) is added to `pyproject.toml` here and reused by chapter 17.

**Fanout.** `_harvest_spec(service)` in [fanout.py](../../../apps/api/app/features/discovery/fanout.py), added to `FANOUT_RULES`: for `source == pvog` with a non-empty `details` list, enqueue `harvest_payload` with `target_url = portal_url`, priority 50 (before network fetches), and `input_key = "pvog-payload@<version>"`. A version bump therefore produces new tasks while the same version stays idempotent. Rows already staged get their tasks on the next PVOG catalogue run, because fanout runs on upsert.

**Handler.** `handle_harvest_payload` in `discovery_ingest/worker/harvest.py`: `get_catalogue`, run the harvester, `post_mentions` in chunks of at most 100, `complete_task`. A missing catalogue row fails non-retryably; an API 5xx fails as retryable. The worker's default `--kinds` becomes `fetch_url, enrich_metadata, harvest_payload`; the API default stays on the two legacy kinds.

**Client.** `DiscoveryMachineClient.post_mentions(items)` for the route from chapter 6.

## TDD loops

### Loop A — Harvester

**Red** (`apps/discovery-ingest/tests/test_pvog_harvest.py`)

1. `harvester extracts one required mention per list item of a filled documents module`.
2. `harvester turns form links into form mentions with the link uri as official url`.
3. `harvester skips unfilled modules and placeholder text`.
4. `harvester drops sentences and stop-list items` — noise negatives from the F2 fixtures.
5. `harvester is deterministic` — same input, same ordered output.

**Green:** one function per strategy, dispatched through `MODULE_SELECTORS` rather than a conditional chain.

**Refactor:** keep each strategy about five lines; the noise filter is a single predicate.

### Loop B — Fanout

**Red** (`apps/api/tests/test_discovery_fanout.py`)

1. `pvog row with details enqueues a harvest task with a versioned input key`.
2. `govdata row and pvog row without details enqueue none`.
3. `re-fanout is idempotent for the same version and creates a task for a new version`.

**Green:** one fanout rule.

**Refactor:** share the target-spec construction with the existing rule.

### Loop C — Handler and drain

**Red** (`apps/discovery-ingest/tests/test_harvest_worker.py`, `test_worker_drain.py`)

1. `harvest handler posts mentions in chunks and completes the task`.
2. `harvest handler fails a missing catalogue row without retry`.
3. `drain dispatches harvest_payload and counts it completed`.

**Green:** register the handler in the dispatch table next to the existing two.

**Refactor:** the dispatch table stays the only place that maps kind to handler.

## Verification

```bash
cd apps/discovery-ingest && python -m pytest tests/test_pvog_harvest.py tests/test_harvest_worker.py tests/test_worker_drain.py && ruff check . && mypy discovery_ingest
cd apps/api && python -m pytest tests/test_discovery_fanout.py
gh pr checks --watch
gh workflow run platform-maintenance.yml -f job=discovery     # re-runs PVOG ingest, which fans out harvest tasks
gh workflow run discovery-drain.yml -f kinds=harvest_payload -f max_batches=5
```

Live gate: the drain report shows `harvest_payload` tasks completed; `GET /api/v1/discovery/admin/candidates` returns candidates with mention counts. Record the run IDs and the counts.

## Out of scope

HTTP page extraction (chapters 17 and 18), GovData payloads (they carry no modules), emit (chapter 11), a UI (chapter 10).
