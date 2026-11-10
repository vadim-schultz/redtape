---
name: "Chapter 18 — Evaluation, tuning and rollout"
overview: "Measure keyword, vector and hybrid search per language with and without translated text, tune the combined score and index parameters, decide which locales keep their vectors, and enable hybrid search, translations and locales in a controlled order."
id: C18
depends_on:
  - C8
  - C10
  - C11
  - C12
  - C16
  - C17
touches:
  - apps/api/tests/fixtures/search_eval/
  - apps/api/scripts/search_eval.py
  - apps/api/app/config.py
  - apps/web/src/features/documents/utils/
  - docs/operations/
  - docs/planning/STATUS.md
  - .plans/search-first/
execution: chief-of-staff
todos:
  - id: golden-set
    content: "Build a golden query set per locale from real candidates with expected results."
    status: pending
  - id: eval-script
    content: "Add an offline evaluation script comparing keyword, vector and hybrid, with and without translated rows, using recall, MRR and nDCG."
    status: pending
  - id: tuning
    content: "Tune the confidence weight, RRF k, similarity cut-off, top-N and HNSW parameters and record the choices."
    status: pending
  - id: decisions
    content: "Decide which locales keep vectors, the similarity ring thresholds, and the Polish and Ukrainian keyword quality."
    status: pending
  - id: rollout
    content: "Enable translation, hybrid search and locales in the documented order with read-only live validation."
    status: pending
  - id: docs
    content: "Update operations docs and STATUS, and record the seams for the next suites."
    status: pending
---

# Chapter 18 — Evaluation, tuning and rollout

**Repo:** `redtape` (`apps/api`, `docs`, deployed apps)
**Depends on:** [Chapter 8](08-hybrid-query-path.md), [Chapter 10](10-results-presentation.md), [Chapter 11](11-ui-and-taxonomy-label-translation.md), [Chapter 12](12-combined-ranking-score.md), [Chapter 16](16-translated-text-in-search-and-embeddings.md), [Chapter 17](17-translation-read-path-and-popover.md) · **Architecture:** [../00-architecture.md](../00-architecture.md) · **Rollout:** [../01-rollout.md](../01-rollout.md)

## Goal

Turn "it returns results" into evidence. Hybrid search is enabled only when it measurably beats keyword search for German queries and is acceptable for the other six languages, and the numbers settle the questions the earlier chapters deliberately left open.

## Design decisions

- **Golden set** (`apps/api/tests/fixtures/search_eval/`): at least 20 queries per locale (`de en tr ru uk pl ro`), each with the candidate keys expected in the top 10, drawn from a fixed fixture database that includes stored translations. German queries come from candidate titles and paraphrases; other locales are native-language queries (machine-translated ones are flagged and reviewed by the same native speakers as chapter 11 when available). The set includes cross-lingual cases (a Turkish query for German-only content) and same-language cases (a Turkish query against the Turkish translation).
- **Evaluation script** `apps/api/scripts/search_eval.py` runs these configurations: keyword only, vector only, fused, and combined, each **with and without translated rows**. It reports recall@10, MRR and nDCG@10 per configuration and locale, the mean confidence of the top 10 (to see what the confidence weight costs or buys), and p50/p95 latency. It uses the real embedder if a token is present and a recorded-vector cache otherwise, so CI runs it without spending neurons.
- **Tuning** over a small grid, recorded in the ledger: `SEARCH_CONFIDENCE_WEIGHT` ∈ {0, 0.15, 0.3, 0.5, 1}; `RRF_K` ∈ {20, 60, 100}; the similarity cut-off sweep; `SEARCH_TOP_N` ∈ {20, 50, 100}; HNSW `ef_search` and, if recall requires, `m`/`ef_construction` (compared against an exact scan, also under category filters). The chosen weight is the one with the best MRR/nDCG that does not lower top-10 mean confidence below an agreed floor; the trade-off curve is recorded.
- **Gate to enable `SEARCH_HYBRID_ENABLED`:** on German queries hybrid recall@10 and MRR are at least keyword's; on every other locale hybrid is not below its keyword baseline; translated rows improve or do not harm the non-German numbers; p95 latency is within an agreed budget (recorded); the fallback is verified.
- **Decisions this chapter settles**, each written into [../gaps-and-decisions.md](../gaps-and-decisions.md):
  - O10: which locales keep vectors. Compare per-locale vector rows against the German canonical vector alone; drop locales whose vectors do not improve results with `prune_embeddings.py`, and set `EMBEDDING_LOCALES` accordingly, recording the database space reclaimed against `DB_SOFT_LIMIT_BYTES` (invariant 11).
  - O9: Polish and Ukrainian keyword quality with the `simple` configuration; if recall is unacceptable, decide between `pg_trgm` as a third retriever or relying on the vector leg for those locales.
  - O7: the similarity ring's bands, from the distribution of rescaled similarity for relevant and irrelevant hits; confidence bands stay as they are.
  - Whether translating more than title and description is worth its cost (the chapter 13 unit).
