# Search-first — Gaps and decisions

**Architecture:** [00-architecture.md](00-architecture.md) · **Rollout:** [01-rollout.md](01-rollout.md)

This file records decisions that implementation chapters must consume. A chapter may add a decision only when it records the reason, affected contracts, migration consequence and rollback consequence.

## Settled decisions

### D1 — Query embedding happens at request time (accepted)

An early requirement said "no embedding at request time"; the later hybrid-search specification says "generate an embedding for each user query at request time using the same model". The specification governs and the product owner accepted the consequences:

- the API host holds a Workers-AI-scoped token (this breaks the previous rule that Cloudflare tokens are never Render variables; the token must be scoped to Workers AI only and recorded as an operator action);
- each query reserves neurons through `BudgetService`, is cached in process by normalised query and model, has a hard timeout (800–1500 ms), and the public route is rate limited;
- the translate drain keeps a reserved floor in the neuron ledger so query embedding is never starved;
- any failure degrades to keyword-only search (`search_mode: "keyword"`), never to an error;
- **document** embeddings and translations still come only from background drain workers.

Rollback: `SEARCH_HYBRID_ENABLED=false` (keyword-only), or replace the `QueryEmbedder` implementation with an asynchronous one; no schema change.

### D2 — Ordering is a combined score (revised)

Results are ordered by `combined = (1 − w) · relevance + w · confidence` (chapter 12). Relevance is the normalised RRF score; confidence is the existing card confidence; `w = SEARCH_CONFIDENCE_WEIGHT`, default 0.3, tuned in chapter 18. Only candidates inside the fused relevance gate are ordered. Without a query the score equals the confidence, so browse order is unchanged. `w = 1` is confidence-first within the pool, `w = 0` is pure relevance, so the original "always highest confidence first" wish is one setting away. Confidence and similarity are shown as two separate rings. Sort controls are removed from the UI; an explicit `sort_by` from an API client still wins.

Rejected alternatives: a product of relevance and confidence (zero confidence would erase relevant results), and confidence as a third RRF leg (turns a magnitude into a rank and treats a query-independent prior as a retriever).

### D3 — The corpus is the candidate pool

Search covers `discovery_document_candidate` through `GET /api/v1/candidates`. The dormant `document` table and `catalogue_service` rows are not results. The search subject id is the candidate id.

### D4 — Fusion in one SQL statement

Both legs and the RRF join run in one statement, not two parallel sessions: sync SQLAlchemy, about 4000 rows, transactional consistency, no extra session per request. Revisit only if measured latency demands it.

### D5 — Fallback for existing multilingual data

For non-German readers the chain is requested → `en` → `de`; for German readers `de` → `en`. This applies to taxonomy and jurisdictions. Candidate titles and descriptions are not subject to this chain: their translations are served separately (D11), never substituted for the German text.

### D6 — Document text is translated and searched in the reader's language (revised)

The earlier position (non-German search relies on the multilingual vector leg alone) is replaced: document text is translated once into the six target locales (D11, D14), the translated text feeds per-locale search text, full-text vectors and embedding tasks (chapter 16), and the query path is locale-aware (chapter 8). Qwen3-Embedding's multilingual alignment still lets a query in one language find text in another; the German row is always searched too. Polish and Ukrainian have no built-in Postgres text-search configuration and use `simple` + `unaccent` (open seam O9).

### D7 — Translation engine for interface strings and documents is shared

One translation core (engine, per-locale glossary, validators, neuron metering) serves interface strings (chapter 11) and documents (chapters 13–15). The interface needs native-speaker review before a locale is enabled; documents do not (they are labelled machine translations).

### D8 — Taxonomy labels are translated with the UI strings

Category names and descriptions (a few dozen short labels shown as chips) are interface text. Translations live beside the frozen category contract (`category_contract_v1.json` stays untouched) and are merged by `seed_taxonomy`. Strike this from chapter 11 if it is not wanted; chips then remain `en`/`de` in the new locales.

### D9 — Subject id and key shape for entity resolution

Results dedupe on a single subject id. `candidate_search_text` is keyed `(candidate_id, locale)`; `candidate_embedding` is keyed `(candidate_id, model, locale)`; `candidate_translation` carries provenance; all text is built in one builder. No entity table, alias table or resolution logic is created.

