---
name: "Chapter 5 — Matrix endpoint"
overview: "GET /api/v1/matrix returns non-empty (domain, situation, count) cells plus distinct-document totals per situation row and per domain column and a grand total, optionally scoped to a jurisdiction."
todos:
  - id: query
    content: "Repository aggregates: cell counts by pair, distinct-document totals per axis term"
    status: done
  - id: service
    content: "Service maps ids to codes; assembles cells, axis totals and grand total; optional jurisdiction scoping"
    status: done
  - id: http
    content: "Controller and route on the taxonomy router"
    status: done
isProject: false
---

# Chapter 5 — Matrix endpoint

**Repo:** `redtape` (`apps/api`) · **Branch:** `feat/matrix-endpoint` · **Status:** done

**Depends on:** [3](03-taxonomy-api.md), [4](04-documents-filter.md) · **Architecture:** [../00-architecture.md](../00-architecture.md) §3, §5 · **Rollout:** [../01-rollout.md](../01-rollout.md)

---

## Goal

`GET /api/v1/matrix` → `{total, cells, situations, domains}` as specified in
[architecture §5.1](../00-architecture.md): non-empty cells, plus `situations[]` and `domains[]` with each
term's **distinct document count** (what a user gets by selecting that whole row or column), plus the
grand `total`. Terms with zero documents in scope are omitted from `situations` / `domains`.

Scoping: `?jurisdiction_id=` or `?municipality_code=` restricts counted documents, using
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

**Axis totals are computed, not summed.** `situations[].count` is `COUNT(DISTINCT document_id)` over
`document_life_situation` grouped by situation; `domains[].count` the same over `document_domain`. Summing
cells would double-count documents sitting in several columns of one row, so the service never derives
totals from cells. Each total equals what the documents endpoint returns as `total` for that single-axis
filter (chapter 4) — a test locks that equivalence, so row/column selection in the UI always shows the
number it promised.

**Grand `total`** is the number of documents in scope, tagged or not (`DocumentService` already counts
by jurisdiction); it powers the "all documents" corner link.

**Response uses codes**, not ids, so the frontend links cells straight to
`/documents?domain=…&situation=…`. Cell ordering follows `sort_order` of domain then situation for
stable output.

**Scale seam.** If this exceeds its budget on real data, the answer is a materialized view refreshed on
tagging changes ([gaps-and-decisions.md](../gaps-and-decisions.md)); not built now.

## Files

**Add / edit**

| Path | Change |
| --- | --- |
| `apps/api/app/features/taxonomy/repository.py` | `matrix_counts(document_ids: Sequence[UUID] \| None)` |
| `apps/api/app/features/taxonomy/service.py` | `get_matrix(document_ids \| None)` maps ids to codes |
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
| `matrix · codes and order are stable` | Sorted by sort_order |
| `matrix · situation total counts each document once even if it is in several domains` | Row total < sum of its cells |
| `matrix · domain total counts each document once even if it is in several situations` | Column total < sum of its cells |
| `matrix · axis total equals documents endpoint total for the same single filter` | Cross-check with chapter 4 |
| `matrix · total includes untagged documents` | Grand total ≥ any axis total |
| `matrix · terms with no documents in scope are omitted from situations and domains` | Scoped to another jurisdiction → absent |

## Green

1. Repository cell aggregate, unscoped; test.
2. Axis-total aggregates (`_axis_counts(association)` shared by both axes); tests.
3. Scope parameter; test.
4. Controller composition and response models.

## Refactor gate

- Controller composes two services in ≈5 LOC; if it grows, introduce a small `MatrixQuery` handler
  object in the service layer instead.
- Repository query builder stays under ~5 LOC per method by extracting `_cell_select()`,
  `_axis_counts(association)` (one helper for both axes) and `_scoped(stmt, ids)`.

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
