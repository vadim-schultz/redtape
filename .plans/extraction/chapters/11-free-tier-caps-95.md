---
name: "Chapter E11 — Free-tier caps at 95 percent"
overview: "Raise the internal soft caps on R2 bytes and operations, Browser Run seconds, Workers AI neurons and the database from their conservative defaults to 95 percent of each free allowance, in one table-driven change with a guard test, and leave the shared GitHub Actions budget alone."
todos:
  - id: defaults
    content: "Settings defaults, CLI and workflow browser default, and the tests that pin the old numbers"
    status: pending
  - id: guard
    content: "One table test: every cap is at most 95 percent of its allowance and the allowances are written down once"
    status: pending
  - id: docs
    content: "Runbooks, README and the extraction plan numbers say the same values"
    status: pending
  - id: operator
    content: "Operator removes or updates Render overrides and verifies the new caps on the budgets route"
    status: pending
isProject: false
---

# Chapter E11 — Free-tier caps at 95 percent

**Repo:** `redtape` (`apps/api`, `apps/discovery-ingest`, `.github/workflows`, `docs/operations`) · **Branch:** `chore/extraction-free-tier-caps` · **Status:** planned

**Depends on:** crawlers [23](../../crawlers/chapters/23-free-tier-guards.md) (the ledger and the settings, merged) · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/extraction`

**Order:** executes **first**, together with [E10](10-robots-rules-fix.md); it is configuration only and independent of E1 to E9. The extraction suite is the first heavy user of the neuron cap, so the cap is settled before any live gate spends it.

## Goal

The owner's decision (2026-10-28): the internal soft caps sit too far below the free allowances. They become **95 percent of each allowance**, so a day of crawling uses the free tier almost fully and the application still stops before the provider does. Nothing about how a cap is enforced changes; only the numbers and the places that print them.

### Where the numbers stand today

The caps were not uniformly 80 percent. Measured against the allowance each one guards:

| Resource | Free allowance | Setting (today) | Share today | New value | New share |
| --- | --- | --- | --- | --- | --- |
| Stored artifact bytes | 10 GB-month | `object_store_max_bytes` = 8 GiB (8,589,934,592) | 86 percent | **9,500,000,000** | 95 percent |
| R2 Class A operations | 1,000,000 a month | `budget_r2_class_a_monthly` = 400,000 | 40 percent | **950,000** | 95 percent |
| R2 Class B operations | 10,000,000 a month | `budget_r2_class_b_monthly` = 4,000,000 | 40 percent | **9,500,000** | 95 percent |
| Browser Run seconds | 600 a day | `budget_browser_seconds_daily` = 480 | 80 percent | **570** | 95 percent |
| Workers AI neurons | 10,000 a day | `budget_neurons_daily` = 8,000 | 80 percent | **9,500** | 95 percent |
| Database size | 500 MB (read-only above) | `db_soft_limit_bytes` = 400,000,000 | 80 percent | **475,000,000** | 95 percent |

All six move to 95 percent. Three of them (the two R2 operation caps, and the bytes cap's GiB-against-GB mix) were never at 80 percent, which is why this chapter writes the allowances down once and tests the ratio instead of repeating "80".

### Deliberately unchanged

- **GitHub Actions minutes** (`budget_actions_minutes_monthly` = 1,000, `actions_ci_reserve_minutes` = 600). The 2,000 free minutes are **shared by every repository on the account**, so this repository's 1,000 is its share and not a fraction of "available usage". Raising it to 95 percent of 2,000 would take minutes from other repositories and from CI. The cap stays a repository share; changing it is a separate decision.
- **The 80 percent warning chip** in the admin ([`nearsStorageCap.ts`](../../../apps/web/src/features/discovery-admin/utils/nearsStorageCap.ts)) is an alert, not a limit, and measures against the cap. It stays at 80 percent of the cap, which is now 76 percent of the allowance; changing the alert is a separate decision.
- **Per-run budgets** such as `--neuron-budget 4000` in the live-gate commands of E4, E5 and E7, and the run wall-clock budgets. Those are deliberately small and are not caps.

## Contract

1. **Settings** ([`apps/api/app/config.py`](../../../apps/api/app/config.py)): new defaults from the table above, with each description naming the allowance and the 95 percent rule. No new setting, no new environment variable.
2. **Browser default at the edges.** `--browser-budget-seconds` in [`cli/worker/commands.py`](../../../apps/discovery-ingest/discovery_ingest/cli/worker/commands.py), the `browser_budget_seconds` default and fallback in [`discovery-render.yml`](../../../.github/workflows/discovery-render.yml), and the README table become **570**. The run budget is still capped by the ledger's remaining seconds, so the ledger stays the authority.
3. **One place for the allowances.** A small module constant (or a documented block in the settings tests) lists the six allowances; the guard test derives the ratio from it. The runtime does not read it; it exists so a future allowance change is a one-line edit with a failing test pointing at it.
4. **Docs print the same numbers**, taken from the settings: the operator checklist (S8, S21), the post-deploy steps, `discovery-online.md`, `deployment-checklist.md`, `scheduled-jobs.md`, `gha-budget.md` where it cites Cloudflare numbers, the ingest README, and the extraction plan's own figures (`00-architecture.md`, `chapters/09`, `gaps-and-decisions.md`). The merged crawlers plan files are history and stay as written; the crawlers ledger gets a one-line pointer.
5. **No change to the guards' behaviour.** Reserve-then-adjust, release-not-fail, the 507 on the byte cap and the database soft limit, and the fail-open reads all stay as built in crawlers chapter 23.

## Risks the owner accepted

Recorded so a surprise later has a name. A 5 percent margin is thin where the application's count can differ from the provider's.

| Risk | Why it is thinner now | Mitigation kept |
| --- | --- | --- |
| Browser seconds: 570 of 600 | Probes and manual calls are not in the ledger (about 26 s went on probing on 2026-10-27), and the dashboard may count a little differently | A provider `429` still releases tasks; the operator checks Browser Run usage in the Cloudflare dashboard monthly |
| Neurons: 9,500 of 10,000 | A model call is reserved before it runs, but the real cost can differ from the estimate, and the Workers AI playground or other tools on the account draw on the same allowance | Reserve-then-adjust; a provider quota error marks the day exhausted and releases tasks |
| R2 operations and bytes | R2 **bills** past the free tier; the margin is now 5 percent of the allowance | The billing notification (crawlers S19) is the guard that sees what the application cannot; keep it |
| Database: 475 MB of 500 MB | `pg_database_size` is the whole database including tables the application does not own, indexes, and growth between the cached reads (five minutes); Supabase goes read-only at 500 MB | The soft limit answers 507 on writes; the admin shows the size; prune before a backfill such as a full catalogue re-ingest (the 2026-10-28 PVOG re-ingest added about 770 rows) |

## TDD loops

### Loop A — Defaults

**Red** (`apps/api/tests`, edit the tests that pin the old numbers, then add the guard)

1. `test_config_object_store.py`: `object_store_max_bytes == 9_500_000_000`.
2. `test_db_headroom.py`: `db_soft_limit_bytes == 475_000_000`.
3. `test_discovery_budgets.py` and `test_discovery_budgets_api.py`: the cap and `remaining` expectations for neurons (9,500), Class A (950,000) and the byte cap in `stored_bytes_cap`; the exhausted-day test still exhausts at the new cap.
4. `test_budget_caps_ratio.py` (new, table-driven): for each of the six resources, `cap <= 0.95 * allowance` and `cap >= 0.90 * allowance` (so an accidental drop back to a conservative value also fails); `actions_minutes` is asserted unchanged at 1,000 with a message saying why.
5. `an environment override still wins over the default` — negative guard that tuning down through Render variables keeps working.

**Green:** change the defaults in `config.py`. **Refactor:** descriptions generated from nothing; plain text naming allowance and rule; no new abstraction.

### Loop B — Browser default at the edges

**Red** (`apps/discovery-ingest/tests`)

1. `the drain cli default browser budget is 570` (parser default).
2. `a run budget above the ledger's remaining seconds is still capped by the ledger` — regression guard that the ledger stays the authority.
3. `the render workflow default is 570` — a text test over the workflow file, in the style of the existing workflow contract tests.

