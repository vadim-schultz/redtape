---
name: "Chapter 17 — Extractor framework and extract_page"
overview: "A registry-based extractor interface, an extract_page task kind that reads a stored rendered snapshot and records mentions, fixture-capture tooling, and the enqueue wiring after a snapshot."
todos:
  - id: interface
    content: "Extractor protocol, PageContext, registry, charset-safe decoding"
    status: pending
  - id: handler
    content: "extract_page handler: download snapshot, extract, post mentions, complete with a note when nothing applies"
    status: pending
  - id: wiring
    content: "after_snapshot hook enqueues extract_page only when an extractor matches"
    status: pending
  - id: fixtures
    content: "artifacts download CLI and a manual fixture-capture workflow"
    status: pending
isProject: false
---

# Chapter 17 — Extractor framework and `extract_page`

**Repo:** `redtape` (`apps/discovery-ingest`, `.github/workflows`) · **Branch:** `feat/crawlers-extractor-framework` · **Status:** planned

**Depends on:** [06](06-candidate-staging-model-and-api.md), [15](15-cloudflare-render-and-snapshot.md) · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/crawlers`

## Goal

Hand-written extractors for specific hosts must plug into the queue without any host knowledge in the API. The framework ships with an empty production registry; chapter 18 adds the first real extractor. Snapshots are the **rendered DOM** Cloudflare produced in chapter 15, so extractors see single-page content that raw HTML would not contain; they still make no network calls.

## Contract

**Interface** (`discovery_ingest/extract/`):

```text
class Extractor(Protocol):
    id: str                       # e.g. "verwaltung-bund"
    version: str                  # bumped on any rule change
    def matches(self, url: str, content_type: str | None) -> bool: ...
    def extract(self, html: str, ctx: PageContext) -> list[MentionItem]: ...
```

`PageContext` carries `catalogue_service_id`, `source_url`, `final_url`, `artifact_id`. `EXTRACTORS` is a tuple in `registry.py` (empty in production here); `find_extractor(url, content_type)` returns the first match. Dispatch is a registry lookup, the same discipline as the task-kind table. `MentionItem` and the noise filter are shared with the payload harvester from chapter 7. The HTML parser dependency added in chapter 7 is reused.

**Decoding.** Bytes are decoded using the `Content-Type` charset, then a `<meta charset>` sniff, then UTF-8 with replacement, in one function with tests. NUL bytes are stripped.

**Wiring.** The `after_snapshot` hook of the `render_page` handler (chapter 15) calls `find_extractor(artifact.source_url, artifact.content_type)`. If one matches it enqueues `extract_page` through `POST /machine/tasks` with `artifact_id` and `input_key = "<extractor.id>@<extractor.version>"`, priority 100. If none matches, nothing is enqueued, so a page with no extractor creates no task. A version bump enqueues a new task for the same snapshot, which is how re-extraction works without touching completed tasks.

**Handler.** `handle_extract_page`: read the artifact through `GET /machine/artifacts/{id}/content`, decode, re-resolve the extractor (a task whose extractor has disappeared completes with note `no_extractor` rather than failing), run it, drop mentions that fail validation, `post_mentions` with `artifact_id` set, then complete. The extractor must not raise on malformed markup; an exception is caught at the handler boundary and fails the task non-retryably with the extractor id and version in the error. A task that completes with no mentions is a normal outcome.

**Result notes.** The worker completes tasks with `{note}` through the route and column added in chapter 14 (`result_note`; the admin task DTO already exposes it). This chapter uses `no_extractor` and `no_mentions`; `login_wall` and `oversize` come from chapter 15. There is no API or migration work in this chapter.

**Default kinds.** The worker's default `--kinds` gains `extract_page` (no network, so it belongs in the plain drain). `render_page` and `capture_screenshot` stay out of the defaults (chapter 15).

**Login walls.** A page that is a login wall never gets a snapshot (chapter 15), so it can never be extracted or screenshotted.

**Fixture tooling.** `python -m discovery_ingest artifacts download --id <uuid> --out <path>` (uses the machine content route) and `python -m discovery_ingest artifacts list --host <host> --limit N`. A manual workflow `discovery-fixture-capture.yml` (inputs `host`, `limit`) lists matching snapshots, downloads them, and uploads them as a GitHub Actions artifact; `gh run download` brings them to the developer. This is how chapter 18 obtains real markup in a limited local environment.

## TDD loops

### Loop A — Registry and decoding

**Red** (`apps/discovery-ingest/tests/test_extract_registry.py`)

1. `find_extractor returns the first matching extractor and none when nothing matches`.
2. `decode handles declared charset, meta charset, and falls back to utf-8 with replacement`.
3. `decode strips NUL bytes`.

**Green:** two small modules. **Refactor:** keep matching and decoding independent of the handler.

### Loop B — Handler

**Red** (`test_extract_worker.py`, a fake extractor registered in the test only)

1. `extract_page posts mentions with the artifact id and completes`.
2. `extract_page completes with note no_extractor when the extractor is gone`.
3. `extract_page completes with note no_mentions when the page yields none`.
4. `extract_page fails an extractor exception without retry and names the extractor and version`.
5. `extract_page fails retryably when the content route returns 5xx`.

**Green:** handler with named steps (fetch, decode, extract, post). **Refactor:** about five lines per step.

### Loop C — Wiring

**Red**

1. `after_snapshot enqueues extract_page with the artifact id and extractor key only when an extractor matches`.
2. `a new extractor version enqueues a second task; the same version does not`.
3. `the worker sends the note when completing with no_extractor or no_mentions`.

**Green/Refactor:** pass the hook at handler construction.

## Verification

```bash
cd apps/discovery-ingest && python -m pytest tests/test_extract_registry.py tests/test_extract_worker.py tests/test_worker_drain.py && ruff check . && mypy discovery_ingest
gh pr checks --watch
```

Live gate: none that exercises extraction (the registry is empty). Dispatch `discovery-drain.yml -f kinds=extract_page` and confirm `queue_empty`; dispatch `discovery-fixture-capture.yml -f host=verwaltung.bund.de -f limit=5` after chapter 15's live gate and confirm the downloaded files are rendered HTML (not the raw response). Record both run IDs.

## Out of scope

The first real extractor (chapter 18), link following, PDF parsing, LLM extraction. JavaScript rendering is done upstream by chapter 15 and is not repeated here.
