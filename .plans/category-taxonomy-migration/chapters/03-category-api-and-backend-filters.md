---
name: "Chapter 3 — Category API and backend filters"
overview: "Expose the category tree and machine vocabulary, make category filtering authoritative in the backend, and provide a compatibility bridge for old axis parameters."
id: C3
depends_on:
  - C2
touches:
  - apps/api/app/features/taxonomy/
  - apps/api/app/features/documents/
  - apps/api/app/features/candidates/
  - apps/api/app/features/discovery/
  - apps/api/app/schema/taxonomy/
  - apps/api/app/schema/candidate/
  - apps/api/app/schema/document/
  - apps/api/tests/
  - apps/web/src/test/contract/
execution: chapter-implementer
todos:
  - id: category-read-api
    content: "Expose locale-resolved category tree and machine vocabulary from the target taxonomy."
    status: pending
  - id: category-filter
    content: "Resolve category codes and descendants in document and candidate list queries."
    status: pending
  - id: compatibility
    content: "Translate legacy domain/group/situation filters during the compatibility window and define matrix retirement."
    status: pending
  - id: tests
    content: "Add API, repository, unknown-code, descendant, compatibility, and response-shape tests."
    status: pending
---

# Chapter 3 — Category API and backend filters

**Repo:** `redtape` (`apps/api`)
**Depends on:** [Chapter 2](02-category-schema-and-data-migration.md) · **Architecture:** [../00-architecture.md](../00-architecture.md) · **Rollout:** [../01-rollout.md](../01-rollout.md)

## Goal

Make the new category tree the authoritative backend read and filter contract while old clients can still transition. The backend owns parent/descendant semantics so the web, admin, machine workers, and future clients cannot diverge.

## Design decisions

- Add `GET /api/v1/categories` for locale-resolved roots and children.
- Change `GET /api/v1/discovery/machine/taxonomy` to expose the active category vocabulary and the metadata workers need; do not expose the obsolete dual-axis vocabulary as the primary contract.
- Add `filter[category]` using the repository's established repeated/CSV list convention. A root expands to active descendants in the taxonomy service/repository.
- Return canonical category tags with `code`, localized `name`, and `confidence`; do not return PVOG leaf codes as category tags.
- Translate old `filter[domain]`, `filter[situation]`, and web `group` inputs through the chapter 1 crosswalk only during the compatibility window. Conflicts and unknowns remain explicit validation errors.
- Keep `/matrix` dormant until the reference scan proves no runtime consumer; then remove it in chapter 9 rather than maintaining a second aggregate contract.
- Preserve the candidate browse score model and confidence ordering. A category filter changes the selected evidence set, not the confidence algorithm.

## Files

| Path | Change |
| --- | --- |
| `apps/api/app/features/taxonomy/repository.py` | List tree rows, resolve codes, expand descendants, and return ordered category terms. |
| `apps/api/app/features/taxonomy/service.py` | Add locale resolution, category validation, descendant expansion, machine vocabulary, and compatibility crosswalk resolution. |
| `apps/api/app/features/taxonomy/controller.py` | Add category-tree route and retire dual-axis routes only at the documented cutoff. |
| `apps/api/app/schema/taxonomy/read.py` | Add tree/node, category tag, machine vocabulary, and compatibility response models. |
| `apps/api/app/features/discovery/taxonomy_machine_controller.py` | Serve the category machine contract. |
| `apps/api/app/features/documents/query.py` | Replace or bridge `DocumentFilters` domain/situation fields with category codes. |
| `apps/api/app/features/documents/repository.py` | Filter through `document_category`, expand roots, load canonical tags, and retain score ordering. |
| `apps/api/app/features/documents/service.py` | Resolve category filters and map canonical tags to localized reads. |
| `apps/api/app/features/candidates/repository.py` | Apply category filters to candidate score/tag data. |
| `apps/api/app/features/candidates/service.py` | Validate category codes and localize category names. |
| `apps/api/app/features/discovery/candidate_codes.py` | Replace axis-specific known-code filtering with category validation and explicit compatibility accounting. |
| `apps/api/app/schema/candidate/read.py` | Replace public `domains`/`situations` tag arrays with canonical category tags when the contract cutover is approved. |
| `apps/api/tests/test_taxonomy_api.py` | Test tree order, locale, fallback, and node shape. |
| `apps/api/tests/test_taxonomy_repository.py` | Test descendant expansion and ordering. |
| `apps/api/tests/test_documents_filter.py` | Test category filtering and compatibility inputs. |
| `apps/api/tests/test_candidates_public_api.py` | Test category filtering, tags, and unknown codes. |
| `apps/api/tests/test_discovery_taxonomy_route.py` | Test the machine category vocabulary. |
| `apps/api/tests/test_matrix_endpoint.py` | Keep the current dormant behavior characterized until chapter 9 removes it. |
| `apps/web/src/test/contract/openapi.schemas.json` | Update only after the API contract is generated and verified. |

## Red tests

### Happy path

- `categories · returns ordered localized roots and children` asserts stable order, parent code, icon, and locale fallback.
- `documents · root filter includes descendant categories` asserts a root returns documents linked to children without requiring a second filter.
- `candidates · category filter returns canonical tags and confidence` asserts list and detail reads use one tag vocabulary.
- `machine taxonomy · returns active category codes` asserts workers receive the frozen category inventory.

### Negative path

- `categories · cyclic or inactive parent cannot be served` asserts invalid taxonomy is rejected or excluded before it reaches clients.
- `documents · unknown category returns 422` asserts no silent empty result.
- `candidates · legacy filter with conflicting mapping returns a diagnostic validation error` asserts compatibility does not hide ambiguity.
- `machine taxonomy · source-only PVOG leaf is not offered as a product category` asserts the machine enum remains small and canonical.

Run the API suite before changing production code and confirm failures are contract failures.

## Green

1. Add repository/service tree reads and category code resolution.
2. Add the locale-resolved public endpoint and machine response.
3. Switch document and candidate reads to category filters and canonical tag mapping.
4. Add compatibility translation for old filters and define warning/telemetry behavior.
5. Update OpenAPI and frontend contract fixtures only after the API response is stable.

## Refactor gate

Audit the complete taxonomy/controller/filter path:

- controllers perform no SQL and contain only parameter/response orchestration;
- category resolution and descendant expansion live in one service/repository path;
- legacy translation is an adapter at the boundary, not branches spread through query code;
- no endpoint maintains a duplicate code-to-name map;
- candidate and document filters share a narrow category filter DTO;
- no boolean parameter selects old versus new semantics inside a repository;
- list/card/detail read mappers do not reconstruct category paths independently.

Report the refactor outcome and rerun API tests after each extraction.

## Verification

```bash
cd apps/api
uv run pytest tests/test_taxonomy_api.py tests/test_taxonomy_repository.py \
  tests/test_documents_filter.py tests/test_candidates_public_api.py \
  tests/test_discovery_taxonomy_route.py tests/test_matrix_endpoint.py
uv run ruff format --check . && uv run ruff check . && uv run mypy app scripts
./ci.sh
```

Use the web contract test after regenerating the OpenAPI snapshot. Record category-tree response, filter parity, and compatibility results in [../run-ledger.md](../run-ledger.md).

## Out of scope

PVOG/LLM writer migration, frontend component work, deleting old routes/tables, redesigning document detail, embeddings, and entity identification.

## Git workflow

```bash
git checkout feat/plans-category-taxonomy-migration && git pull
git checkout -b feat/category-api-filters
```

```text
test(api): describe category tree and filter contract
feat(api): expose canonical category browsing
```
