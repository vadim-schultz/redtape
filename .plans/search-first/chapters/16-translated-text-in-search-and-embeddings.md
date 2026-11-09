---
name: "Chapter 16 — Translated text in search text and embedding tasks"
overview: "Turn stored translations into per-locale search text, full-text vectors and embedding tasks, so a query in Turkish, Russian, Ukrainian, Polish or Romanian is matched against text in that language, with per-locale storage controls."
id: C16
depends_on:
  - C6
  - C14
touches:
  - apps/api/app/features/search/
  - apps/api/app/features/translation/
  - apps/api/app/config.py
  - apps/api/scripts/
  - apps/api/tests/
execution: chapter-implementer
todos:
  - id: refresh-locale
    content: "Build per-locale search text and full-text vectors from stored translations through the existing builder."
    status: pending
  - id: subscribe
    content: "Subscribe the refresh to the translation-stored event so translated text is searchable immediately."
    status: pending
  - id: embedding-tasks
    content: "Enqueue embedding tasks per locale, gated by an embedding-locales setting."
    status: pending
  - id: backfill-prune
    content: "Extend the backfill to translated locales and add a prune tool to reclaim a locale's storage."
    status: pending
  - id: tests
    content: "Add per-locale text, configuration, enqueue, gating, backfill, prune and end-to-end retrieval tests."
    status: pending
---

# Chapter 16 — Translated text in search text and embedding tasks

**Repo:** `redtape` (`apps/api`)
**Depends on:** [Chapter 6](06-embedding-drain-worker.md), [Chapter 14](14-translation-queue-and-machine-api.md) · **Architecture:** [../00-architecture.md](../00-architecture.md) · **Rollout:** [../01-rollout.md](../01-rollout.md)

## Goal

Close the weakness recorded in D6: until now only German text was searchable, so non-German queries leaned on the vector leg alone. Feed the stored translations into the same search-text, full-text and embedding machinery, one locale at a time.

## Design decisions

- **Per-locale search text.** `SearchTextService.refresh_locale(candidate_id, locale)` (chapter 4's builder, locale-parameterised) builds the text of a non-`de` locale from the stored `candidate_translation` row: the translated title, then the translated description. It upserts `candidate_search_text(candidate, locale)` with `tsv_native` in the locale's configuration (`TS_CONFIG_BY_LOCALE`: `en` english, `tr` turkish, `ru` russian, `ro` romanian, `pl` and `uk` simple) and `tsv_simple`, plus the content hash. Polish and Ukrainian have no built-in Postgres configuration (open seam O9): they use `simple` with `unaccent`, so they match on exact word forms only; chapter 18 records how much that costs in recall.
- **Immediate searchability.** The refresh is subscribed to chapter 14's `on_translation_stored` event, so a translation is keyword-searchable as soon as it is stored, without waiting for the embed drain.
- **Embedding tasks per locale.** If the new hash differs from the stored embedding's `text_hash` for `(candidate, model, locale)`, enqueue an `embedding_task` for that locale (chapter 4's idempotent enqueue; chapter 5 and 6 already carry `locale` and the text through claim and complete). **Translated text is what the task carries**, as requested: the embedding of a Turkish row is computed from Turkish text.
- **Storage control.** `EMBEDDING_LOCALES` (validated subset of the supported locales; default `de` plus all translation targets) decides which locales get embedding tasks. Search-text rows and tsvectors are always written (cheap); vectors are the expensive part. This is the lever chapter 18 uses to drop a locale whose vectors do not earn their space.
- **Prune tool.** `apps/api/scripts/prune_embeddings.py --locale <code>` deletes that locale's `candidate_embedding` rows and open embedding tasks (and prints the bytes reclaimed); re-enabling a locale is a backfill. Storage per locale is measured after the first backfill and recorded (rollout invariant 11).
- **Stale and human translations.** A stale translation keeps serving search until it is re-translated (the pop-over flags it); a `human` translation is treated exactly like a machine one for search.
- **Retrieval needs no change.** Chapter 8's legs are already locale-aware: the keyword leg reads the request locale's rows with that locale's configuration plus the German row, and the vector leg reads rows of the request locale or `de` and keeps the best similarity per candidate. This chapter supplies the data and verifies the behaviour end to end.
- **Backfill.** `backfill_search.py` gains `--locale` (repeatable): builds rows from existing translations and enqueues embedding tasks; idempotent and resumable, as in chapter 4.

