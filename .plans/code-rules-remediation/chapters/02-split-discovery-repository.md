---
name: "Chapter 2 — Split DiscoveryRepository"
overview: "Break the 427-line DiscoveryRepository into queries-only repositories and move claim business logic into a service."
todos:
  - id: characterize
    content: "Characterization tests for catalogue, task, entity, claim repository behaviour"
    status: pending
  - id: split
    content: "Four repositories of about 100 lines each"
    status: pending
  - id: claim-service
    content: "append_claim fingerprint/upsert/rollback logic moves to a claim service"
    status: pending
isProject: false
---

# Chapter 2 — Split DiscoveryRepository

**Repo:** `redtape` · **Branch:** `refactor/split-discovery-repository` · **Status:** planned

**Depends on:** chapter 1 · **Architecture:** [../00-architecture.md](../00-architecture.md) B2, B6 · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/plans-code-rules-remediation` · **Release branch:** `main`

## Goal

Repositories only run queries. `DiscoveryRepository` (`apps/api/app/features/discovery/repository.py`, 513 lines, class about 427) is split by aggregate, and business logic and transaction policy move up to a service. Public behaviour is unchanged.

## Files

- `apps/api/app/features/discovery/repository.py` — mixed concerns:
  - `append_claim` (~line 426-470): fingerprinting, upsert, rollback, race recovery.
  - `upsert_catalogue_item` (~102) and rollback paths (~130, 147, 458): transaction policy.
  - `_is_jurisdiction_foreign_key_violation` (~65-77): parses DB error codes and constraint names.
  - `fetch_coverage_metrics` (~327): three near-identical count queries.
  - `append_fetch_log` (~256): 6 parameters.
- Callers: `service.py`, `emit.py`, `fanout.py`, `dependencies.py`, `router.py` (dependency providers), tests under `apps/api/tests/`.
- New layout (a package): `apps/api/app/features/discovery/repository/` with `catalogue.py`, `tasks.py`, `entities.py`, `claims.py`, and an `__init__.py` re-exporting what callers import. Add `claim_service.py` (or similar) for the fingerprint and conflict-recovery logic.

## TDD loop

### Red (characterization first)

1. Happy path per aggregate: upsert and read catalogue item; enqueue and claim a task; create an entity; append a claim.
2. Negative path: duplicate claim (same fingerprint) is idempotent and writes nothing extra; claim for an unknown jurisdiction raises the domain invalid-reference error from chapter 1; a lost race on upsert recovers without a partial write.

Run against the **current** repository (they must pass: they pin behaviour), then switch imports to the new modules and confirm they fail for the right reason (missing module), then green.

### Green

1. Create the package and move methods by aggregate with no logic edits.
2. Extract fingerprint, upsert-or-recover, and rollback policy into the claim service; the claim repository exposes only queries and flushes.
3. Parameter objects (a small dataclass) for any method with more than 3 parameters, such as `append_fetch_log`.

### Refactor

Audit each new class: about 100 lines, methods about 5 lines, no boolean flags, one nesting level. Extract a single `_count_by(...)` helper for the three count queries in `fetch_coverage_metrics`. Report before/after line counts (`DiscoveryRepository 427 → N × about 100`).

## Verification

```bash
cd apps/api
uv run ruff format --check . && uv run ruff check . && uv run mypy app scripts
uv run pytest -k discovery
cd ../..
./ci.sh
```

## Git workflow

```bash
git checkout feat/plans-code-rules-remediation && git pull
git checkout -b refactor/split-discovery-repository
```

```text
test(api): characterize discovery repository behaviour
refactor(api): split DiscoveryRepository by aggregate and move claim logic to a service
```

Open the chapter PR into `feat/plans-code-rules-remediation`, not `main`.
