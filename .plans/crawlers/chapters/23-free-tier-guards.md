---
name: "Chapter 23 — Free-tier guards"
overview: "A server-side budget ledger with atomic reservations, a ledger-backed meter for the object store, a database soft limit on machine writes, a worker-side budget client and CLI, and the Actions-minutes cap, so no free allocation can be overrun by concurrent or repeated runs."
todos:
  - id: ledger
    content: "discovery_budget_ledger model, migration, caps in settings, BudgetService with reserve, adjust and exhaust"
    status: pending
  - id: routes
    content: "Machine routes (list, reserve, adjust, exhaust) and the admin list"
    status: pending
  - id: metered-store
    content: "Ledger-backed meter for MeteredObjectStore: R2 Class A and Class B counted and capped"
    status: pending
  - id: db-limit
    content: "Database soft limit dependency on machine write routes"
    status: pending
  - id: worker
    content: "Worker BudgetGuard, budget show and report-minutes CLI, drain workflow skip and minutes steps"
    status: pending
isProject: false
---

# Chapter 23 — Free-tier guards

**Repo:** `redtape` (`apps/api`, `apps/discovery-ingest`, `.github/workflows`) · **Branch:** `feat/crawlers-free-tier-guards` · **Status:** planned (added by the 2026-10-26 replan)

