---
id: C13
depends_on:
  - C10
  - C11
  - C12
touches:
  - .plans/category-taxonomy-remediation/run-ledger.md
execution: chief-of-staff
todos:
  - ch13-production-preflight
---

# Chapter 13 — Production preflight (live, read-only)

**Suite:** [README](README.md) · **Architecture:** [../00-architecture.md](../00-architecture.md) · **Rollout:** [../01-rollout.md](../01-rollout.md) · **Ledger:** [../run-ledger.md](../run-ledger.md)
**Decisions:** D-R1 in [../gaps-and-decisions.md](../gaps-and-decisions.md)

**Batch:** B6 · **Execution:** chief-of-staff · **Status:** planned

## Goal

Measure production before the retirement migration reaches it. Record the counts, checksums, dry-run report, and migration revision. Confirm that no unexplained rows block the release.

This is live, read-only work for the chief of staff. No implementer runs it.

## Boundaries

- `execution`: chief-of-staff.
- `touches`: the ledger only.
- **No writes.** Do not run a migration, a backfill, or a promotion against production.
- **No `pg_dump`.** The free tier has no backups. The archive plus checksum is the recovery model (D-R1).

## Checks

1. Run `retirement_preflight` read-only against production, using the release candidate build. Record the output.
2. Record the production alembic revision. Expected: the revision before `20261105_retire_legacy_taxonomy`.
3. Record per-table row counts and checksums for every legacy table.
4. Record the backfill dry-run report: unmapped, ambiguous, conflict, and null-confidence counts.
5. Record whether any promotion ran after C2 was integrated. If one did, record it as the M1 trigger and check the promotion-written `document_category` rows against the preflight counts and confidence values.
6. Record the archive owner and drop date supplied by the user. If they are not supplied, record them as open.

## Pass and block rules

- **Pass:** unmapped, ambiguous, and conflict counts are all zero. The archive owner and drop date are recorded. The M1 check (if triggered) passes.
- **Block:** any non-zero unmapped, ambiguous, or conflict count blocks C14 until the user decides. Record the decision in [../gaps-and-decisions.md](../gaps-and-decisions.md).

## Red and green (as evidence)

- **Happy path (pass):** the preflight runs read-only and every rule above is met. Record the run in the ledger.
- **Negative path (block):** any count is non-zero, or the revision is unexpected. C14 is blocked and the ledger says why.

## Gate

- The baseline table in [../run-ledger.md](../run-ledger.md) has a recorded value for every row.
- The live-gate checklist for C13 is checked, or each unchecked item is explained.
- C14 does not start while the block rule applies.

## Notes

- This chapter is the first place production is read. It runs after C12, so the release candidate is final.
- The preflight script comes from C3. Running it here does not change production.