### D10 — One locale list in code

`SUPPORTED_LOCALES` in `apps/api/app/shared/locale.py` is the one list that seeds `supported_locale` rows and validates JSONB locale keys; the `enabled` column decides serving. The web `localeMeta.ts` mirrors it and a test compares the two. Seed inserts new locales with `enabled=false` and never overwrites `enabled` on conflict, so an operator's flip persists.

### D11 — Translations are stored once, secondary, labelled and protected

A translation is written once per `(candidate, locale)` by a worker, stored in R2 with a thin index row in Postgres (D17), and read back from storage; nothing translates at read time. It is shown only in a pop-over beside the German original (chapter 17), always with a "machine translation" note. It is re-translated only when the German source changes (stale translations keep serving, flagged), at low priority. A `human` row is never overwritten by a machine one. Rollback: remove locales from `TRANSLATION_TARGET_LOCALES` (reads are by locale); stored objects and rows are additive and harmless.

### D12 — Per-locale vectors with storage controls (revised)

Translated text is embedded per locale (`candidate_embedding` has one row per embedded locale). The budget is the existing `DB_SOFT_LIMIT_BYTES` guard; the product owner reports about 83 MB used of 500 MB with the corpus nearly complete, so seven locales of vectors (on the order of 200 MB with HNSW) fit but are the dominant cost. Chapter 1 still decides `vector` versus `halfvec` and a reduced Matryoshka dimension from the measured projection, and must show the projected total under the soft limit with margin; `EMBEDDING_LOCALES` limits which locales get vectors; `prune_embeddings.py` reclaims a locale; chapter 18 drops locales whose vectors do not improve results (O10). Vectors stay in Postgres (pgvector needs them there); translation text does not (D17).

### D13 — The translation engine is chosen by a probe, and cost is not assumed to fit

Chapter 13's probe compares the registered engines (the Cloudflare LLM adapter and, if useful, a Cloudflare machine-translation adapter; any later adapter such as Azure Translator is probed the same way with `--engine`) on a fixed sample, reports validator pass rate, neurons per unit and the projected neurons and days for the whole corpus, and writes a sheet for native-speaker spot checks. The engine, model and pace are recorded here after that gate. If the cost does not fit the neuron budget share the options are a cheaper engine, fewer locales, or priority-limited coverage (highest confidence first).

**D13 decision (2026-11-10, product owner):** proof of concept stays on the Cloudflare `llm` adapter (`@cf/qwen/qwen3-30b-a3b-fp8`) for now; the move to Azure AI Translator is a later, separate step (O17, D16). Probe evidence so far (50 real cards per locale): about 10 to 13 neurons per card, a projected 48k to 62k neurons per locale and about 340k for six locales, which is about 36 days of the 9,500-neuron daily share. Validator pass rate 75% to 86% (glossary and number-preservation failures dominate). Consequence for the PoC: full-corpus translation in all six locales does not fit a free-tier pace, so C14/C15 must keep priority-limited coverage (highest-confidence candidates first) and the target locale list should be narrowed by the product owner before the first drain is enabled. Spot-check sheets still need native-speaker review before translations are served.

### D14 — The translation unit is the title and the card description

Only the German title and the card description (best mention excerpt) are translated: they are what a card shows and what the pop-over displays, and enough for short queries. Other mention excerpts are not translated. Chapter 18 checks whether more is worth its cost.

### D15 — Translation never starves query embedding

Request-time query embedding (D1) shares the daily neuron ledger. While the translation engine is neuron-metered (D16), the translate drain stops before the ledger's remaining neurons fall below `QUERY_EMBED_RESERVE`.

### D16 — Translation engines are adapters; Cloudflare first, Azure Translator later

