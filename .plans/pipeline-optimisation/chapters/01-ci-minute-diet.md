---
name: "Chapter 1 — CI minute diet and real-minute reconciliation"
overview: "Measure what CI really bills, then cut the minutes that CI spends on drafts, duplicate pushes and cold caches, so the drain budget can be sized from data."
todos:
  - id: measure
    content: "Add a read-only script that sums billable minutes per workflow from GitHub run timing"
    status: pending
  - id: cache
    content: "Cache pip, uv and npm downloads; skip API CI on draft pull requests"
    status: pending
  - id: migrations
    content: "Run the migration round trip only when alembic or its check script changed"
    status: pending
  - id: record
    content: "Record the measured minutes and the operator's pool figure in the run ledger"
    status: pending
isProject: false
---

# Chapter 1 — CI minute diet and real-minute reconciliation

**Repo:** `redtape` · **Branch:** `feat/pipeline-optimisation-ci-minute-diet` · **Status:** planned
**Depends on:** none · **Decisions:** D1 · **Architecture:** [../00-architecture.md](../00-architecture.md) (section 2.4, waste 11)

**Loop branch:** `feat/plans-pipeline-optimisation` · **Release branch:** `main`

## Goal

CI is the largest consumer of the 2,000-minute pool, and the ledger does not see it. Measure what CI bills, then cut the avoidable part, so the drain budget that chapter 12 derives is based on measured use.

## Design

- **Measure first.** `scripts/gha_minutes.py` (standard library only) reads `gh run list --json` and `gh api repos/{owner}/{repo}/actions/runs/{id}/timing` for a `--since` date, and prints billable minutes per workflow. Each job rounds up to a whole minute, as GitHub bills it. Read-only; it needs the operator's `gh` session.
- **Drafts.** `api-lint-test.yml` and `web-ci.yml` skip draft pull requests, with `if: github.event.pull_request.draft == false` on the job.
- **Duplicate pushes.** Keep the push-to-`main` run, because the release relies on it. Confirm that superseded pull request runs are cancelled (they are, by the existing `concurrency` block, and the check must stay).
- **Caches.** `actions/cache` for the pip wheel cache in `api-lint-test.yml` (keyed on `apps/api/uv.lock`), and the `actions/setup-node` npm cache in `web-ci.yml`. Cache keys include the lock file hash.
- **Migrations.** The `migrations` job in `api-lint-test.yml` runs only when `apps/api/alembic/**` or `apps/api/scripts/check_migrations.sh` changed. A small first job reports the change set; `migrations` depends on it.
- **No parallel tests.** Do not add `pytest-xdist`. The API suite shares one `REQUIRE_DB` database, so workers would collide.

## Files

**Edit**

- `.github/workflows/api-lint-test.yml`
- `.github/workflows/web-ci.yml`
- `.github/workflows/discovery-ingest-ci.yml`
- `docs/operations/gha-budget.md` (the measured table, and the drift rows listed in chapter 15)

**Create**

- `scripts/gha_minutes.py`
- `scripts/tests/test_gha_minutes.py`

**Do not edit**

- Any `apps/api` or `apps/web` application code.

## Red tests

| Test | Asserts |
| --- | --- |
| `gha_minutes rounds each job up to a whole minute` | Happy: 61 s bills 2 minutes. Negative: 0 ms bills 0, not 1. |
| `gha_minutes sums billable minutes per workflow over a date range` | Happy: two runs of one workflow add up; runs outside `--since` are excluded. |
| `draft pull requests run no API job` | Negative: the job condition is false for `draft: true`. |
| `the migrations job runs only when alembic or the check script changed` | Happy and negative: the change-set job output decides. |

## Green

1. Write `gha_minutes.py` and its tests, with the `gh` call behind one function so the tests use a recorded response.
2. Add the draft condition and the migrations gating to `api-lint-test.yml`. Add the caches.
3. Run `actionlint` and a YAML parse on every changed workflow.

## Refactor gate

Audit the workflow files for duplicated setup steps. If the two Python jobs share the same setup block, extract it to a composite action under `.github/actions/`. Audit `gha_minutes.py` for functions over about five lines.

## Verification

```bash
python -m pytest scripts/tests -q
actionlint .github/workflows/api-lint-test.yml .github/workflows/web-ci.yml .github/workflows/discovery-ingest-ci.yml
./ci.sh
```

Live gate: over the next five pull requests, compare the billed minutes per run with the October figures in `gha-budget.md`. Record the before and after in the run ledger, together with the operator's pool figure (operator step S1).

## Commits

`test(scripts): define the billable-minutes report`, `feat(scripts): report billable Actions minutes per workflow`, `ci: skip API CI on draft pull requests`, `ci: cache Python and Node downloads in the CI workflows`, `ci: run the migration round trip only when migrations change`.

## Out of scope

Parallel test execution, self-hosted runners, changing the cancellation behaviour of pull request runs, and any change to the drain workflows (chapter 12).

## Git workflow

```bash
git checkout feat/plans-pipeline-optimisation && git pull
git checkout -b feat/pipeline-optimisation-ci-minute-diet
```

Open the chapter PR into `feat/plans-pipeline-optimisation`.
