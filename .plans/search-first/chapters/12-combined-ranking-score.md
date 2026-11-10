---
name: "Chapter 12 — Combined ranking score"
overview: "Order results by one combined score that blends query relevance with evidence confidence, with a tunable weight, a relevance gate, deterministic paging and confidence-only ordering when browsing."
id: C12
depends_on:
  - C8
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
  - id: scoring-module
    content: "Add a single scoring module: a pure reference function and the matching SQL expression."
    status: pending
  - id: ordering
    content: "Order by the combined score with deterministic tie-breaks and make it the default order."
    status: pending
  - id: response
    content: "Expose the combined score on each card and add a combined sort key."
    status: pending
  - id: settings
    content: "Add the validated confidence weight setting."
    status: pending
  - id: tests
    content: "Add formula, weight-extreme, gate, paging, browse-regression and SQL-versus-Python agreement tests."
    status: pending
---

# Chapter 12 — Combined ranking score

**Repo:** `redtape` (`apps/api`, contract fixture in `apps/web`)
**Depends on:** [Chapter 8](08-hybrid-query-path.md) · **Architecture:** [../00-architecture.md](../00-architecture.md) · **Rollout:** [../01-rollout.md](../01-rollout.md)

## Goal

Replace the interim "relevance first, confidence as tie-break" order with the decided ranking (D2): one combined score that rewards results that both match the query and are well supported by evidence, with the balance controlled by one setting.

## Design decisions

- **Formula.** `combined = (1 − w) · relevance + w · confidence`, with `relevance` and `confidence` both in 0..1 and `w = SEARCH_CONFIDENCE_WEIGHT` (validated 0..1; default 0.3 as a starting value, tuned in chapter 18).
  - `relevance` is chapter 8's normalised fused score: `rrf / (legs / (k + 1))`, where `legs` is 2 in hybrid mode and 1 in keyword-only mode, so the best possible match scores 1.0 in either mode.
  - `confidence` is the existing `CardRelations.confidence` (0 when a candidate has no score).
- **Why a linear blend.** It is transparent and tunable with one number; `w = 1` reproduces "confidence first" and `w = 0` is pure relevance, so the setting spans the earlier requirement and the retrieval-only ranking. Rejected: a product (`relevance × confidence`) would erase relevant results with zero confidence, and many candidates have no score; a third RRF leg for confidence would turn a magnitude into a rank and treat a query-independent quality prior like a query-dependent retriever.
- **Relevance gate.** Only candidates in chapter 8's fused pool (above the similarity cut-off, within `SEARCH_FUSED_TOP_K`) are ordered. A high-confidence but irrelevant candidate never enters the list; the weight only reorders within the pool.
- **Browse.** Without `q` there is no relevance term, so the score is the confidence and the order is exactly today's browse order (confidence, then the existing completeness, mention and id tie-breaks). Browse behaviour must not change; a regression test pins it.
- **Tie-breaks.** `combined DESC, relevance DESC, confidence DESC, candidate id` in search mode, so paging is deterministic (no duplicates or gaps across pages).
- **Sort contract.** `PublicSortKey` gains `combined`, which is the default when no `sort_by` is given (this closes open seam O6: the default is now defined once, here). Explicit `sort_by` values (`confidence`, `completeness`, `mentions`, `title`, `created_at`) keep working for API clients and override the default.
- **Response.** Each card gains `score` (the combined score, 0..1, four decimals; equals the confidence in browse mode). The web does not display it; it exists for transparency, evaluation and debugging.
- **One module.** `features/search/scoring.py` holds a pure Python reference `combined_score(relevance, confidence, weight)` and `combined_expression(relevance_column, confidence_column, weight)` for SQL; a test cross-checks the two on a grid. `public_order.py` and `cards.py` only call it; no scoring arithmetic anywhere else.
- The setting is server-side configuration; clients cannot change the weight.

## Files

| Path | Change |
| --- | --- |
| `apps/api/app/features/search/scoring.py` | Reference function and SQL expression. |
| `apps/api/app/features/candidates/repository/public_order.py` | `combined` ordering and default; tie-breaks. |
| `apps/api/app/features/candidates/repository/cards.py`, `public_filter.py` | Expose relevance and score columns from the fused relation. |
| `apps/api/app/features/candidates/list_query.py`, `service.py` | `combined` sort key; default selection; remove the disagreeing no-sort branch. |
| `apps/api/app/schema/candidate/read.py` | `score` on cards. |
| `apps/api/app/config.py` | `SEARCH_CONFIDENCE_WEIGHT`. |
| `apps/api/tests/test_search_scoring.py` | Formula and SQL/Python agreement. |
| `apps/api/tests/test_candidates_ranking_api.py` | Ordering, gate, paging, browse regression, overrides. |
| `apps/api/tests/test_openapi_snapshot.py`, `apps/web/src/test/contract/openapi.schemas.json` | Regenerate. |

## Red tests

### Happy path

- `scoring · combines relevance and confidence with the weight` for hand-computed points, in hybrid and keyword-only normalisation.
- `ranking · a slightly less relevant but much better supported candidate can outrank a barely better match` at the default weight.
- `ranking · weight 1 orders by confidence within the pool and weight 0 by relevance`.
- `ranking · browse order is unchanged` (existing browse tests stay green).
- `ranking · pages are stable` asserts no duplicate or missing candidate across consecutive pages.
- `scoring · SQL expression and Python reference agree` over a grid of relevance, confidence and weight.
- `api · each card carries score; no sort_by yields the combined order; explicit sort_by overrides it`.

### Negative path

- `ranking · an irrelevant high-confidence candidate never appears` (outside the relevance gate).
- `ranking · missing confidence counts as 0 and never errors`.
- `settings · weight outside 0..1 fails at load`.
- `ranking · keyword fallback mode still orders by the combined score` with single-leg normalisation.
- `ranking · equal scores fall back to the deterministic tie-break`.

## Green

1. Scoring module with both implementations.
2. Wire the expression into ordering and the default; add `score` and the sort key.
3. Regenerate OpenAPI and the contract fixture.

## Refactor gate

- Scoring arithmetic exists in exactly one module; ordering code has no formulas.
- No boolean parameter chooses a ranking mode; the mode is data (`browse`, `hybrid`, `keyword`) decided in the service.
- The old no-sort branch that returned a different order is deleted, not bypassed.
- Types and docstrings on new functions; no `Any`.

## Verification

```bash
cd apps/api
uv run pytest tests/test_search_scoring.py tests/test_candidates_ranking_api.py \
  tests/test_candidates_public_api.py tests/test_candidates_browse.py tests/test_openapi_snapshot.py
uv run ruff format --check . && uv run ruff check . && uv run mypy app scripts
cd ../web && npm test -- src/test/contract
cd ../.. && ./ci.sh
```

Record the regenerated snapshots and the default weight in [../run-ledger.md](../run-ledger.md).

## Out of scope

Tuning `w` (chapter 18), showing the score in the UI, learned ranking, per-user personalisation.

## Git workflow

```bash
git checkout feat/plans-search-first && git pull
git checkout -b feat/combined-ranking
```

```text
test(api): describe the combined relevance and confidence score
feat(api): order candidates by a tunable combined score
```
