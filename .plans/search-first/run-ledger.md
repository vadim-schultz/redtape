# Search-first — Run ledger

**Suite:** [00-architecture.md](00-architecture.md) · [01-rollout.md](01-rollout.md)
**Purpose:** Record implementation and post-deploy evidence. This file is a ledger template; no production checks are implied by its creation.

## Orchestration

- Loop branch: `feat/plans-search-first`
- Release branch: `main`
- Local CI: `./ci.sh`
- Implementation and integration order: `C1 → C2 → C3 → C7 → C4 → C13 → C5 → C6 → C14 → C8 → C15 → C16 → C12 → C9 → C10 → C17 → C11 → C18`
- Parallel batches: `B1=C1,C2`, `B2=C3,C7`, `B3=C4,C13`, `B4=C5`, `B5=C6,C14`, `B6=C8,C15,C16`, `B7=C12`, `B8=C9`, `B9=C10`, `B10=C17`, `B11=C11`, `B12=C18`
- Environment: web installs use `npm ci` against the corporate npm mirror; `./ci.sh` runs `uv run`, which may rewrite `apps/discovery-ingest/uv.lock` to the corporate PyPI mirror. Revert that file before committing (except the intentional C1 dependency change in `apps/api`).
- Status: planned; no chapter started.
- Conflicts/failures: none.
- Current work: none.

## Merge ledger (chief of staff)

**Loop branch:** `feat/plans-search-first`
**Release branch:** `main`
**Release MR/PR:** _(filled when opened)_
**Execution order:** the rollout's "Integration order" (C1 → C2 → C3 → C7 → C4 → C13 → C5 → C6 → C14 → C8 → C15 → C16 → C12 → C9 → C10 → C17 → C11 → C18). C18 is `chief-of-staff` execution (operator actions, live validation) and is not run by an implementer.

Chapter MRs merge into the loop branch only. The chapter-implementer **does not** edit this file; chapter evidence above is filled by the chief of staff from implementer returns.

