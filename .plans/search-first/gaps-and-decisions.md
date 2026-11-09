# Search-first — Gaps and decisions

**Architecture:** [00-architecture.md](00-architecture.md) · **Rollout:** [01-rollout.md](01-rollout.md)

This file records decisions that implementation chapters must consume. A chapter may add a decision only when it records the reason, affected contracts, migration consequence and rollback consequence.

## Settled decisions

### D1 — Query embedding happens at request time

An early requirement said "no embedding at request time"; the later hybrid-search specification says "generate an embedding for each user query at request time using the same model". The specification governs. Consequences:

- the API host holds a Workers-AI-scoped token (this breaks the previous rule that Cloudflare tokens are never Render variables; the token must be scoped to Workers AI only and recorded as an operator action);
- each query reserves neurons through `BudgetService`, is cached in process by normalised query and model, has a hard timeout (800–1500 ms), and the public route is rate limited;
- any failure degrades to keyword-only search (`search_mode: "keyword"`), never to an error;
- **document** embeddings still come only from background drain workers.

Rollback: set `SEARCH_HYBRID_ENABLED=false` (keyword-only), or replace the `QueryEmbedder` implementation with an asynchronous one; no schema change.

### D2 — Ordering

With `q`: fused RRF rank descending, ties by confidence descending. Without `q`: confidence descending, always. The sort controls are removed from the UI. Confidence and similarity are shown as two separate rings. This departs from "always confidence first" while searching, because the fused rank is the ranking the specification asks for. An explicit `sort_by` from an API client still wins.

### D3 — The corpus is the candidate pool

Search covers `discovery_document_candidate` through `GET /api/v1/candidates`. The dormant `document` table and `catalogue_service` rows are not results. The search subject id is the candidate id.

### D4 — Fusion in one SQL statement

Both legs and the RRF join run in one statement, not two parallel sessions: sync SQLAlchemy, about 4000 rows, transactional consistency, no extra session per request. Revisit only if measured latency demands it.

### D5 — Fallback for existing multilingual data

For non-German readers the chain is requested → `en` → `de`; for German readers `de` → `en`. This applies to taxonomy and jurisdictions (the only multilingual data today). Candidate content is German-only until a translation suite exists.

### D6 — Non-German search relies on the vector leg

Qwen3-Embedding is multilingual, so a Turkish, Russian, Ukrainian, Polish or Romanian query lands near German text without translation. The keyword leg can only match German terms, proper nouns and identifiers, so it always uses the `german` and `simple` configurations over the `de` row, never the user's language configuration. Expect weak keyword recall for those users; chapter 12 measures it per locale and records whether it justifies bringing document translation forward. One canonical embedding per candidate; `locale` stays in the primary key for later per-locale vectors.

### D7 — UI strings are translated by an LLM on Workers AI, then reviewed

The translation command uses the existing `LlmClient`, `NeuronMeter` and ledger, a glossary, JSON-schema output and validators (placeholders, plural forms, markup, length). A locale stays `enabled=false` until the review manifest records a native-speaker review and coverage is 100%. A dedicated machine-translation model stays a fallback to evaluate.

### D8 — Taxonomy labels are translated with the UI strings

Category names and descriptions (a few dozen short labels shown as chips) are treated as interface text, not documents. Translations live beside the frozen category contract (`category_contract_v1.json` stays untouched) and are merged by `seed_taxonomy`. Strike this from chapter 11 if it is not wanted; chips then remain `en`/`de` in the new locales.

### D9 — Subject id and key shape for entity resolution

Results dedupe on a single subject id. `candidate_search_text` is keyed `(candidate_id, locale)`; `candidate_embedding` is keyed `(candidate_id, model, locale)`; all text is built in one builder. No entity table, alias table or resolution logic is created.

### D10 — One locale list in code

`SUPPORTED_LOCALES` in `apps/api/app/shared/locale.py` is the one list that seeds `supported_locale` rows and validates JSONB locale keys; the `enabled` column decides serving. The web `localeMeta.ts` mirrors it and a test compares the two. Seed inserts new locales with `enabled=false` and never overwrites `enabled` on conflict, so an operator's flip persists.

## Open seams

| ID | Seam | Owner | Resolved in |
| --- | --- | --- | --- |
| O1 | Supabase `vector` availability and pgvector version (iterative HNSW scan needs 0.8 or later) | operator | C1 gate |
| O2 | Qwen3-Embedding output dimension and batch limit (expected 1024; unconfirmed) | C1 probe | C1, then C3 |
| O3 | Render token provisioning for query embedding (D1) | operator | before C8 enablement |
| O4 | Native-speaker reviewers for tr, ru, uk, pl, ro | operator | C11 |
| O5 | Document translation, provenance and "machine translated" labelling | next suite | after C12 |
| O6 | The API's no-sort ordering is described two ways in the code (`public_order.py` says confidence first; `list_query.py:54-64` says completeness first); the UI currently sends an explicit sort | C9 | C9 characterises it and pins confidence descending |
| O7 | Similarity ring band thresholds (the confidence bands are 0.4 and 0.7; similarity is rescaled but not calibrated the same way) | C12 | C12 |
| O8 | The confidence ring is labelled "Confidence" but the product owner describes it as effectively completeness | product | follow-up, not this suite |
| O9 | No Postgres text-search configuration exists for Polish or Ukrainian (verify with `\dF`); only matters once content exists in those languages | next suite | after O5 |
| O10 | Whether per-locale embeddings are needed | C12 | C12 |
| O11 | Arabic and right-to-left layout | product | later suite |
| O12 | Real client IP behind the Render proxy for rate limiting (`X-Forwarded-For` handling) | C8 | C8 |
