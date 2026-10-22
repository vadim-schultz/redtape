---
name: "Chapter 4 — Controller params and locale"
overview: "Replace 8-parameter list handlers with a query DTO; share locale resolution and paging parameters; slim suggestions create."
todos:
  - id: characterize
    content: "Pin list and create responses for documents, suggestions, locations, taxonomy"
    status: pending
  - id: dto
    content: "Query-params DTO for list_documents and list_suggestions"
    status: pending
  - id: shared-deps
    content: "Shared locale and paging dependencies"
    status: pending
  - id: create
    content: "suggestions create split into small steps"
    status: pending
isProject: false
---

# Chapter 4 — Controller params and locale

**Repo:** `redtape` · **Branch:** `refactor/controller-params-and-locale` · **Status:** planned

**Depends on:** chapter 1 · **Architecture:** [../00-architecture.md](../00-architecture.md) B4 · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/plans-code-rules-remediation` · **Release branch:** `main`

## Goal

Controllers call one service per handler and stay about 5 lines. Query parameters travel as one object, and cross-cutting lookups (locale, paging) are shared dependencies. OpenAPI parameter names and defaults do not change.

## Files

- `apps/api/app/features/documents/controller.py:25` `list_documents` (8 parameters); lines 36-49 read `request.app.state` and resolve the locale.
- `apps/api/app/features/suggestions/controller.py:64-95` `create` (18 lines, catches six domain errors, builds the `Location` header and `SuggestionRead`, 5 parameters); `:97` `list_suggestions` (8 parameters, calls two collaborators).
- `apps/api/app/features/locations/controller.py:26-38`, `apps/api/app/features/taxonomy/controller.py:15` — locale and `enabled_locale_codes` lookup (5 copies in total).
- `Parameter(query="offset"/"limit")` pairs repeated in 4 controllers.
- `apps/api/app/features/suggestions/repository.py:71` `list_page` (6 parameters).
- New: `apps/api/app/shared/` (or an existing shared module) with `paging.py` and `locale.py` dependencies.

## TDD loop

### Red

1. Happy path: list endpoints return the same pages, ordering, and locale-specific names as today (characterization); `create` returns 201 with the `Location` header.
2. Negative path: invalid paging (`limit=0`, negative `offset`) and an unsupported locale give the same 4xx as today; `create` conflicts map to the same statuses and bodies (409, 422, and the rest).

### Green

1. A frozen dataclass or Pydantic model per list endpoint (`DocumentListQuery`, `SuggestionListQuery`) built by Litestar dependencies; handlers take it as one parameter.
2. One `PageParams` dependency for offset/limit and one `ResolvedLocale` dependency; delete the copies.
3. Move `create`'s error-to-response mapping into a `_to_http` helper (pattern from `voting/controller.py`); collaborators fold behind one service call where a handler touches two services.

### Refactor

Audit every touched controller: about 5 lines per handler, at most 3 parameters, no boolean flags. Report parameter counts before and after (expected: 8 → at most 3).

## Verification

```bash
cd apps/api
uv run ruff format --check . && uv run ruff check . && uv run mypy app scripts
uv run pytest -k "documents or suggestions or locations or taxonomy"
cd ../..
./ci.sh
```

Also compare the generated OpenAPI before and after (`/schema/openapi.json`); only internal names may differ.

## Git workflow

```bash
git checkout feat/plans-code-rules-remediation && git pull
git checkout -b refactor/controller-params-and-locale
```

```text
test(api): pin list and create responses before refactoring controllers
refactor(api): pass list queries as one DTO and share locale and paging dependencies
```

Open the chapter PR into `feat/plans-code-rules-remediation`, not `main`.
