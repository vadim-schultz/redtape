---
name: "Chapter 5 — Read-only catalogue pipeline"
overview: "The admin catalogue_pipeline GET stops writing pipeline_stage; stage transitions live in one place."
todos:
  - id: characterize
    content: "GET twice leaves the stage unchanged; unknown id returns 404"
    status: pending
  - id: move-write
    content: "Stage write moves to the explicit machine path"
    status: pending
  - id: centralize
    content: "One stage-transition table or handler per stage"
    status: pending
isProject: false
---

# Chapter 5 — Read-only catalogue pipeline

**Repo:** `redtape` · **Branch:** `refactor/read-only-catalogue-pipeline` · **Status:** planned

**Depends on:** chapter 2 · **Architecture:** [../00-architecture.md](../00-architecture.md) B5 · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/plans-code-rules-remediation` · **Release branch:** `main`

## Goal

An admin GET never mutates data, and the pipeline stage rules (T0, T1, T3 and so on) live in one module instead of string literals in three places.

## Files

- `apps/api/app/features/discovery/service.py` — `DiscoveryAdminService.catalogue_pipeline` (about lines 170-198, 28 lines, six repository calls) derives the stage and sets `row.pipeline_stage`; inline transitions at about 189, 213-214 ("T0" to "T1"), 351-352 ("T3").
- `apps/api/app/features/discovery/pipeline.py`, `apps/api/app/features/discovery/fanout.py` — stage logic also lives here.
- `apps/api/app/features/discovery/admin_controller.py` — the GET handler.
- Machine write path: `DiscoveryMachineService` in `service.py` (the explicit place that advances stages).
- Frontend consumer to keep working: `DiscoveryPipelinePage` (reads the derived stage label from the API).

## TDD loop

### Red

1. Happy path: `GET .../pipeline/{id}` returns the derived stage label, and a second identical GET returns the same body (idempotent).
2. Negative path: after the GET the stored `pipeline_stage` is **unchanged** (assert on the row); an unknown id returns 404 with the pinned body.
3. Machine path: the explicit machine endpoint or service call still advances the stage (characterization).

Red evidence: test 2 fails today because the GET mutates the row.

### Green

1. Derive the stage in the read path without assigning to the row.
2. Perform the stage persistence in the machine path (or at the moment the underlying event happens), covered by test 3.
3. Replace inline literals with one transition table (an enum of stages plus a mapping or a handler per stage) in `pipeline.py`, used by service, fanout, and the read path.

### Refactor

Audit `DiscoveryAdminService` and the stage module: `catalogue_pipeline` about 5 lines (delegate to small helpers), rule of three on the stage branches (more than 2 arms means a table or handlers), no inline stage strings. Report the number of stage-literal sites before and after.

## Verification

```bash
cd apps/api
uv run ruff format --check . && uv run ruff check . && uv run mypy app scripts
uv run pytest -k "discovery"
cd ../..
./ci.sh
```

Manual: open an admin pipeline page in the web app and confirm it renders the same stage label as before.

## Git workflow

```bash
git checkout feat/plans-code-rules-remediation && git pull
git checkout -b refactor/read-only-catalogue-pipeline
```

```text
test(api): assert the catalogue pipeline GET does not change the stored stage
refactor(api): derive pipeline stage read-only and centralise stage transitions
```

Open the chapter PR into `feat/plans-code-rules-remediation`, not `main`.
