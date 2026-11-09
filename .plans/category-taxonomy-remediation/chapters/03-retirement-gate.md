---
id: C3
depends_on:
  - C2
touches:
  - apps/api/alembic/versions/20261105_retire_legacy_taxonomy.py
  - apps/api/scripts/legacy_taxonomy_archive.py
  - apps/api/scripts/retirement_preflight.py
  - apps/api/tests/test_legacy_taxonomy_migration.py
execution: chapter-implementer
todos:
  - ch03-retirement-gate
---

# Chapter 3 — Retirement migration gate (H1)

**Suite:** [README](README.md) · **Architecture:** [../00-architecture.md](../00-architecture.md) · **Rollout:** [../01-rollout.md](../01-rollout.md) · **Ledger:** [../run-ledger.md](../run-ledger.md)
**Decisions:** D-R1 in [../gaps-and-decisions.md](../gaps-and-decisions.md)

**Batch:** B3 · **Execution:** chapter-implementer · **Status:** planned

## Goal

Make the destructive retirement migration verifiable. Before any legacy table is dropped, the migration must prove that the archive equals the source, and that the backfill has no unmapped, ambiguous, or conflict rows. The free tier has no backups, so this proof is the recovery model (D-R1).

## Boundaries

- `depends_on`: C2.
- `touches`: `20261105_retire_legacy_taxonomy.py`, `legacy_taxonomy_archive.py`, `retirement_preflight.py` (new), `test_legacy_taxonomy_migration.py` (new).
- The pre-retirement revision is `20261104_category_taxonomy_backfill`. The retirement revision is `20261105_retire_legacy_taxonomy`.
- Do not change the contract artifact or the completeness code.

## Parts

1. **Preflight script** (`retirement_preflight.py`): a read-only transaction. It prints per-table row counts, content checksums, mention axis counts, and the backfill dry-run report (unmapped, ambiguous, conflict, null confidence). Chapter 13 runs it against production.
2. **Migration verification:** after the archive copy, compare each archived table with its source by count and checksum, inside the same transaction. Abort on any mismatch.
3. **Backfill gate:** run the backfill and log the full report. Abort if unmapped, ambiguous, or conflict rows are above zero.
4. **Downgrade shape:** the downgrade recreates the empty schema, as today. The test pins that shape.

## Red

- **Happy path:** a seeded database at `20261104_category_taxonomy_backfill` upgrades to head. Every legacy row is archived, the projection is written, the legacy tables are dropped, and the archive equals the source by count and checksum.
- **Negative path (two cases):**
  - an unmapped legacy code aborts the migration and leaves the legacy tables in place;
  - an injected checksum mismatch in the archive aborts the migration and leaves the legacy tables in place.

Confirm both negative cases fail for the right reason: the migration must abort, not pass silently.

## Green

- Implement the in-transaction verification and the report logging.
- The abort path rolls back the transaction, so legacy tables stay.

## Refactor

- Extract `_verify_archive` from the migration body.
- The migration body is a short sequence of named steps: archive, verify, backfill, gate, drop, project.
- Refactor audit: the whole migration module and `legacy_taxonomy_archive.py`. Check that the table list is defined once.
- Re-run the migration test after each extraction.

## Gate

- Backend: `uv run pytest tests/test_legacy_taxonomy_migration.py` in `apps/api`.
- Run only on disposable databases. The local `redtape` database is already at head, so it must not be used for upgrade tests.
- Then `./ci.sh`.
- Record results in [the ledger](../run-ledger.md).
- Corporate build block: [corporate-build-env.md](../../../.cursor/skills/chief-of-staff/corporate-build-env.md).

## Notes

- C10 uses this test file in its reference scan allowlist. The allowlist entry is valid only after this chapter creates the file.
- No `pg_dump` requirement. The archive plus checksum is the recovery model (D-R1).