## Files

| Path | Change |
| --- | --- |
| `apps/api/app/features/search/service.py`, `text.py` | `refresh_locale`, locale-specific recipe from a translation. |
| `apps/api/app/features/search/enqueue.py` | Locale-aware enqueue gated by `EMBEDDING_LOCALES`. |
| `apps/api/app/features/translation/service.py` | Register the subscriber. |
| `apps/api/app/config.py` | `EMBEDDING_LOCALES`. |
| `apps/api/scripts/backfill_search.py`, `prune_embeddings.py` | Backfill and prune. |
| `apps/api/tests/test_search_locale_text.py`, `test_search_locale_enqueue.py`, `test_prune_embeddings.py`, `test_search_translated_retrieval.py` | Tests. |

## Red tests

### Happy path

- `refresh_locale · builds Turkish text from the stored translation and the turkish tsvector matches an inflected query form`.
- `translation stored · makes the translation keyword-searchable without the embed drain`.
- `enqueue · a changed locale hash enqueues one embedding task for (candidate, model, locale)`; unchanged enqueues nothing.
- `gating · a locale outside EMBEDDING_LOCALES gets search text but no embedding task`.
- `retrieval · a Turkish query finds a candidate through its Turkish row (keyword) and through its tr vector (fixture embedder), and a German-term query still finds the German row`.
- `backfill · builds rows for existing translations and is idempotent`.
- `prune · removes one locale's vectors and tasks and reports the space reclaimed`.

### Negative path

- `refresh_locale · a missing or empty translated title produces no row`.
- `refresh_locale · an unsupported locale is an error`.
- `retrieval · Polish and Ukrainian use the simple configuration and match exact word forms only` (documents the limit rather than hiding it).
- `prune · other locales and German rows are untouched`.
- `settings · EMBEDDING_LOCALES with an unsupported code fails at load`.

## Green

1. `refresh_locale` and the subscriber.
2. Locale-gated enqueue.
3. Backfill and prune; run the backfill against a fixture with translations and measure sizes.

## Refactor gate

- One builder with a locale parameter, not a second builder per language; `TS_CONFIG_BY_LOCALE` is the only locale-to-configuration map.
- The subscriber is a one-line call; no search logic in the translation feature.
- No boolean flags; typed outcomes.
- Docstrings and types; functions about 5 lines.

## Verification

```bash
cd apps/api
uv run pytest tests/test_search_locale_text.py tests/test_search_locale_enqueue.py \
  tests/test_prune_embeddings.py tests/test_search_translated_retrieval.py \
  tests/test_search_text.py tests/test_search_enqueue.py
uv run ruff format --check . && uv run ruff check . && uv run mypy app scripts
cd ../.. && ./ci.sh
```

After the translate drain has produced data (operator): run the backfill for the translated locales, run the embed drain until the queue is empty, and record per-locale row counts, embedded counts, stale counts and table/index sizes in [../run-ledger.md](../run-ledger.md).

## Out of scope

Producing translations (chapters 13 to 15), changing the query path (chapter 8), the pop-over (chapter 17), alias or entity text, tuning (chapter 18).

## Git workflow

```bash
git checkout feat/plans-search-first && git pull
git checkout -b feat/translated-search-text
```

```text
test(api): describe per-locale search text and embedding enqueue
feat(api): index translated text and queue per-locale embeddings
feat(api): add prune tool for a locale's embeddings
```
