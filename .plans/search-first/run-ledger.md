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

## Baseline

| Check | Expected evidence | Recorded |
| --- | --- | --- |
| Candidate count and text sizes | Row count of `discovery_document_candidate`; p50/p95 canonical text and translation-unit length | pending |
| Current search behaviour | `q` title-match results for a fixed set of German queries, kept as the keyword baseline | pending |
| No-sort ordering | What `GET /api/v1/candidates` returns with no `sort_by` (open seam O6) | pending |
| Database size | `pg_database_size`, against `DB_SOFT_LIMIT_BYTES`; agreed search storage budget (O13) | pending |
| Neuron ledger | Daily neuron budget and current usage | pending |
| UI baseline | Screenshots of `/documents` (de) at desktop and mobile width | pending |
| Locale bundles | Key counts per locale file and per prefix | pending |

## Chapter evidence

### Chapter 1 — Infra and embedding probe

- Status: pending
- pgvector version (local image, CI image, Supabase): pending
- Probe: model, output dimension, supported reduced dimensions, batch limit, latency, neurons per 1k tokens: pending
- Gate decision (`EMBEDDING_DIM`, `vector` or `halfvec`) and storage estimate for seven locales versus budget: pending

### Chapter 2 — Backend locale foundation

- Status: pending
- Locale rows seeded (enabled flags): pending
- Resolution and validation tests: pending

### Chapter 3 — Search schema

- Status: pending
- Migration id and round-trip result: pending
- `alembic check` with `Vector` and HNSW: pending
- Table and index sizes at current row count: pending

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
- Probe reports per locale and engine (validator pass rate, neurons per unit, projected corpus cost, days at budget share): pending
- Native-speaker spot-check notes and engine decision (D13): pending

### Chapter 14 — Translation queue and machine API

- Status: pending
- Backfill counts (enqueued, up to date, stale): pending
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
- Query-count test (constant per page): pending
- Screenshots (trigger, open pop-over, stale note, phone width; `tr`, `ru`): pending
- Zero-request check on open: pending

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
| `Accept-Language: tr` list | `translation` present for translated candidates, `null` for `de` readers | pending |
| Queue summaries (embeddings, translations) | `pending_ready` near 0 after the drains | pending |
| Neuron ledger | Query-embedding floor intact after a translate run | pending |
| Database size | within the search storage budget and well under `DB_SOFT_LIMIT_BYTES` | pending |
| Locale served | only enabled locales appear in `GET /locales` | pending |
| `human` translations | none overwritten (query recorded) | pending |
