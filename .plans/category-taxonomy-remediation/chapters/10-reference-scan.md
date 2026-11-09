---
id: C10
depends_on:
  - C3
  - C7
touches:
  - apps/api/tests/test_legacy_reference_scan.py
execution: chapter-implementer
todos:
  - ch10-reference-scan
---

# Chapter 10 — Reference scan and gates (M5)

**Suite:** [README](README.md) · **Architecture:** [../00-architecture.md](../00-architecture.md) · **Rollout:** [../01-rollout.md](../01-rollout.md) · **Ledger:** [../run-ledger.md](../run-ledger.md)

**Batch:** B4 · **Execution:** chapter-implementer · **Status:** planned

## Goal

The legacy reference scan currently covers the API only and exempts whole files. It misses `apps/discovery-ingest` and active docs. Widen the scan, replace whole-file exemptions with reasoned line allowances, and make the scan fail on an allowlist entry that names a file that does not exist.

## Boundaries

- `depends_on`: C3 (creates the migration test file that the allowlist names) and C7 (removes the ingest legacy code).
- `touches`: `apps/api/tests/test_legacy_reference_scan.py`.
- Do not change the legacy code to satisfy the scan, except where a hit is a real remaining reference. Those hits are fixed in their own chapter or recorded here with a reason.

## Scope to confirm in the red step

Record the scan scope in the ledger row before red. Proposed scope:

- Code: `apps/api/**` and `apps/discovery-ingest/**`, excluding generated files.
- Active docs: `docs/**` and `apps/*/README.md`.
- Excluded: `.plans/**`, which records history. Stale claims there are C12's job.

## Red

- **Happy path:** the widened scan runs over the scope above. It fails on the known remaining hits. Record each hit in the ledger row before fixing it.
- **Negative path:** a planted legacy identifier in a temporary file under the scanned scope fails the scan with the file name and line. The temporary file is removed after the test.
- **Also:** an allowlist entry that names a missing file fails the scan. This catches the `test_legacy_taxonomy_migration.py` entry before C3 creates it, and any future stale entry.

## Green

- Fix each real remaining hit, or allow a single line with a reason. The reason is a required field.
- Replace the whole-file exemptions with line-level allowances.

## Refactor

- A data-driven allowlist. Each entry has a path, a line matcher, and a reason. The scan reads the list from one place.
- Refactor audit: the whole scan test module, because the exemption logic lives in one place and must not branch per file.

## Gate

- Backend: in `apps/api`, `uv run pytest tests/test_legacy_reference_scan.py`, plus ruff and mypy.
- Then `./ci.sh`.
- Record each allowlist entry with its reason in [the ledger](../run-ledger.md).
- Corporate build block: [corporate-build-env.md](../../../.cursor/skills/chief-of-staff/corporate-build-env.md).

## Notes

- This chapter runs after C7. Running it earlier would flag the ingest legacy code that C7 removes.
- The scan must not depend on the developer's `redtape` database.