| chapter | branch | mr/pr | local ci | remote ci | merged | blocker |
| --- | --- | --- | --- | --- | --- | --- |
| 01-infra-and-embedding-probe | `feat/search-infra-and-probe` | [#372](https://github.com/vadim-schultz/redtape/pull/372) (+ [#373](https://github.com/vadim-schultz/redtape/pull/373) typer pin) | pass | pass | yes (64ef112) | none |
| 02-backend-locale-foundation | `feat/search-backend-locales` | [#374](https://github.com/vadim-schultz/redtape/pull/374) | pass | pass | yes (5ccabc4) | none |
| 03-search-schema | `feat/search-schema` | [#375](https://github.com/vadim-schultz/redtape/pull/375) | pass | pass | yes (edfffd9) | none |

## Baseline

| Check | Expected evidence | Recorded |
| --- | --- | --- |
| Candidate count and text sizes | Row count of `discovery_document_candidate`; p50/p95 canonical text and translation-unit length | pending |
| Current search behaviour | `q` title-match results for a fixed set of German queries, kept as the keyword baseline | pending |
| No-sort ordering | What `GET /api/v1/candidates` returns with no `sort_by` (open seam O6) | pending |
| Database size | `pg_database_size` against `DB_SOFT_LIMIT_BYTES` (product owner's figure: about 83 MB of 500 MB; record the measured value) | pending |
| Object storage | Bucket bytes and objects today (screenshots, snapshots), R2 Class A and B usage this month against the caps | pending |
| Neuron ledger | Daily neuron budget and current usage | pending |
| UI baseline | Screenshots of `/documents` (de) at desktop and mobile width | pending |
| Locale bundles | Key counts per locale file and per prefix | pending |

## Chapter evidence

### Chapter 1 — Infra and embedding probe

- Status: merged into loop branch (#372); refactor gate: Long Function in `CloudflareEmbeddingClient.embed` -> Extract Function; data-design gate: not applicable
- pgvector version (local image, CI image, Supabase): local/CI `pgvector/pgvector:pg16`, vector 0.8.7 on PG 16.15; Supabase not checked (operator action)
- Probe (2026-11-10, `embed probe` from PR #372, live Workers AI): model `@cf/qwen/qwen3-embedding-0.6b`, dimension 1024; reduced dimensions 768/512/256/128 NOT honoured (`dimensions` returned 1024); batches 1–256 all accepted (no rejection up to 256); single-text latency 359 ms (batch 256: 3.6 s); 7,931 tokens, 8.52 neurons, 1.07 neurons per 1k tokens. Request/response shape assumed by the client confirmed.
- pgvector on Supabase (operator, 2026-11-10): `vector` 0.8.0 available, not yet installed (C3 migration runs `CREATE EXTENSION`); `unaccent` 1.1 available, not installed.
- Measured baseline: `pg_database_size` 58,707,091 bytes (about 58.7 MB, not the 83 MB estimate); 4,713 candidates.
- Gate decision: `EMBEDDING_DIM=1024`, column type `halfvec(1024)` (pgvector 0.8 supports halfvec and iterative HNSW scans); no reduced dimension (the model ignores `dimensions`). Projection for 4,713 x 7 = 32,991 rows: halfvec(1024) table+HNSW about 175 MB, plus search text/tsvectors about 41 MB (estimate, C3 measures), plus 58.7 MB baseline = about 275 MB versus `DB_SOFT_LIMIT_BYTES` 475 MB (about 200 MB margin). `vector(1024)` would be about 440 MB total (thin margin), so it is not chosen.

### Chapter 2 — Backend locale foundation

- Status: merged into loop branch (#374); refactor gate: smells found -> refactorings applied (`pick_i18n` loops extracted, seed split); data-design gate: reviewed, no `apply` findings (observed: stored `completeness_pct` now dead; accepted-risk: uncached `/locales` count)
- Locale rows seeded (enabled flags): 7 rows; de, en enabled; tr, ru, uk, pl, ro disabled. `ui_translation`: de 367 keys, en 367 keys; computed completeness de/en 100.0, others 0.0
- Resolution and validation tests: added (fallback chain, seed idempotence preserving `enabled`, locale-key validation rejects `fr`); non-German readers now fall back `en` before `de`

### Chapter 3 — Search schema

- Status: merged into loop branch (#375); refactor gate: smells found -> refactorings applied (`_candidate_id()` extracted in migration; test helper); data-design gate: no `apply` findings (accepted-risk: no index on `embedding_task.candidate_id`, redundant `dim`; observed for C4/C5: use matching `index_where` on enqueue upsert, retry cap/backoff and claim fencing)
- Migration id and round-trip result: `20261110_search_schema` (parent `20261105_retire_legacy_taxonomy`); `scripts/check_migrations.sh` passes (single head, upgrade, downgrade -1, upgrade, `alembic check`). Migration creates `vector` and `unaccent` extensions; on Supabase both are available but not installed, so the deploy role needs permission to create extensions, or an operator enables them first.
- `alembic check` with `Vector` and HNSW: passes with no hook; detects `halfvec(512)` vs `halfvec(1024)` drift and a dropped GIN index
- Table and index sizes (scratch DB, synthetic rows, `halfvec(1024)`, HNSW m=16 ef_construction=64): de only, 4,713 rows: embedding 27.4 MB (HNSW 12 MB), search text 26.2 MB (each GIN 5.1 MB), tasks 1.2 MB. Seven locales, 32,991 rows: embedding 191 MB (HNSW 86 MB), search text 133 MB (synthetic 60-word text, pessimistic), tasks 8.1 MB. Worst case 58.7 + 332 = about 391 MB vs 475 MB soft limit (about 84 MB margin); the C1 estimate of about 275 MB assumed shorter text. Re-check with real text lengths (C4 backfill, C16, C18). Levers: `EMBEDDING_LOCALES`, prune tool. HNSW `REINDEX` not measured.

### Chapter 4 — Search-text builder, hooks and backfill

- Status: pending
- Backfill counts (rows written, tasks enqueued, skipped for empty text): pending
- Recipe version and hash stability check: pending

### Chapter 5 — Embedding task machine API

- Status: pending
- Contract fixture regenerated: pending
- Claim concurrency test (two claimers, no overlap): pending
- Generic leased queue extraction; existing discovery queue tests unchanged: pending

### Chapter 6 — Embedding drain worker

- Status: pending
- First drain report (claimed, completed, stale, neurons): pending
- Cadence chosen and Actions minutes per run: pending
- Backfill completion (embedded / total, stale count): pending

### Chapter 7 — Web locale foundation

- Status: pending
- Bundle size before and after lazy loading: pending
- Parity test coverage (keys, placeholders, plurals): pending

### Chapter 8 — Hybrid query path

- Status: pending
- `EXPLAIN` for vector leg (HNSW used) and keyword leg (GIN used): pending
- Latency p50/p95, hybrid and fallback: pending
- Fallback behaviour under timeout, error and exhausted budget: pending
- OpenAPI snapshot and web contract fixture regenerated: pending

### Chapter 9 — Centred search and sort removal

- Status: pending
- Pinned default ordering (O6 resolution, combined score): pending
- Screenshots after (de, ru; desktop and mobile): pending

### Chapter 10 — Results presentation

- Status: pending
- `ScoreRing` shared by confidence and similarity; screenshots: pending
- `keyword` mode hint and omitted similarity ring: pending

### Chapter 11 — UI and taxonomy-label translation

- Status: pending
- Strings translated per locale; validator rejections and repairs: pending
- Neurons spent: pending
- Review manifest status per locale (machine / reviewed, reviewer, date): pending

### Chapter 12 — Combined ranking score

- Status: pending
- Default weight and the SQL/Python agreement result: pending
- Browse regression result: pending
- OpenAPI snapshot and contract fixture regenerated: pending

### Chapter 13 — Translation schema and core

- Status: pending
- Migration id and round-trip result: pending
- Engine port, registry and conformance suite: adapters passing (`llm`, optional `mt`): pending
- Translation object store round trip (write, read, content hash, key layout): pending
- Probe reports per locale and engine (validator pass rate, usage per unit, projected corpus cost, days at budget share): pending
- Native-speaker spot-check notes and engine decision (D13): pending

### Chapter 14 — Translation queue and machine API

- Status: pending
- Backfill counts (enqueued, up to date, stale): pending
- Object-store outage test (task handed back, attempt not burned): pending
- Priority ordering evidence (high-confidence first, all locales together): pending
- Contract fixture regenerated: pending

### Chapter 15 — Translation drain worker

- Status: pending
- First drain report (claimed, stored, stale, rejected, neurons): pending
- Validator failure and repair rate: pending
- Cadence, query-embedding floor and Actions minutes per run: pending
- Translated / total per locale: pending

### Chapter 16 — Translated text in search text and embedding tasks

- Status: pending
- Per-locale search-text rows, embedded counts and stale counts: pending
- Table and index sizes per locale versus budget: pending
- Polish and Ukrainian keyword behaviour (O9): pending

### Chapter 17 — Translation read path and pop-over

- Status: pending
- Query-count test (constant per page) and zero object-store calls on a list page: pending
- R2 reads for one pop-over open, and `304` on revalidation without a store read: pending
- Screenshots (trigger, open pop-over, stale note, phone width; `tr`, `ru`): pending
- Pop-over network check (one stored-text request on first open, none on second open, no model call): pending

### Chapter 18 — Evaluation, tuning and rollout

- Status: pending
- Golden set size per locale: pending
- Recall@10, MRR and nDCG@10 per configuration and locale, with and without translated rows: pending
- Chosen `SEARCH_CONFIDENCE_WEIGHT`, `RRF_K`, similarity cut-off, top-N, HNSW parameters: pending
- Locales that keep vectors and storage reclaimed (O10): pending
- Similarity ring band thresholds (O7): pending

## Post-deploy validation

| Check | Expected | Recorded |
| --- | --- | --- |
| `GET /api/v1/candidates?q=…` with the flag off | `search_mode: "keyword"`, legacy behaviour | pending |
| Same with the flag on | `search_mode: "hybrid"`, similarity and score present | pending |
| Query with the embedder token removed | `search_mode: "keyword"`, HTTP 200 | pending |
| `Accept-Language: tr` list | `translation` summary present for translated candidates, `null` for `de` readers | pending |
| `GET /api/v1/candidates/{id}/translation?locale=tr` | stored text with `ETag`; `304` on revalidation | pending |
| Queue summaries (embeddings, translations) | `pending_ready` near 0 after the drains | pending |
| Neuron ledger | Query-embedding floor intact after a translate run | pending |
| Database size | under `DB_SOFT_LIMIT_BYTES` with margin (baseline about 83 MB) | pending |
| Object storage | translation objects and bytes; R2 Class A and B usage under the caps | pending |
| Locale served | only enabled locales appear in `GET /locales` | pending |
| `human` translations | none overwritten (query recorded) | pending |
