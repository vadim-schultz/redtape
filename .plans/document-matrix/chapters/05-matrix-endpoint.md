---
name: "Chapter 5 — Matrix endpoint"
overview: "GET /api/v1/matrix returns non-empty (domain, situation, count) cells, optionally scoped to a jurisdiction, computed by one intersection query."
todos:
  - id: query
    content: "Repository aggregate: join both association tables, group by pair"
    status: pending
  - id: service
    content: "Service maps ids to slugs; optional jurisdiction scoping"
    status: pending
  - id: http
    content: "Controller and route on the taxonomy router"
    status: pending
isProject: false
---

# Chapter 5 — Matrix endpoint

**Repo:** `redtape` (`apps/api`) · **Branch:** `feat/matrix-endpoint` · **Status:** planned

**Depends on:** [3](03-taxonomy-api.md), [4](04-documents-filter.md) · **Architecture:** [../00-architecture.md](../00-architecture.md) §3, §5 · **Rollout:** [../01-rollout.md](../01-rollout.md)

---

## Goal

`GET /api/v1/matrix` → `{"cells": [{"domain": "wohnen", "situation": "umzug", "count": 2}, …]}`.
Only non-empty cells. `?jurisdiction_id=` or `?municipality_code=` restricts counted documents, using
the same jurisdiction resolution the documents list uses.

## Design decisions

**Lives in the taxonomy feature.** The matrix is a view over taxonomy tags. The one cross-feature need
— restricting to documents in a jurisdiction — is met by **controller composition**: the controller asks
`DocumentService.document_ids_in_scope(...)` for the in-scope ids and passes them to
`TaxonomyService.get_matrix(document_ids)`. Rejected: joining `document` inside the taxonomy repository
(breaks layering), and making the taxonomy service depend on the documents service (documents already
depends on taxonomy since chapter 4, so that would be a cycle). Note the composition in the PR description.

**One aggregate query**, `GROUP BY (domain_id, life_situation_id)` over the two association tables
joined on `document_id`, optionally `WHERE document_id IN (scope)`. No N+1, no per-cell queries.

**Counts are distinct documents.** A document tagged with two domains counts once per cell it occupies,
never twice within a cell.

**Response uses slugs**, not ids, so the frontend links cells straight to
`/documents?domain=…&situation=…`. Cell ordering follows `sort_order` of domain then situation for
stable output.

**Scale seam.** If this exceeds its budget on real data, the answer is a materialized view refreshed on
tagging changes ([gaps-and-decisions.md](../gaps-and-decisions.md)); not built now.

## Files

**Add / edit**

| Path | Change |
| --- | --- |
| `apps/api/app/features/taxonomy/repository.py` | `matrix_counts(document_ids: Sequence[UUID] \| None)` |
| `apps/api/app/features/taxonomy/service.py` | `get_matrix(document_ids \| None)` maps ids to slugs |
| `apps/api/app/features/documents/service.py` | `document_ids_in_scope(jurisdiction_id, municipality_code)` |
| `apps/api/app/features/taxonomy/controller.py` | `GET /matrix` |
| `apps/api/app/schema/taxonomy/read.py` | `MatrixCell`, `MatrixResponse` |
| `apps/api/tests/test_matrix_endpoint.py` | Tests below |

## Red tests

| Test | Asserts |
| --- | --- |
| `matrix · counts documents per domain and situation pair` | Known fixture counts |
| `matrix · omits empty cells` | Missing pair absent |
| `matrix · untagged document contributes nothing` | Negative |
| `matrix · document with two domains counts once per cell` | No double counting within a cell |
| `matrix · jurisdiction scope excludes documents from other jurisdictions` | Filtered counts |
| `matrix · unknown jurisdiction returns empty cells, not an error` | Empty list, 200 |
| `matrix · slugs and order are stable` | Sorted by sort_order |

## Green

1. Repository aggregate, unscoped; test.
2. Scope parameter; test.
3. Controller composition and response models.

## Refactor gate

- Controller composes two services in ≈5 LOC; if it grows, introduce a small `MatrixQuery` handler
  object in the service layer instead.
- Repository query builder stays under ~5 LOC per method by extracting `_cell_select()` and
  `_scoped(stmt, ids)`.

## Verification

```bash
cd apps/api
python -m pytest tests/test_matrix_endpoint.py
cd ../.. && ./ci.sh
curl -s 'localhost:8000/api/v1/matrix'
```

## Out of scope

Web rendering (chapter 8), caching and materialized views.

## Git workflow

```bash
git checkout main && git pull
git checkout -b feat/matrix-endpoint
```

```text
test(api): describe matrix cell counts and jurisdiction scoping

feat(api): add matrix endpoint with per-cell document counts
```