- **Rollout order**, each step recorded with evidence: migrations applied and `vector` confirmed on Supabase; Render token set (operator); embedding backfill and embed drain until the queue is empty; translation backfill and translate drain (priority order) to coverage target; translated-locale search-text backfill and embed drain again; evaluation passes; native-speaker reviews recorded and locales enabled one at a time with `enable_locale.py`; `SEARCH_HYBRID_ENABLED=true`; read-only live validation (table in the run ledger); watch database size, the neuron ledger and Actions minutes for a week.
- **Rollback**: `SEARCH_HYBRID_ENABLED=false` returns the legacy title-match search with no deploy; `SEARCH_CONFIDENCE_WEIGHT=1` restores confidence-first ordering within the relevance gate; a locale is disabled with `enabled=false`; translations are hidden by removing `TRANSLATION_TARGET_LOCALES` entries (reads are by locale) and stored objects and index rows are additive and harmless; a different translation engine is selected with `TRANSLATION_ENGINE` and affects only new and stale units.
- **Docs**: new `docs/operations/search.md` (architecture in brief, the three queues and drains, flags and weights, budgets and the query-embedding floor, troubleshooting stale or missing embeddings and translations, how to add a model or a locale) and `docs/operations/translation-engines.md` (the `TranslationEngine` port, the registry, the conformance suite and the checklist for adding an adapter such as Azure AI Translator, O17; where translation objects live in R2 and how to inspect them); update `scheduled-jobs.md` and `docs/planning/STATUS.md`; list the seams (search-text builder, `(candidate_id, model, locale)` embeddings, per-locale text rows, translation index rows with provenance and the R2 object layout, the translation engine port, subject-id dedupe, `localeMeta.ts`) for the entity-resolution and right-to-left suites.
- This chapter is chief-of-staff owned: it does not repair production data silently; it records observed state and follow-ups.

## Files

| Path | Change |
| --- | --- |
| `apps/api/tests/fixtures/search_eval/` | Fixture database builder (with translations) and golden queries. |
| `apps/api/scripts/search_eval.py` | Evaluation script. |
| `apps/api/app/config.py` | Final defaults: weight, `RRF_K`, cut-off, top-N, `SEARCH_FUSED_TOP_K`, `EMBEDDING_LOCALES`. |
| `apps/web/src/features/documents/utils/` | Similarity band thresholds if they differ from the confidence bands. |
| `docs/operations/search.md`, `scheduled-jobs.md`, `docs/planning/STATUS.md` | Docs. |
| `.plans/search-first/run-ledger.md`, `gaps-and-decisions.md` | Evidence and settled decisions. |

## Red tests

### Happy path

- `eval · reports recall@10, MRR and nDCG@10 per configuration and locale from a fixed fixture` (deterministic with the recorded-vector cache).
- `eval · fused is not worse than keyword on the German golden set` (becomes a regression test once tuned).
- `eval · translated rows are reported separately from German-only rows`.
- `similarity bands · classify known relevant and irrelevant hits as expected` with the tuned thresholds.
- `settings · tuned defaults load and validate`.

### Negative path

- `eval · fails loudly on a golden query whose expected candidate is missing from the fixture`.
- `eval · degrades to keyword-only numbers, clearly labelled, when no embedder or cache is available`.
- `rollout · flag off returns legacy behaviour` (chapter 8's test re-run against the final settings).
- `live validation · the embedder token removed still returns 200 with search_mode keyword` (read-only check, recorded).
- `rollback · weight 1 reproduces confidence-first order within the pool`.

## Green

1. Build the fixture and the script; record a keyword-only baseline.
2. Run all configurations; tune; record the numbers.
3. Settle the decisions; update settings and band thresholds with tests.
4. Execute the rollout steps in order; fill the post-deploy validation table.

## Refactor gate

- Evaluation code is separate from product code and imports only public interfaces.
- No tuning constants duplicated between settings, tests and docs.
- Docs describe the final state, not the plan.

## Verification

```bash
cd apps/api
uv run python scripts/search_eval.py --report ../../.plans/search-first/eval-report.md
uv run pytest tests/test_search_eval.py
uv run ruff format --check . && uv run ruff check . && uv run mypy app scripts
cd ../.. && ./ci.sh
```

Post-deploy (read-only): the table at the end of [../run-ledger.md](../run-ledger.md).

## Out of scope

Entity resolution, right-to-left support, relabelling the confidence ring, reranking models, human translation review tooling.

## Git workflow

```bash
git checkout feat/plans-search-first && git pull
git checkout -b feat/search-eval-and-rollout
```

```text
test(api): describe the search evaluation harness and golden set
feat(api): add offline search evaluation and tuned defaults
docs(search): record rollout, operations and open seams
```
