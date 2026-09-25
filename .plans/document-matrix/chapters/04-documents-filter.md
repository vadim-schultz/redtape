---
name: "Chapter 4 — Documents filter and tags"
overview: "Optional domain and situation query params on GET /api/v1/documents, and domains/life_situations arrays in the document detail response, via the taxonomy service."
todos:
  - id: filter
    content: "Repository filters by domain/situation ids (AND across axes, OR within an axis)"
    status: pending
  - id: params
    content: "Controller params domain and situation; unknown code -> 422"
    status: pending
  - id: tags
    content: "Detail response includes resolved domains and life_situations"
    status: pending
isProject: false
---

# Chapter 4 — Documents filter and tags

**Repo:** `redtape` (`apps/api`) · **Branch:** `feat/matrix-documents-filter` · **Status:** planned

**Depends on:** [2](02-germany-seed.md), [3](03-taxonomy-api.md) · **Architecture:** [../00-architecture.md](../00-architecture.md) §5 · **Rollout:** [../01-rollout.md](../01-rollout.md)

---

## Goal

`GET /api/v1/documents?domain=housing&situation=moving-house` returns only documents tagged in both. Detail
responses list each document's domains and situations. Without the params, output is byte-for-byte what
it is today.

## Design decisions

**Semantics.** Across axes: AND. Within an axis (repeatable param, `?domain=a&domain=b`): OR. This
makes the matrix cell link and multi-chip filtering the same call.

**Layering.** Controller passes code lists to `DocumentService`. The service asks
`TaxonomyService.resolve_*_ids` (chapter 3) and hands ids to `DocumentRepository`. The documents
feature does not import taxonomy models or repository. `DocumentService` gains `TaxonomyService` as a
constructor dependency wired in [dependencies.py](../../../apps/api/app/features/documents/dependencies.py).

**Filter as composable query fragments.** `_base_select` in
[repository.py](../../../apps/api/app/features/documents/repository.py) grows a `domain_ids` and
`situation_ids` parameter; each adds one `EXISTS` subquery. `count` and `list_page` must share the same
filtered select so `total` stays correct.

**Tags in detail only.** The list stays lightweight (`DocumentSummary` unchanged) in this chapter;
card badges (chapter 9) use a `tags` field added to the summary there if measured worthwhile — recorded
as a seam, not built now.

## Files

**Edit**

| Path | Change |
| --- | --- |
| `apps/api/app/features/documents/repository.py` | Filter fragments shared by `count` and `list_page`; eager tags on detail |
| `apps/api/app/features/documents/service.py` | Resolve codes via taxonomy service; map tags to read models |
| `apps/api/app/features/documents/controller.py` | `domain`, `situation` list query params |
| `apps/api/app/features/documents/dependencies.py` | Inject `TaxonomyService` |
| `apps/api/app/schema/document/read.py` | `TermRead` fields `domains`, `life_situations` on `DocumentDetail` (default empty) |

**Add** — `apps/api/tests/test_documents_filter.py`.

## Red tests

| Test | Asserts |
| --- | --- |
| `filter · domain returns only documents tagged with it` | Result ids |
| `filter · domain and situation are ANDed` | Intersection only |
| `filter · two domains are ORed` | Union within axis |
| `filter · total reflects the filter, not the catalog` | `total` equals filtered count |
| `filter · unknown domain code returns 422` | Negative path |
| `filter · situation alone returns every document with it, across domains` | Row selection (matrix row header) |
| `filter · domain alone returns every document with it, across situations` | Column selection (matrix column header) |
| `filter · no params returns the unfiltered list` | Regression guard |
| `filter · untagged document never appears when a filter is set` | Negative |
| `detail · includes resolved domains and life_situations` | Locale-resolved names |
| `detail · document without tags returns empty arrays` | Not null |

## Green

1. Repository filter on one axis; test; then second axis.
2. Service wiring and 422 mapping.
3. Detail tags.

## Refactor gate

- `_base_select` must not exceed ~5 LOC of its own: extract `_filter_by_terms(stmt, association, ids)`
  and call it twice.
- `DocumentService.list_documents` already has many parameters; introduce a `DocumentFilters`
  dataclass (`jurisdiction_id`, `municipality_code`, `domain_codes`, `situation_codes`) instead of
  adding two more arguments.
- No nesting beyond one level in code-resolution branches.

## Verification

```bash
cd apps/api
python -m pytest tests/test_documents_filter.py tests/test_document_jurisdiction_path.py
cd ../.. && ./ci.sh
curl -s 'localhost:8000/api/v1/documents?domain=housing&situation=moving-house'
```

## Out of scope

Tags on list items, matrix counts (chapter 5), web changes.

## Git workflow

```bash
git checkout main && git pull
git checkout -b feat/matrix-documents-filter
```

```text
test(api): describe document filtering by domain and situation

feat(api): filter documents by domain and life situation and expose tags on detail
```
