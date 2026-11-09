# Search-first — Run ledger

**Suite:** [00-architecture.md](00-architecture.md) · [01-rollout.md](01-rollout.md)
**Purpose:** Record implementation and post-deploy evidence. This file is a ledger template; no production checks are implied by its creation.

## Orchestration

- Loop branch: `feat/plans-search-first`
- Release branch: `main`
- Local CI: `./ci.sh`
- Implementation order: `C1 → C2 → C3 → C7 → C4 → C9 → C5 → C6 → C8 → C10 → C11`
- Integration order: `C1 → C2 → C3 → C7 → C4 → C9 → C5 → C6 → C8 → C10 → C11 → C12`
- Parallel batches: `B1=C1,C2`, `B2=C3,C7`, `B3=C4,C9`, `B4=C5`, `B5=C6`, `B6=C8`, `B7=C10`, `B8=C11`, `B9=C12`
- Environment: web installs use `npm ci` against the corporate npm mirror; `./ci.sh` runs `uv run`, which may rewrite `apps/discovery-ingest/uv.lock` to the corporate PyPI mirror. Revert that file before committing (except the intentional C1 dependency change in `apps/api`).
- Status: planned; no chapter started.
- Conflicts/failures: none.
- Current work: none.

## Baseline

| Check | Expected evidence | Recorded |
| --- | --- | --- |
| Candidate count and text sizes | Row count of `discovery_document_candidate`; p50/p95 canonical text length | pending |
| Current search behaviour | `q` title-match results for a fixed set of German queries, kept as the keyword baseline | pending |
| No-sort ordering | What `GET /api/v1/candidates` returns with no `sort_by` (open seam O6) | pending |
| Database size | `pg_database_size`, against `DB_SOFT_LIMIT_BYTES` | pending |
| Neuron ledger | Daily neuron budget and current usage | pending |
| UI baseline | Screenshots of `/documents` (de) at desktop and mobile width | pending |
| Locale bundles | Key counts per locale file and per prefix | pending |

## Chapter evidence

### Chapter 1 — Infra and embedding probe

- Status: pending
- pgvector version (local image, CI image, Supabase): pending
- Probe: model, output dimension, batch limit, latency, neurons per 1k tokens: pending
- Gate decision (`EMBEDDING_DIM`): pending

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
- Pinned no-sort ordering (O6 resolution): pending
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

### Chapter 12 — Evaluation, tuning and rollout

- Status: pending
- Golden set size per locale: pending
- Recall@10 and MRR per leg and fused, per locale: pending
- Chosen `RRF_K`, similarity cut-off, top-N, HNSW parameters: pending
- Decision on per-locale embeddings (O10) and on bringing document translation forward (O5): pending
- Similarity ring band thresholds (O7): pending

## Post-deploy validation

| Check | Expected | Recorded |
| --- | --- | --- |
| `GET /api/v1/candidates?q=…` with the flag off | `search_mode: "keyword"`, legacy behaviour | pending |
| Same with the flag on | `search_mode: "hybrid"`, similarity present | pending |
| Query with the embedder token removed | `search_mode: "keyword"`, HTTP 200 | pending |
| Queue summary | `pending_ready` near 0 after the drain | pending |
| Database size | well under `DB_SOFT_LIMIT_BYTES` | pending |
| Locale served | only enabled locales appear in `GET /locales` | pending |
