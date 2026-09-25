---
name: "Chapter 3 — Taxonomy API"
overview: "New features/taxonomy package with repository, service, controller and router exposing locale-resolved GET /api/v1/domains and /api/v1/life-situations."
todos:
  - id: repo
    content: "TaxonomyRepository: ordered list of domains and situations; lookup ids by code"
    status: completed
  - id: service
    content: "TaxonomyService: resolves i18n, exposes code->id resolution for other features"
    status: completed
  - id: http
    content: "Controller, router, dependencies; router registered in main.py"
    status: completed
  - id: schema
    content: "Pydantic read models under app/schema/taxonomy"
    status: completed
isProject: false
---

# Chapter 3 — Taxonomy API

**Repo:** `redtape` (`apps/api`) · **Branch:** `feat/matrix-taxonomy-api` · **Status:** done

**Depends on:** [2](02-germany-seed.md) · **Architecture:** [../00-architecture.md](../00-architecture.md) §5 · **Rollout:** [../01-rollout.md](../01-rollout.md)

---

## Goal

`GET /api/v1/domains` and `GET /api/v1/life-situations` return ordered, locale-resolved lists. The
taxonomy service also offers `resolve_domain_ids(codes)` / `resolve_situation_ids(codes)` for the
documents feature (chapter 4), raising a domain error for unknown codes.

## Design decisions

**Copy the documents feature shape exactly:** `repository.py`, `service.py`, `controller.py`,
`dependencies.py`, `router.py` under `apps/api/app/features/taxonomy/` (see
[features/documents/](../../../apps/api/app/features/documents/)). Router registered next to
`documents_router` in [main.py](../../../apps/api/app/main.py).

**One generic path for both axes.** Both endpoints differ only in model; the repository exposes
`list_terms(model)` and `ids_for_codes(model, codes)`; the service has `list_domains()` /
`list_situations()` as thin wrappers. Avoids two parallel copies (rule of three would fire at a third
axis).

**i18n resolution reuses the documents logic.** `_pick_i18n` currently lives in
[documents/service.py](../../../apps/api/app/features/documents/service.py). Extract it to a shared
module (`app/i18n_resolution.py` next to [locale_resolution.py](../../../apps/api/app/locale_resolution.py))
in a preparatory refactor commit, with the existing document tests as the safety net, then use it from
both features.

**Unknown codes are a service-level error**, translated to HTTP 422 by the controller, so the
documents feature never sees repositories.

## Files

**Add**

| Path | Contents |
| --- | --- |
| `apps/api/app/features/taxonomy/{repository,service,controller,dependencies,router}.py` | Feature stack |
| `apps/api/app/schema/taxonomy/read.py` | `TermRead {code, name, description, icon}` |
| `apps/api/app/i18n_resolution.py` | Extracted `pick_i18n` |
| `apps/api/tests/test_taxonomy_api.py`, `test_taxonomy_service.py` | Tests below |

**Edit**

| Path | Change |
| --- | --- |
| `apps/api/app/features/documents/service.py` | Import shared `pick_i18n` instead of local helper |
| `apps/api/app/main.py` | Register `taxonomy_router` |

## Red tests

| Test | Asserts |
| --- | --- |
| `domains · returns all domains in sort order` | Order and count |
| `domains · resolves names to the request locale` | `Accept-Language: en` → English names |
| `domains · falls back to de when the locale has no name` | Existing fallback chain |
| `life-situations · returns 18 situations with icon and code` | Shape |
| `service · resolves known codes to ids` | Returned ids match |
| `service · unknown code raises TaxonomyCodeError` | Negative path |
| `documents · pick_i18n unchanged after extraction` | Existing document tests still green |

## Green

1. Preparatory refactor: extract `pick_i18n`, keep all existing tests green, commit.
2. Repository + service for domains; controller/router; test list endpoint.
3. Generalize to situations; add code resolution.

## Refactor gate

- Controller has no queries; service has no SQL; repository has no i18n logic. Verify by grep for
  `select(` outside repository and `Accept-Language` handling outside controller/middleware.
- Each handler ≈5 LOC; the two list endpoints share one private helper rather than duplicating.

## Verification

```bash
cd apps/api
python -m pytest tests/test_taxonomy_api.py tests/test_taxonomy_service.py
cd ../.. && ./ci.sh
curl -s -H 'Accept-Language: en' localhost:8000/api/v1/domains | head
```

## Out of scope

Filtering documents (chapter 4), matrix counts (chapter 5), write endpoints.

## Git workflow

```bash
git checkout main && git pull
git checkout -b feat/matrix-taxonomy-api
```

```text
refactor(api): share i18n resolution between features

feat(api): list domains and life situations with resolved names
```

## Outcome

- `pick_i18n` extracted to `app/i18n_resolution.py` (own unit tests); documents feature imports it.
- Repository, service, controller stay under 40 LOC each; both endpoints and both code resolvers go through one private helper per layer.
- `TaxonomyCodeError` is raised by the service. No endpoint consumes codes yet, so the HTTP 422 mapping lands with chapter 4 rather than as dead code here.
- DB-backed tests skip under the SQLite `ci.sh` run like the existing ones; verified against local Postgres (dev DB drift makes a few older seed/model tests fail there independent of this change).
