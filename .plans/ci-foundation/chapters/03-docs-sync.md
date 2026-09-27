---
name: "Chapter 3 — Docs sync"
overview: "Record the Postgres-backed CI and migration check as shipped, correct the SQLite statements in the planning docs, and register the suite in .plans/README.md."
todos:
  - id: status
    content: "docs/planning/STATUS.md: remove the silent-skip caveat, add a dated line"
    status: completed
  - id: ops
    content: "docs/operations/local-development.md: test and REQUIRE_DB notes"
    status: completed
  - id: plans
    content: "Flip rollout and chapter statuses; index in .plans/README.md"
    status: completed
isProject: false
---

# Chapter 3 — Docs sync

**Repo:** `redtape` (docs only) · **Branch:** `docs/ci-foundation-sync` · **Status:** done

**Depends on:** [1](01-postgres-in-ci.md), [2](02-migration-roundtrip-job.md) · **Architecture:** [../00-architecture.md](../00-architecture.md) · **Rollout:** [../01-rollout.md](../01-rollout.md)

---

## Goal

Planning docs match the shipped CI. Same shape as
[floating-nav chapter 6](../../floating-nav/chapters/06-docs-sync.md).

## Design decisions

- Rollout rows and chapter meta lines in this folder flip to `shipped`.
- [docs/planning/STATUS.md](../../../docs/planning/STATUS.md): delete the note that DB-backed tests likely
  skip silently in CI; add a dated update line.
- [docs/operations/local-development.md](../../../docs/operations/local-development.md): how to run the
  tests (`docker compose up -d --wait db`, `REQUIRE_DB=1`) and how to run `check_migrations.sh`.
- `.plans/README.md`: keep the `ci-foundation` entry's Status line current.

## Files

**Edit** — `.plans/README.md`, `.plans/ci-foundation/01-rollout.md` and chapters,
`docs/planning/STATUS.md`, `docs/operations/local-development.md`.

## Red tests

| Check | Asserts |
| --- | --- |
| Link check | Every relative link in edited files resolves to an existing file |
| Status grep | No doc still claims API tests run on SQLite or skip silently in CI |

## Green

Edit docs; run a link-check script over `.plans/` and `docs/`.

## Refactor gate

Docs only; nothing to gate beyond the link check.

## Verification

Link check; `git diff --stat` shows docs only.

## Out of scope

Code changes.

## Git workflow

Branch `docs/ci-foundation-sync`; `docs(planning): record Postgres CI and migration check as shipped`; one PR.

## Outcome

- `docs/planning/STATUS.md`: removed the "likely skips silently in CI" follow-up (fixed by chapters 1–2),
  added a dated 2026-09-27 entry describing the shipped Postgres CI and migration check, bumped "Last
  updated."
- `docs/operations/local-development.md`: added a "Checking migrations" section documenting
  `scripts/check_migrations.sh`, its four checks, and why it needs a database separate from the pytest one.
  The test-suite section already covered `REQUIRE_DB`/`docker compose up -d --wait db` from chapter 1, so no
  change was needed there.
- `.plans/ci-foundation/01-rollout.md` and this chapter flipped to `done`; `.plans/README.md`'s
  `ci-foundation` entry now reads "shipped."
- Link check: every relative link in the five edited files resolves; `git diff --stat` touches only docs.
