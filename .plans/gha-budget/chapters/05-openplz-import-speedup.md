---
name: "Chapter 5 — OpenPLZ import speed-up"
overview: "Preload existing rows and write only new or changed ones, so the monthly import finishes well inside its timeout instead of cancelling after 60 minutes."
todos:
  - id: audit
    content: "Audit readers of last_updated and record decision D11"
    status: pending
  - id: tests
    content: "Red tests: zero writes on a second run, one write per changed row"
    status: pending
  - id: impl
    content: "Preload jurisdictions and localities, write only changes in batches"
    status: pending
  - id: timeout
    content: "Lower the maintenance openplz timeout to 30 minutes"
    status: pending
isProject: false
---

# Chapter 5 — OpenPLZ import speed-up

**Repo:** `redtape` (`apps/api/scripts`, `apps/api/tests`, `.github/workflows`) · **Branch:** `chore/gha-budget-openplz-speedup` · **Status:** planned

**Depends on:** [3](03-monthly-maintenance.md) · **Decisions:** D9 · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `chore/gha-budget`

## Goal

[import_openplz_locations.py](../../../apps/api/scripts/import_openplz_locations.py) takes 47–60 minutes from a GitHub runner to the Supabase pooler. `upsert_jurisdiction` runs one `SELECT` per row, `upsert_locality` one `session.get` per row, and every existing row is rewritten (`last_updated = touched_at`), so a re-import of unchanged data is still N round trips plus N updates. Four of five October runs were cancelled at the 60 minute timeout. A monthly import must finish in well under 15 minutes.

## Design

1. **Audit first.** `grep -rn "last_updated" apps/api/app` and the admin/web readers. Record in [../gaps-and-decisions.md](../gaps-and-decisions.md) a new decision **D11**: whether anything uses `last_updated` as "last import time". Default: unchanged rows are not touched; if a reader needs import recency, write `last_updated` for all imported rows with one bulk `UPDATE ... WHERE id IN (...)` per kind per run instead of per row.
2. **Preload.** At the start of `import_all` (or per state/district scope if memory matters; Germany has on the order of 10^4 municipalities and 10^4–10^5 localities, which fits in memory), load existing jurisdictions keyed by `(kind, code)` and existing locality ids with one query each.
3. **Compare, then write.** `upsert_*` consult the preloaded maps. A row is inserted when absent, updated when any imported field differs (kind, parent, `openplz_type`, postal code, multiple-postal-codes flag, roles, names; for localities the municipality and name), and skipped otherwise. Keep the self-healing behaviour documented in the current comments: a jurisdiction keyed by `(kind, code)` can move to a new parent, a locality keyed by its deterministic id can move to a new municipality.
4. **Batch writes.** Keep the `commit_every` batching and the parent-before-child ordering (the FK comment in `_import_country`, `_import_state` and the district/municipality loops); flush the session where the existing code already does.
5. Keep `--states`, `--dry-run`, `--commit-every` and the public function names used by tests (`import_locations`, `upsert_jurisdiction`, `upsert_locality`); change signatures only if all callers move in the same commit.
6. In `.github/workflows/platform-maintenance.yml` lower the `openplz` job `timeout-minutes` from 60 to 30.

## TDD loops (local Postgres, `REQUIRE_DB=1`)

**Loop A — no-op re-import.** Red (`apps/api/tests/`, next to the existing OpenPLZ import tests; find them with `grep -rln "import_openplz_locations" apps/api/tests`):
1. `second import over identical input performs no writes` — count `UPDATE`/`INSERT` statements (SQLAlchemy event listener) and assert zero on the second run.
2. `second import over identical input leaves row counts unchanged`.

**Loop B — changes are applied once.**
1. `a renamed municipality updates exactly that row`.
2. `a re-parented district moves to the new parent` (self-heal, existing behaviour).
3. `a new locality is inserted and unchanged siblings are untouched`.

**Loop C — flags.** `--states` filters as before; `--dry-run` commits nothing.

**Green:** preload maps plus compare-then-write. **Refactor:** the insert/update helpers stay small and typed; extract the field comparison into one helper rather than repeating it per kind (rule of three applies: two kinds, two call sites).

## Gate

API section of `./ci.sh` (ruff format and check, `mypy app scripts`, pytest with Postgres). Record the before/after statement counts of the Loop A test in the PR body. The live timing is a deferred operator step (O4 in chapter 6).

## Commits

- `test(openplz): pin no-op re-import and changed-row behaviour`
- `perf(openplz): preload existing rows and write only changes`
- `ci(maintenance): shorten the OpenPLZ job timeout to 30 minutes`
