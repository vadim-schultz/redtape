---
name: "Chapter 8 — Hybrid query path"
overview: "Answer GET /api/v1/candidates?q= with Postgres full-text and pgvector cosine retrieval fused by Reciprocal Rank Fusion in one SQL statement, with request-time query embedding, caching, budgeting and a safe keyword-only fallback."
id: C8
depends_on:
  - C3
  - C4
  - C6
touches:
  - apps/api/app/features/search/
  - apps/api/app/features/candidates/
  - apps/api/app/schema/candidate/
  - apps/api/app/config.py
  - apps/api/tests/
  - apps/api/scripts/export_openapi.py
  - apps/web/src/test/contract/openapi.schemas.json
execution: chapter-implementer
todos:
  - id: query-embedder
    content: "Add the QueryEmbedder port with a Cloudflare implementation, cache, timeout, budget reservation and a fake."
    status: pending
  - id: keyword-leg
    content: "Implement the full-text keyword leg over the German and simple vectors."
    status: pending
  - id: vector-leg
    content: "Implement the cosine vector leg with cut-off and iterative HNSW scan."
    status: pending
  - id: fusion
    content: "Fuse the legs with RRF in one SQL statement, deduplicated by candidate id."
    status: pending
  - id: integration
    content: "Integrate into the candidates list: ordering, pagination, similarity, search_mode, fallback, rate limit."
    status: pending
  - id: tests
    content: "Add fusion, cut-off, filter, fallback, ordering, rate-limit and contract tests."
    status: pending
---

# Chapter 8 — Hybrid query path

**Repo:** `redtape` (`apps/api`, contract fixture in `apps/web`)
**Depends on:** [Chapter 3](03-search-schema.md), [Chapter 4](04-search-text-builder-and-backfill.md), [Chapter 6](06-embedding-drain-worker.md) · **Architecture:** [../00-architecture.md](../00-architecture.md) · **Rollout:** [../01-rollout.md](../01-rollout.md)

## Goal

Replace the title `ILIKE` with real search for `q`, while leaving browse (no `q`) exactly as it is. The query path must be safe on a public, unauthenticated endpoint that now spends neurons.

## Design decisions

- **Where it plugs in.** `PublicCandidateFilter.conditions` / `ordering` (`candidates/repository/public_filter.py`, `public_order.py`), `CardRelations` (`candidates/repository/cards.py`) and `CandidateService` list flow (`candidates/service.py`, `list_query.py`). The existing `q` handling in the allowlist stays (max length); the title-match condition is replaced by the fused relation when search is on.
- **`QueryEmbedder` port** (`Protocol`, in the style of `shared/object_store/port.py`) in `features/search/query_embedder.py`: `embed(query: NormalisedQuery) -> QueryVector | None`. Implementations: `CloudflareQueryEmbedder` (sync `httpx`, timeout `QUERY_EMBED_TIMEOUT_S`, instruction prefix `Instruct: <task>\nQuery: <q>`, secrets scrubbed), `UnavailableQueryEmbedder` (no token configured), and an in-memory fake for tests. An in-process LRU cache keyed by `(model, normalised query)` wraps the real one.
- **Budget.** Each uncached embed reserves a small neuron amount through `BudgetService.reserve` (`features/discovery/budgets.py`, `repository/budgets.py:reserve_ledger`); an exhausted reservation returns `None` (fallback), it does not raise.
- **Query normalisation** (`features/search/query.py`): NFC, trim, collapse whitespace, length cap, locale-aware lower-casing (Turkish dotted/dotless I) in application code, not `lower()` in SQL.
- **Keyword leg** (`keyword.py`): `websearch_to_tsquery('german', q)` against `tsv_german` and `websearch_to_tsquery('simple', unaccent(q))` against `tsv_simple`, over the `de` row regardless of request locale (D6), ranked by `ts_rank_cd`; the existing `title_matches` stays as an extra match signal so exact titles never regress. Top `SEARCH_TOP_N`.
- **Vector leg** (`vector.py`): `embedding <=> :qvec` (cosine distance), restricted to the configured model, similarity `1 − distance ≥ SEARCH_MIN_SIMILARITY`, `ORDER BY distance LIMIT SEARCH_TOP_N`, with `SET LOCAL hnsw.iterative_scan = relaxed_order` (pgvector 0.8 or later; if the server is older, the chapter records it and falls back to exact scan, which is milliseconds at this size). A setting bypasses the index for diagnosis.
- **Fusion** (`fusion.py`), one statement:

  ```sql
  WITH kw AS (SELECT candidate_id, row_number() OVER (ORDER BY score DESC, candidate_id) AS r FROM …),
       vec AS (SELECT candidate_id, row_number() OVER (ORDER BY distance, candidate_id) AS r, 1 - distance AS cos FROM …)
  SELECT COALESCE(kw.candidate_id, vec.candidate_id) AS candidate_id,
         COALESCE(1.0 / (:k + kw.r), 0) + COALESCE(1.0 / (:k + vec.r), 0) AS rrf,
         vec.cos
  FROM kw FULL OUTER JOIN vec USING (candidate_id)
  ```

  Both legs apply the same category and `complete` filters (the category expansion stays in the service). The joined relation exposes `candidate_id`, `rrf`, `cos` to `CardRelations`; confidence still comes from `CardRelations.confidence`.
