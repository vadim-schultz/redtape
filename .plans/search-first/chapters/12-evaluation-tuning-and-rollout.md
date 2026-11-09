---
name: "Chapter 12 — Evaluation, tuning and rollout"
overview: "Measure keyword, vector and hybrid search per language on a golden query set, tune the fusion and index parameters, calibrate the similarity ring, and enable hybrid search and the new locales in a controlled order."
id: C12
depends_on:
  - C8
  - C10
  - C11
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
    content: "Add an offline evaluation script comparing keyword, vector and hybrid with recall and MRR."
    status: pending
  - id: tuning
    content: "Tune RRF k, similarity cut-off, top-N and HNSW parameters and record the choices."
    status: pending
  - id: decisions
    content: "Decide on per-locale embeddings, similarity ring thresholds, and whether document translation should come forward."
    status: pending
  - id: rollout
    content: "Enable hybrid search and locales in the documented order with read-only live validation."
    status: pending
  - id: docs
    content: "Update operations docs and STATUS, and record the seams for the next suites."
    status: pending
---

# Chapter 12 — Evaluation, tuning and rollout

**Repo:** `redtape` (`apps/api`, `docs`, deployed apps)
**Depends on:** [Chapter 8](08-hybrid-query-path.md), [Chapter 10](10-results-presentation.md), [Chapter 11](11-ui-and-taxonomy-label-translation.md) · **Architecture:** [../00-architecture.md](../00-architecture.md) · **Rollout:** [../01-rollout.md](../01-rollout.md)

## Goal

Turn "it returns results" into evidence. Hybrid search is enabled only when it measurably beats keyword search for German queries and is acceptable for the other six languages; the numbers also settle the open questions the earlier chapters deliberately left.

## Design decisions

- **Golden set** (`apps/api/tests/fixtures/search_eval/`): at least 20 queries per locale (`de en tr ru uk pl ro`), each with the candidate keys that should appear in the top 10, drawn from real candidates in a fixed fixture database. German queries are written from candidate titles and paraphrases; other locales are translated queries (so the set measures cross-lingual recall, decision D6). Machine-translated queries are flagged as such in the fixture and reviewed by the same native speakers as chapter 11 when available.
- **Evaluation script** `apps/api/scripts/search_eval.py`: runs the three configurations (keyword leg only, vector leg only, fused) against the fixture, reports recall@10 and MRR per leg and per locale, the fused-versus-keyword delta, and p50/p95 latency. It uses the real embedder if a token is present and a recorded-vector cache otherwise, so CI can run it without spending neurons.
- **Tuning** over a small grid, recorded in the ledger: `RRF_K` ∈ {20, 60, 100}, `SEARCH_MIN_SIMILARITY` sweep, `SEARCH_TOP_N` ∈ {20, 50, 100}, HNSW `ef_search` and (if recall requires) `m`/`ef_construction`; compare against the exact scan to confirm the index does not lose recall under category filters.
- **Gate to enable `SEARCH_HYBRID_ENABLED`:** on German queries hybrid recall@10 and MRR are at least keyword's; on each other locale hybrid is not below keyword's baseline and the cross-lingual recall is recorded; p95 latency within an agreed budget (record the budget in the ledger); fallback verified.
- **Decisions this chapter settles**, each written into [../gaps-and-decisions.md](../gaps-and-decisions.md): O10 whether per-locale embeddings are needed (if some locale's recall is poor, add rows keyed by `locale`; no schema change); O7 the similarity ring's bands (compare the distribution of rescaled similarity for relevant and irrelevant hits and set band thresholds that read honestly; the confidence bands stay as they are); O5 whether weak keyword recall for non-German users justifies bringing document translation forward.
- **Rollout order**, each step recorded with evidence: migration applied and `vector` confirmed on Supabase; Render token set (operator); backfill run (chapter 4) and embed drain run until `pending_ready` is 0; `candidate_embedding` coverage and stale count recorded; evaluation passes; native-speaker reviews recorded and locales enabled one at a time with `enable_locale.py`; `SEARCH_HYBRID_ENABLED=true`; read-only live validation (table in the run ledger); watch database size, neuron ledger and Actions minutes for a week.
- **Rollback**: `SEARCH_HYBRID_ENABLED=false` returns the legacy title-match search with no deploy; disabling a locale is `enabled=false`; the schema is additive.
- **Docs**: new `docs/operations/search.md` (architecture in brief, queue and drain operations, flag, budgets, troubleshooting stale or missing embeddings, how to add a model or a locale); update `docs/operations/scheduled-jobs.md` and `docs/planning/STATUS.md`; list the seams (search-text builder, `(candidate_id, model, locale)` embeddings, subject-id dedupe, per-locale text rows, `localeMeta.ts`) in the architecture's "seams" section for the entity-resolution, document-translation and right-to-left suites.
- This chapter is chief-of-staff owned: it does not repair production data silently; it records observed state and follow-ups.

## Files

| Path | Change |
| --- | --- |
| `apps/api/tests/fixtures/search_eval/` | Fixture database builder and the golden queries. |
| `apps/api/scripts/search_eval.py` | Evaluation script. |
| `apps/api/app/config.py` | Final defaults for `RRF_K`, cut-off, top-N, `SEARCH_FUSED_TOP_K`. |
| `apps/web/src/features/documents/utils/` | Similarity band thresholds if they differ from the confidence bands. |
| `docs/operations/search.md`, `scheduled-jobs.md`, `docs/planning/STATUS.md` | Docs. |
| `.plans/search-first/run-ledger.md`, `gaps-and-decisions.md` | Evidence and settled decisions. |

## Red tests

### Happy path

- `eval · reports recall@10 and MRR per leg and locale from a fixed fixture` (deterministic with the recorded-vector cache).
- `eval · fused is not worse than keyword on the German golden set` (becomes a regression test once tuned).
- `similarity bands · classify known relevant and irrelevant hits as expected` using the tuned thresholds.
- `settings · tuned defaults load and validate`.

### Negative path

- `eval · fails loudly on a golden query whose expected candidate is missing from the fixture`.
- `eval · degrades to keyword-only numbers, clearly labelled, when no embedder or cache is available`.
- `rollout · flag off returns legacy behaviour` (re-run of chapter 8's test against the final settings).
- `live validation · the embedder token removed still returns 200 with search_mode keyword` (read-only check, recorded).

## Green

1. Build the fixture and the script; record a baseline with keyword only.
2. Run the three configurations; tune; record the numbers.
3. Settle the three decisions; update settings and band thresholds with tests.
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

Document translation, entity resolution, right-to-left support, relabelling the confidence ring, reranking models.

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
