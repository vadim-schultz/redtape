---
name: "Chapter 1 — Runtime correctness"
overview: "Fix the emit-batch rollback seam, announce discovery-admin page loading, and reject an explicit worker max-tasks zero."
todos:
  - id: emit-savepoint
    content: "Add paired emit tests and scope an IntegrityError rollback to one insert."
    status: pending
  - id: page-loading
    content: "Add paired drill-down page tests and use LoadingNote in both QueryBoundary shells."
    status: pending
  - id: cli-bound
    content: "Replace the zero-max-tasks characterization with a usage-error regression test and preserve omitted defaults."
    status: pending
isProject: false
---

# Chapter 1 — Runtime correctness

**Repo:** `redtape` · **Branch:** `fix/audit-remediation-runtime` · **Status:** planned  
**Depends on:** parent audit on `main` · **Architecture:** [00-architecture.md](../00-architecture.md) · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/plans-codebase-audit-remediation` · **Release branch:** `main`

## Goal

Fix three independent seams without changing successful-path contracts:

1. A uniqueness race in suggestion insert must not roll back earlier emit-batch inserts.
2. Discovery document and pipeline loading must be announced through `LoadingNote`.
3. An explicit `--max-tasks 0` must exit with `EXIT_USAGE`; an omitted option keeps its default.

## Design decisions

- Scope the suggestion insert and flush in a nested transaction/savepoint. Do not use a full
  `Session.rollback()` for the per-item race path.
- Reuse the existing `QueryBoundary` and `LoadingNote`; do not add a page-specific loading helper.
- Preserve `None` as the omitted CLI value and let explicit zero reach a guard that reports usage
  error before any API claim request.

## Files

| Path | Change |
| --- | --- |
| `apps/api/app/features/suggestions/{service,repository}.py` | Scope the insert conflict rollback. |
| `apps/api/tests/test_discovery_emit_service.py` | Add the emit-batch regression pair. |
| `apps/web/src/features/discovery-admin/containers/{DiscoveryDocumentPage,DiscoveryPipelinePage}.tsx` | Use `LoadingNote`. |
| `apps/web/src/features/discovery-admin/containers/{DiscoveryDocumentPage,DiscoveryPipelinePage}.test.tsx` | Add loading-state assertions. |
| `apps/discovery-ingest/discovery_ingest/cli/worker/commands.py` | Reject explicit zero. |
| `apps/discovery-ingest/tests/test_ingest_operations_contract.py` | Replace the old zero-default characterization. |
| `apps/discovery-ingest/tests/test_cli_worker.py` or the existing worker CLI contract test | Pin no claim request on invalid zero. |

Do not change workflow defaults, `DrainOptions.policy()` semantics for `None`, emit routes, or
production data.

## Red tests

Write both tests in each slice before production changes.

### Slice A — emit persistence

- Happy: the existing multi-claim emit test still creates one pending suggestion per valid claim.
- Negative: `test_emit_catalogue_keeps_earlier_suggestions_when_a_later_insert_hits_integrity_error`
  simulates a conflict on a later claim and asserts the earlier suggestion remains persisted while
  the conflict follows the existing replay/skip contract. It fails against the full rollback.

### Slice B — page loading

- Happy: each existing loaded-page test still renders the document or pipeline content.
- Negative: while the main query is pending, each page exposes a status-role loading message and
  does not render the loaded content.

### Slice C — CLI bounds

- Happy: an omitted `--max-tasks` still sends the existing default claim limit.
- Negative: `--max-tasks 0` returns exit code `2`, prints an invalid-bounds message, and makes no
  claim request. Replace the current
  `test_worker_drain_zero_max_tasks_keeps_the_default_claim_size` characterization.

Run the narrow suite after each red test pair and confirm failures are for the intended reasons.

## Green

1. Add a repository-level nested transaction or equivalent scoped insert operation; map the
   existing replay result after the nested rollback.
2. Pass `loading={<LoadingNote />}` to both page boundaries and remove unused imports.
3. Add the explicit zero guard before `DrainOptions` is executed; leave omitted values as `None`.

## Refactor gate

Audit the whole containing entities:

- `SuggestionService._insert` and the repository insert/rollback methods: one transaction boundary,
  no boolean mode parameter, no duplicated savepoint code, and no outer-session rollback on the
  emit path.
- Both page components: one query boundary and one loading component; no new abstraction for two
  call sites.
- `worker_drain`: guard clause before options construction; no helper extraction unless the method
  grows beyond one concern.

Report `Refactor gate: smells found -> ...; refactorings applied -> ...` and rerun the narrow suite
after each extraction. If no further extraction is needed, say so explicitly.

## Verification

```bash
cd apps/api
uv run pytest tests/test_discovery_emit_service.py tests/test_discovery_emit.py
uv run ruff format --check . && uv run ruff check . && uv run mypy app scripts

cd ../discovery-ingest
uv run pytest tests/test_operations_drain.py tests/test_worker_drain.py tests/test_ingest_operations_contract.py
uv run ruff format --check . && uv run ruff check . && uv run mypy discovery_ingest

cd ../web
npx tsc --noEmit
npx eslint "src/features/discovery-admin/containers/**/*.{ts,tsx}"
npm test -- src/features/discovery-admin/containers
```

Run `./ci.sh` before the chapter PR is pushed.

## Out of scope

Promotion conflict mapping, vote races, partial GovData/enrich semantics, C8 production cleanup,
and the refactor-only query-options/component work in chapter 2.

## Git workflow

```bash
git checkout feat/plans-codebase-audit-remediation && git pull
git checkout -b fix/audit-remediation-runtime
```

Use `test(...)` commits before `fix(...)` commits. Open the chapter PR into the remediation loop
branch, not `main`.

