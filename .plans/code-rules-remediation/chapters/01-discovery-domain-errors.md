---
name: "Chapter 1 — Discovery domain errors"
overview: "Discovery services and repositories raise domain errors; the router and controllers map them to HTTP, as suggestions and voting already do."
todos:
  - id: characterize
    content: "Pin current 404/422 responses of discovery admin and machine endpoints"
    status: pending
  - id: domain-errors
    content: "Define discovery domain errors; services and repository raise them"
    status: pending
  - id: map-http
    content: "Map the errors to HTTP in the router or controllers"
    status: pending
isProject: false
---

# Chapter 1 — Discovery domain errors

**Repo:** `redtape` · **Branch:** `refactor/discovery-domain-errors` · **Status:** planned

**Depends on:** chapter 0 (done) · **Architecture:** [../00-architecture.md](../00-architecture.md) B1 · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/plans-code-rules-remediation` · **Release branch:** `main`

## Goal

No Litestar HTTP exception or status code lives below the controller layer in `apps/api/app/features/discovery/`. Services and repositories raise domain errors; controllers or the router's exception handlers translate them. Response status codes and bodies of existing endpoints stay identical.

## Files

- `apps/api/app/features/discovery/service.py` — imports Litestar `NotFoundException` / `ValidationException` (raised around lines 273, 316, 320, 336, 340, 386).
- `apps/api/app/features/discovery/emit.py:7,45` — `NotFoundException`.
- `apps/api/app/features/discovery/repository.py:10,81-84` — builds `ClientException(status_code=422)` for a jurisdiction FK violation.
- `apps/api/app/features/discovery/router.py` — has `_invalid_payload_is_422`; add or extend exception handlers here.
- `apps/api/app/features/discovery/admin_controller.py:61-62,72-73` — duplicates the not-found check that `_require_task` does in the service.
- Pattern to copy: `apps/api/app/features/suggestions/controller.py` (`_to_http`) and `voting/controller.py`.
- New: `apps/api/app/features/discovery/errors.py` (domain errors, with docstrings and precise types).

## TDD loop

### Red

1. Service level, happy path: an existing task or catalogue item loads without error (characterization).
2. Service level, negative path: a missing task / catalogue item / entity raises the **domain** `...NotFound` error (not a Litestar exception); an unknown jurisdiction FK raises the domain invalid-reference error; no row is written.
3. API level, negative path: the same cases still return **404** and **422** with the same body shape as today (pin the current bodies first).

Run the narrow suite and confirm the new service tests fail because the domain errors do not exist, while the API tests pass (they are characterization).

### Green

1. Add `errors.py` with small exception classes (one per failure mode, shared base).
2. Replace each Litestar exception in service, emit, and repository with the domain error. Remove the Litestar imports from those modules.
3. Add exception handlers (or `_to_http`-style mapping) so the HTTP responses match the pinned ones.

### Refactor

Audit `DiscoveryMachineService`, `DiscoveryAdminService`, `DiscoveryEmitService` per the refactor-step checklist: duplicated `_require_task` and `if x is None: raise` blocks, hand-built 422s, one nesting level. Report outcome with before/after counts of Litestar imports below the controller (expected: zero).

## Verification

```bash
cd apps/api
uv run ruff format --check . && uv run ruff check . && uv run mypy app scripts
uv run pytest tests/test_discovery_admin_api.py tests/ -k discovery
cd ../..
./ci.sh
```

Run the long discovery API tests in the background; the admin API file is slow.

## Git workflow

```bash
git checkout feat/plans-code-rules-remediation && git pull
git checkout -b refactor/discovery-domain-errors
```

```text
test(api): pin discovery not-found and invalid-reference responses
refactor(api): raise domain errors from discovery services and map them in the router
```

Open the chapter PR into `feat/plans-code-rules-remediation`, not `main`.