Cloudflare Workers AI stays the engine for now because it is a known provider for the team. A `TranslationEngine` port, a name-keyed registry, `TRANSLATION_ENGINE` selection and a shared adapter conformance suite (chapter 13) make [Azure AI Translator](https://learn.microsoft.com/en-us/azure/ai-services/translator/how-to/create-translator-resource) or any other provider a drop-in: one adapter module, one registry line, credentials as a GitHub secret and a conformance run. The port declares the usage unit (`neurons` or `characters`) and the drain meters through a `UsageMeter` chosen by that unit, so a character-billed provider does not pretend to be neurons; the query-embedding floor (D15) applies only to neuron-metered engines. Each stored translation records `engine` and `model`; switching engines translates only new and stale units, it does not rewrite existing rows. No Azure code, credentials or probe ships in this suite (O17).

Rejected: wiring Cloudflare calls straight into the drain (a provider swap would touch the queue, the drain and the metering), and building the Azure adapter now (unneeded cost and a second credential to manage).

### D17 — Translation text lives in R2, the database keeps an index (new)

Translated title and description are stored as small JSON objects in the Cloudflare R2 bucket already used for screenshots and snapshots (10 GB free, S3 API, existing metered `ObjectStore`), keyed by candidate, locale and unit; Postgres keeps a thin `candidate_translation` index row (source hash, provenance, engine, model, object key, content hash, size). Consequences:

- translation text never counts toward the 500 MB database or the soft limit; the derived `candidate_search_text` rows and tsvectors that full-text search and embeddings need stay in Postgres and are rebuildable from R2;
- the list response carries only a `translation` summary (`locale`, `source`, `stale`), so a page makes no R2 calls; the pop-over fetches the stored text on first open through `GET /api/v1/candidates/{id}/translation` with `ETag` revalidation (a stored read, not a model call; the earlier "no request on open" rule is replaced by "no translation work on open");
- writes happen only in the API (workers hold no R2 credential); an unavailable store hands the task back without burning an attempt;
- R2 operations are metered against the existing Class A and B caps;
- the unit segment in the key is the seam for full-document translations later (O16).

Rollback: stop enqueueing (`TRANSLATION_TARGET_LOCALES` empty); objects and index rows are additive. A move back into Postgres would be a one-off copy from the objects.

## Open seams

| ID | Seam | Owner | Resolved in |
| --- | --- | --- | --- |
| O1 | Supabase `vector` availability and pgvector version (iterative HNSW scan needs 0.8 or later) | operator | C1 gate |
| O2 | Qwen3-Embedding output dimension, supported reduced dimensions and batch limit (expected 1024; unconfirmed) | C1 probe | C1, then C3 |
| O3 | Render token provisioning for query embedding (D1) | operator | before C8 enablement |
| O4 | Native-speaker reviewers for tr, ru, uk, pl, ro (interface strings, and spot checks of document translations) | operator | C11, C13 |
| O5 | Translation engine and corpus cost (D13) | C13 probe | C13 |
| O6 | The API's no-sort ordering was described two ways in the code (`public_order.py` says confidence first; `list_query.py:54-64` says completeness first). Resolved by decision: the default order is the combined score | C12, C9 | C12 defines it, C9 pins and removes the disagreeing branch |
| O7 | Similarity ring band thresholds (the confidence bands are 0.4 and 0.7; similarity is rescaled but not calibrated the same way) | C18 | C18 |
| O8 | The confidence ring is labelled "Confidence" but the product owner describes it as effectively completeness | product | follow-up, not this suite |
| O9 | No Postgres text-search configuration exists for Polish or Ukrainian (verify with `\dF`); they use `simple` + `unaccent`. Whether `pg_trgm` is needed | C16, C18 | C18 |
| O10 | Which locales keep vectors (D12) | C18 | C18 |
| O11 | Arabic and right-to-left layout | product | later suite |
| O12 | Real client IP behind the Render proxy for rate limiting (`X-Forwarded-For` handling) | C8 | C8 |
| O13 | Search storage budget. Resolved: the existing `DB_SOFT_LIMIT_BYTES` is the budget (baseline about 83 MB of 500 MB, per the product owner); C1's projection must land under it with margin | product | resolved; verified in C1 |
| O14 | The `SEARCH_CONFIDENCE_WEIGHT` default (0.3 is a starting value) | C18 | C18 |
| O15 | Human corrections of translations (an edit path that sets `source = human`) | later | not scheduled |
| O16 | Full-document translations: units beyond `card`, their size accounting against `object_store_max_bytes`, cost probe and chunking | later | separate suite; D17 keeps the key layout open |
| O17 | Adopting Azure AI Translator: resource and key (operator), GitHub secret, adapter module, character ledger and monthly cap, glossary mapping (dynamic dictionary or equivalent), data-processing and region review, probe comparison against the Cloudflare engine | later | separate small suite; D16 keeps the seam |