**Green:** the three defaults. **Refactor:** none expected.

### Loop C — Docs say the same numbers

**Red** (`apps/api/tests/test_discovery_operations_runbook.py`, extend the existing contract test)

1. `the operator checklist and the runbooks print the six new caps` (substring checks, one per cap).
2. `no runbook still prints the old caps as defaults` (negative: 480 as the browser default, 8,000 as the neuron default, 400 MB as the soft limit, 8 GiB as the byte cap).

**Green:** edit the documents listed in the contract. **Refactor:** none.

## Verification

```bash
cd apps/api && python -m pytest tests/test_config_object_store.py tests/test_db_headroom.py tests/test_discovery_budgets.py tests/test_discovery_budgets_api.py tests/test_budget_caps_ratio.py tests/test_discovery_operations_runbook.py && ruff check . && mypy app
cd apps/discovery-ingest && python -m pytest tests/test_budget_guard.py tests/test_render_worker.py && ruff check . && mypy discovery_ingest
gh pr checks --watch
```

**Live gate (operator, after the API redeploys on Render).**

1. Render, `redtape-api`, Environment: check whether any of `OBJECT_STORE_MAX_BYTES`, `BUDGET_R2_CLASS_A_MONTHLY`, `BUDGET_R2_CLASS_B_MONTHLY`, `BUDGET_BROWSER_SECONDS_DAILY`, `BUDGET_NEURONS_DAILY` or `DB_SOFT_LIMIT_BYTES` is set explicitly. An explicit value beats the new default, so delete it or set the new number.
2. Check the result with the machine API key:

```bash
curl -s -H "X-API-Key: $DISCOVERY_API_KEY" "$DISCOVERY_API_URL/api/v1/discovery/machine/budgets"          # caps 950000, 9500000, 570, 9500, and actions_minutes 1000
curl -s -H "X-API-Key: $DISCOVERY_API_KEY" "$DISCOVERY_API_URL/api/v1/discovery/machine/artifacts/status" # bytes_cap 9500000000
```

3. Check the database size against the new soft limit and note the headroom in the [run ledger](../run-ledger.md):

```sql
select pg_size_pretty(pg_database_size(current_database())) as db_size;
```

Record the date, the values returned and any override you removed.

## Out of scope

Changing the GitHub Actions budget or the CI reserve, moving the admin warning threshold, changing per-run budgets, the guards' reserve and release behaviour, rewriting the merged crawlers plan files, and paid plans.