- **Ordering and paging.** `ORDER BY rrf DESC, confidence DESC, id`; the fused list is capped at `SEARCH_FUSED_TOP_K`; `offset`/`limit` page within it; `total` is the fused size. An explicit `sort_by` from an API client wins over the fused order.
- **Response.** `search_mode` on the list (`browse | hybrid | keyword`) and `similarity` on each card: `(cos − cutoff) / (1 − cutoff)` clipped to 0..1, `null` when `cos` is null (keyword-only match, keyword mode, browse).
- **Fallback.** Flag off (`SEARCH_HYBRID_ENABLED=false`): the legacy title-match behaviour, `search_mode: "keyword"`. Flag on but the embedder returns `None` (timeout, error, no token, budget): keyword leg only, still the new full-text, `search_mode: "keyword"`. Never a 5xx for an embedder problem.
- **Abuse limits.** A rate limit on the list route when `q` is present (Litestar `RateLimitConfig`), keyed by the client IP taken correctly behind the Render proxy (open seam O12); `q` length cap already exists.
- Controllers stay thin; no SQL in controllers; fusion and legs are separate modules of about 100 lines or less.

## Files

| Path | Change |
| --- | --- |
| `apps/api/app/features/search/query.py` | Normalisation. |
| `apps/api/app/features/search/query_embedder.py` | Port, Cloudflare and unavailable implementations, cache, fake. |
| `apps/api/app/features/search/keyword.py`, `vector.py`, `fusion.py` | The legs and the fusion relation. |
| `apps/api/app/features/candidates/repository/public_filter.py`, `public_order.py`, `cards.py` | Use the fused relation and ordering. |
| `apps/api/app/features/candidates/service.py`, `list_query.py`, `controller.py` | Orchestration, `search_mode`, rate limit. |
| `apps/api/app/schema/candidate/read.py` | `similarity`, `search_mode`. |
| `apps/api/app/features/discovery/budget_resources.py` | Resource name for query embedding if a separate ledger resource is needed. |
| `apps/api/tests/test_search_query.py`, `test_search_fusion.py`, `test_query_embedder.py`, `test_candidates_search_api.py`, `test_search_fallback.py` | Tests. |
| `apps/api/tests/test_openapi_snapshot.py`, `apps/web/src/test/contract/openapi.schemas.json` | Regenerate after the API is stable. |

## Red tests

### Happy path

- `fusion · a candidate in both legs outranks one in a single leg` with a hand-computed RRF score for `k = 60`.
- `fusion · results are deduplicated by candidate id` and the vector-only and keyword-only matches both appear.
- `search api · a German phrase and a Turkish paraphrase both find the expected candidate` (fake embedder with fixed vectors).
- `search api · category filter applies to both legs` and a root filter includes descendants.
- `search api · no q is unchanged browse` (confidence descending, `search_mode: "browse"`).
- `search api · similarity is rescaled and null for keyword-only matches`.
- `embedder · caches a repeated query and sends the instruction prefix`.

### Negative path

- `fallback · embedder timeout, error, missing token and exhausted budget all return 200 with search_mode keyword`.
- `vector leg · results below the cut-off are dropped` (nonsense query returns no vector hits).
- `search api · flag off keeps legacy title matching`.
- `ordering · an explicit sort_by overrides the fused order`.
- `rate limit · exceeding the limit answers 429`; `q` over the length cap answers 422.
- `normalisation · Turkish İ and I are lower-cased correctly`.

## Green

1. Normalisation and the embedder port with fakes.
2. Keyword leg, vector leg, fusion against SQL tests on a seeded database.
3. Integrate into the candidates flow and schema; regenerate OpenAPI and the web contract.
4. Capture `EXPLAIN (ANALYZE, BUFFERS)` for both legs on a 4000-row fixture.

## Refactor gate

- The fusion statement lives in one place; the legs do not know about each other.
- No boolean parameter selects hybrid versus keyword inside a repository; mode is a typed value decided in the service.
- `PublicCandidateFilter` gains a narrow search input, not another set of optional fields spread through query code.
- Candidate list and count share the same relation (no count drift).
- All functions about 5 lines, docstrings, no `Any`; confidence logic untouched.

## Verification

```bash
cd apps/api
uv run pytest tests/test_search_query.py tests/test_search_fusion.py tests/test_query_embedder.py \
  tests/test_candidates_search_api.py tests/test_search_fallback.py \
  tests/test_candidates_public_api.py tests/test_candidates_browse.py tests/test_openapi_snapshot.py
uv run ruff format --check . && uv run ruff check . && uv run mypy app scripts
cd ../web && npm test -- src/test/contract
cd ../.. && ./ci.sh
```

Record `EXPLAIN` output (HNSW and GIN used), p50/p95 latency for hybrid and fallback, and the regenerated snapshots in [../run-ledger.md](../run-ledger.md).

## Out of scope

Web changes (chapters 9 and 10), tuning of `k`, cut-off and HNSW parameters (chapter 12), per-locale vectors, translated text, enabling the flag in production.

## Git workflow

```bash
git checkout feat/plans-search-first && git pull
git checkout -b feat/hybrid-search
```

```text
test(api): describe hybrid retrieval, fusion and fallback
feat(api): add query embedder with cache, budget and fallback
feat(api): fuse keyword and vector search with RRF
```