**Depends on:** [13](13-object-store-port-and-r2-adapter.md), [14](14-artifact-model-and-api.md) · **Executed between 14 and 15** · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/crawlers`

## Goal

The suite deliberately runs on free allocations: R2 (10 GB, 1M Class A and 10M Class B operations a month), Cloudflare Browser Run (10 browser minutes a day), Workers AI (10,000 neurons a day, used by the [extraction](../../extraction/00-architecture.md) suite), the Supabase database (500 MB) and GitHub Actions (2,000 minutes a month shared across repositories; this repository is capped at **1,000**). Some of these **bill** when exceeded (R2 always, Workers AI on a paid plan), and a per-run budget cannot stop a second run, a local run and a scheduled run from overspending the same day. This chapter adds one server-side ledger that every run reads before spending and writes after, plus the guards that need no worker cooperation (decisions D23 and D24).

## Contract

**Resources and caps.** All caps are API settings (so tuning needs no worker deploy) with defaults below the allowance, which is the 20 percent margin that absorbs races between concurrent runs.

| Resource | Period | Setting | Default | Allowance |
| --- | --- | --- | --- | --- |
| `r2_class_a` | month | `budget_r2_class_a_monthly` | 400,000 | 1,000,000 |
| `r2_class_b` | month | `budget_r2_class_b_monthly` | 4,000,000 | 10,000,000 |
| `browser_seconds` | day | `budget_browser_seconds_daily` | 480 | 600 |
| `neurons` | day | `budget_neurons_daily` | 8,000 | 10,000 (used by the extraction suite) |
| `actions_minutes` | month | `budget_actions_minutes_monthly` (1,000) minus `actions_ci_reserve_minutes` (600) | 400 | 1,000 for this repository |

Stored bytes are not a ledger resource: `OBJECT_STORE_MAX_BYTES` (chapter 14) is a live sum. The database soft limit is `db_soft_limit_bytes` (default 400,000,000).

**Model.** `discovery_budget_ledger` (new migration, enum-free): `id`, `period String(10)` (`YYYY-MM-DD` for daily, `YYYY-MM` for monthly resources), `resource String(40)`, `used Numeric(14,2)`, `exhausted Boolean`, `updated_at`. Unique `(period, resource)`. The period is always derived on the server from UTC now; workers never send one. Update the hard-coded migration heads in `tests/test_discovery_staging_migration_retry.py` and `tests/test_check_migrations_script.py`, and keep `scripts/check_migrations.sh` green.

**Service** `BudgetService` in `apps/api/app/features/discovery/budgets.py` (small module, pure policy plus one repository method):

- `snapshot(now)` returns one row per resource: `resource`, `period`, `cap`, `used`, `remaining` (clamped at 0), `exhausted`. Resources with no row report `used = 0`.
- `reserve(resource, amount, now)` is **atomic**: `INSERT ... ON CONFLICT (period, resource) DO UPDATE SET used = used + :amount WHERE used + :amount <= :cap AND NOT exhausted RETURNING used`. A returned row means granted; no row means denied (HTTP 409). Two concurrent reservations can never jointly pass the cap.
- `adjust(resource, delta, now)` applies a signed correction after the real cost is known (for example `actual - estimate`), never below zero, and never refused: it records reality.
- `exhaust(resource, now)` sets `exhausted` for the current period, so every later reservation that day or month is denied until the period rolls over. Workers call it when a provider says its quota is gone.

**Routes** (machine key unless stated; unknown resource is 404, a non-finite or non-positive reservation is 422):

- `GET /api/v1/discovery/machine/budgets` returns the snapshot.
- `POST /api/v1/discovery/machine/budgets/{resource}/reserve` `{amount}` returns `{granted, remaining}` (200 granted, 409 denied).
- `POST /api/v1/discovery/machine/budgets/{resource}/adjust` `{delta}` returns the new snapshot row.
- `POST /api/v1/discovery/machine/budgets/{resource}/exhaust` returns the snapshot row.
- `GET /api/v1/discovery/admin/budgets` (admin guard) returns the same snapshot plus the live stored-bytes figure and cap, for the chapter 16 meters.

**Metered object store.** The ledger-backed meter passed to `MeteredObjectStore` (chapter 13) reserves `r2_class_a` for `put` and `delete` and `r2_class_b` for `get` and `exists`. A denial raises `ObjectStoreQuotaError`, which the routes map to 503 and workers treat as `storage_unavailable` (release, stop). **Presigned URLs are served by R2 directly**, so each URL the admin route mints counts one `r2_class_b` operation (conservative, since the browser may fetch it once or not at all). The meter fails closed: if the ledger cannot be written, the operation is refused. The Cloudflare dashboard stays the source of truth for billing (operator steps S8 and S19); the ledger counts only what this application does.

**Database soft limit.** A dependency `require_db_headroom` on the machine write routes that create rows (candidate mentions, candidate edges and entity or claim posts when they exist, fetch log append, artifact upload, task enqueue) reads `pg_database_size(current_database())`, cached in process for five minutes, and answers **507** with `detail = "database_soft_limit"` when it exceeds `db_soft_limit_bytes`. Routes that settle work (`complete`, `fail`, `release`, claim, summary, budgets) are exempt so a full database never strands claimed tasks. A failing size query fails **open** with a warning log: blocking every worker because the measurement broke is worse than the risk it measures. Workers treat a 507 with that detail as a stop (`db_limit`), not a task failure.

**Worker side** (`apps/discovery-ingest/discovery_ingest/budget.py`):

- `DiscoveryMachineClient.get_budgets()`, `reserve_budget(resource, amount)`, `adjust_budget(resource, delta)`, `exhaust_budget(resource)`.
- `BudgetGuard(client)` wraps them for handlers: `remaining(resource)` and `reserve(resource, amount)` return a result object, never raise on a transport or 5xx error, and report `ledger_unavailable = true` so the caller can fall back to its own run budget (invariant 13). A `409` is a normal denial. The drain report carries `ledger_unavailable` when it happened.
- CLI `python -m discovery_ingest budget show [--resource R]... [--require-remaining R=N]...` prints the snapshot as JSON and exits **3** when a required resource has less than N remaining or is exhausted; an unreachable ledger exits 0 with a warning, or **4** with `--strict`. `python -m discovery_ingest budget report-minutes --minutes N` adjusts `actions_minutes`.
- Workflow wiring in this chapter covers the existing `discovery-drain.yml`: `timeout-minutes` stays, a first step `budget show --require-remaining actions_minutes=<timeout>` that skips the rest when it exits 3, a recorded start time, and a final `if: always()` step that reports `ceil((now - start) / 60) + 1` minutes (the extra minute stands for runner setup and rounding). Chapters 15 and E7 of the extraction suite apply the same two steps to `discovery-render.yml` and `discovery-llm.yml`. CI workflows are not metered (GitHub's usage report is the source; the CI reserve is what keeps drains from eating the CI share).

**What the ledger does not do.** It does not poll GitHub or Cloudflare usage APIs (`GITHUB_TOKEN` cannot read remaining minutes), it does not meter CI, and it is not a security boundary: a worker with the machine key could misreport. It stops accidents, not attackers.

## TDD loops

### Loop A — Model and migration

**Red** (`apps/api/tests/test_discovery_models.py`, `test_check_migrations_script.py`)

1. `ledger is unique per period and resource`.
2. `migration upgrades, downgrades and upgrades again; the migration head constants are updated`.

**Green:** model, migration, exports. **Refactor:** share the timestamp mixin with the other discovery tables.

### Loop B — Service

**Red** (`apps/api/tests/test_discovery_budgets.py`, injected `now`)

1. `reserve within the cap is granted and counted`.
2. `reserve that would pass the cap is denied and does not change usage` — negative pair.
3. `reserve after exhaust is denied until the period rolls over` — daily rollover at UTC midnight, monthly at the first of the month.
4. `adjust with a negative delta never goes below zero; adjust is never refused`.
5. `two reservations racing for the last capacity grant exactly one` — two sessions against the test database.
6. `snapshot lists every resource, zero for unused, remaining clamped at zero`.
7. `actions_minutes cap is the monthly cap minus the CI reserve`.

**Green:** one repository method for the atomic upsert, policy in the service. **Refactor:** resource table in one place; no resource names as scattered strings.

### Loop C — Routes

**Red** (`test_discovery_budgets_api.py`)

1. `list requires the machine key and returns every resource with its cap`.
2. `reserve returns 200 when granted and 409 when denied`.
3. `reserve rejects a zero, negative or non-finite amount (422) and an unknown resource (404)`.
4. `adjust and exhaust update the snapshot`.
5. `admin budgets requires an admin and includes stored bytes and the byte cap`.

**Green:** thin controller. **Refactor:** reuse the machine-key dependency used by the sibling routes.

### Loop D — Metered store

**Red** (`test_object_store_metered.py`, `test_discovery_artifacts_api.py`)

1. `put and delete reserve class A, get and exists reserve class B, presign reserves nothing`.
2. `a denied reservation raises ObjectStoreQuotaError before the inner store is touched, and the upload route answers 503 and writes nothing`.
3. `the admin artifact list mints presigned urls and counts one class B per url`.
4. `a ledger write failure refuses the operation (fails closed)`.

**Green:** the ledger meter plugged into the provider from chapter 13. **Refactor:** one constant maps operation to class.

### Loop E — Database soft limit

**Red** (`test_db_headroom.py`, injected size function and clock)

1. `a write route answers 507 database_soft_limit above the limit and 2xx below it`.
2. `complete, fail, release, claim and budgets routes still work above the limit`.
3. `the size is read at most once per five minutes`.
4. `a failing size query lets the request through and logs a warning`.

**Green:** one dependency attached through the router for the listed routes. **Refactor:** the list of guarded routes is declared once.

### Loop F — Worker client, CLI and workflow

**Red** (`apps/discovery-ingest/tests/test_budget_guard.py`, `test_cli_budget.py`, `test_drain_workflow_budget.py`)

1. `BudgetGuard reports a denial on 409 and ledger_unavailable on a 5xx or a transport error without raising`.
2. `budget show exits 3 when a required resource is short or exhausted, 0 when enough, 0 with a warning when unreachable and 4 with --strict`.
3. `budget report-minutes posts the adjustment`.
4. `the drain report carries ledger_unavailable when the ledger could not be read`.
5. `discovery-drain.yml has timeout-minutes, a budget skip step before the drain and an if: always() minutes step` — parses the workflow file.

**Green:** small module and CLI branch. **Refactor:** the CLI stays a thin wrapper over the guard.

## Verification

```bash
cd apps/api && python -m pytest tests/test_discovery_budgets.py tests/test_discovery_budgets_api.py tests/test_object_store_metered.py tests/test_db_headroom.py tests/test_discovery_models.py
cd apps/api && alembic upgrade head && alembic downgrade -1 && alembic upgrade head
cd apps/discovery-ingest && python -m pytest tests/test_budget_guard.py tests/test_cli_budget.py tests/test_drain_workflow_budget.py && ruff check . && mypy discovery_ingest
gh pr checks --watch
```

Live gate (after deploy, with operator steps S19 and S21 done):

```bash
curl -H "Authorization: Bearer $DISCOVERY_API_KEY" "$DISCOVERY_API_URL/api/v1/discovery/machine/budgets"   # five resources with caps
gh workflow run discovery-drain.yml -f max_batches=1 -f max_tasks=5
gh run watch && gh run view --log        # budget show prints before the drain; minutes are reported after it
python -m discovery_ingest budget show   # actions_minutes used has grown by about 1 to 3
```

Record the run ID, the caps and the observed `actions_minutes` delta in the ledger.

## Out of scope

Metering CI minutes, polling GitHub or Cloudflare usage APIs, per-key quotas, alerting integrations (the operator's Cloudflare billing notifications are step S19), retroactive accounting of operations before this chapter, a UI to edit caps (they are Render variables, step S21).
