---
name: "Chapter 4 — Search-text builder, hooks and backfill"
overview: "Build the canonical search text and content hash for each candidate, keep it current when candidates or mentions change, enqueue embedding tasks when the hash changes, and backfill existing candidates."
id: C4
depends_on:
  - C3
touches:
  - apps/api/app/features/search/
  - apps/api/app/features/discovery/
  - apps/api/scripts/
  - apps/api/tests/
execution: chapter-implementer
todos:
  - id: builder
    content: "Build deterministic canonical text, tsvectors and content hash from a candidate and its best mentions."
    status: pending
  - id: hooks
    content: "Refresh search text and enqueue embedding tasks where candidates and mentions are written."
    status: pending
  - id: enqueue
    content: "Make enqueue idempotent and hash-aware."
    status: pending
  - id: backfill
    content: "Add an idempotent, resumable backfill script."
    status: pending
  - id: tests
    content: "Add builder determinism, hook, enqueue, backfill and empty-text tests."
    status: pending
---

# Chapter 4 — Search-text builder, hooks and backfill

**Repo:** `redtape` (`apps/api`)
**Depends on:** [Chapter 3](03-search-schema.md) · **Architecture:** [../00-architecture.md](../00-architecture.md) · **Rollout:** [../01-rollout.md](../01-rollout.md)

## Goal

Make `candidate_search_text` the single, always-current source of text for keyword search and embeddings, and make every text change queue exactly the embedding work it needs. This is also the seam where aliases, keywords and translated text will plug in later.

## Design decisions

- New feature folder `apps/api/app/features/search/` with `text.py` (pure text recipe), `hashing.py`, `repository.py`, `service.py`, `enqueue.py`. Controllers are not added here.
- **Canonical text recipe `v1`** (a `RECIPE_VERSION` constant that is part of the hash input, so a recipe change re-embeds everything):
  1. the candidate title, `de` first, then `en`, then any non-blank value (reuse `pick_i18n`);
  2. then up to `K` best mention excerpts (default 4) ordered by score descending, then mention id, so the order is deterministic;
  3. each excerpt and the whole text are Unicode NFC-normalised, whitespace-collapsed and truncated (about 1500 characters in total, truncating on a word boundary).
  A candidate with no usable text gets no row and no task.
- The `de` row also stores `tsv_german = to_tsvector('german', unaccent(text))` and `tsv_simple = to_tsvector('simple', unaccent(text))`, computed in SQL on upsert. Only the `de` row is written (D6); `locale` stays in the key.
- `content_hash = sha256(RECIPE_VERSION + "\n" + text)`.
- **Hooks.** After a candidate upsert or a mention write (`features/discovery`: the candidate emit path in `candidate_emit*.py`, `mention_rows.py`, `candidate_service.py`; confirm the exact call sites by reading the write paths), call `SearchTextService.refresh(candidate_id)` in the same transaction. It is a no-op when the hash is unchanged (no tsvector rewrite, no task).
- **Enqueue.** If the new hash differs from `candidate_embedding.text_hash` for the configured model (or no embedding exists), upsert an `embedding_task`: insert pending if none open; if an open pending task exists, update its `text_hash` to the new one; if the open task is `claimed`, leave it (the stale result will be rejected and re-enqueued by chapter 5). Idempotent through the partial unique index.
- **Backfill.** `apps/api/scripts/backfill_search.py`: keyset pagination over candidates by id, batched commits, resumable by a `--after` id, prints counts (written, unchanged, skipped-empty, enqueued). It calls the same `refresh`; it holds no logic of its own.
- Writing is subject to the existing DB soft-limit (`db_headroom`): the backfill stops with a clear message when the database is at its limit, as machine writes do.
- No boolean flag parameters in service functions: separate named functions (`refresh`, `refresh_many`) instead.

## Files

| Path | Change |
| --- | --- |
| `apps/api/app/features/search/text.py` | The pure recipe: title and excerpt selection, normalisation, truncation. |
| `apps/api/app/features/search/hashing.py` | `RECIPE_VERSION`, hash function. |
| `apps/api/app/features/search/repository.py` | Upsert search text with tsvectors; read current hash; read best mentions. |
| `apps/api/app/features/search/enqueue.py` | Hash-aware idempotent task enqueue. |
| `apps/api/app/features/search/service.py` | `SearchTextService.refresh`, `refresh_many`. |
| `apps/api/app/features/discovery/candidate_emit*.py`, `mention_rows.py`, `candidate_service.py` | Call `refresh` after writes (exact sites confirmed during red). |
| `apps/api/scripts/backfill_search.py` | Resumable backfill. |
| `apps/api/tests/test_search_text.py`, `test_search_hashing.py` | Recipe and hash. |
| `apps/api/tests/test_search_service.py`, `test_search_enqueue.py` | Refresh and enqueue behaviour. |
| `apps/api/tests/test_backfill_search.py` | Backfill. |

## Red tests

### Happy path

- `search text · same inputs always give the same text and hash` asserts determinism, including mention ordering ties.
- `search text · a new mention changes the hash and enqueues one task` asserts exactly one pending task with the new hash.
- `enqueue · a second change while pending updates the task's hash, not a second task`.
- `backfill · writes rows and tasks for all candidates and is idempotent` asserts a second run changes nothing and reports `unchanged`.
- `search text · tsvectors match German stems and exact tokens` asserts `Kindergeldantrag` and `Elterngeld` queries match through the German or simple vector as designed.

### Negative path

- `search text · empty title and no excerpts produces no row and no task`.
- `search text · an unchanged recipe and text does not rewrite or enqueue`.
- `enqueue · a claimed task is not modified by a text change` asserts the open claimed task keeps its hash and a re-enqueue is left to completion handling.
- `backfill · stops cleanly at the database soft limit` asserts partial progress is reported and re-runnable.
- `search text · a recipe version bump changes every hash` (guards silent recipe drift).

## Green

1. Implement the pure recipe and hashing against the tests.
2. Add the repository upsert and the enqueue.
3. Wire the hooks.
4. Add the backfill script.

## Refactor gate

- The recipe is one pure module with no database access; the service orchestrates.
- Hooks are one-line calls; no recipe or hash logic leaks into discovery code.
- No duplicated title-picking: it reuses `pick_i18n`.
- Typed return models for refresh outcomes (`written`, `unchanged`, `skipped_empty`), not tuples or booleans.
- Each function about 5 lines, one nesting level; docstrings present.

## Verification

```bash
cd apps/api
uv run pytest tests/test_search_text.py tests/test_search_hashing.py \
  tests/test_search_service.py tests/test_search_enqueue.py tests/test_backfill_search.py
uv run ruff format --check . && uv run ruff check . && uv run mypy app scripts
cd ../.. && ./ci.sh
```

Record backfill counts and text-length percentiles (p50, p95) in [../run-ledger.md](../run-ledger.md).

## Out of scope

Claiming or storing embeddings, translated or alias text, any query path, document translation.

## Git workflow

```bash
git checkout feat/plans-search-first && git pull
git checkout -b feat/search-text-builder
```

```text
test(api): describe canonical search text and embedding enqueue
feat(api): maintain search text and enqueue embedding work
feat(api): add resumable search backfill script
```
