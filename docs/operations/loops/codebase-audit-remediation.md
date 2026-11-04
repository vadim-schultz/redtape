# Codebase audit remediation (chief of staff)

Close the verified seams left after the parent [codebase-audit](../../../.plans/codebase-audit/)
suite merged to `main`: emit-batch rollback, admin loading announcements, ingest zero-bound
validation, slipped web refactors, and the evidence/C8 handoff.

Plan suite: [`.plans/codebase-audit-remediation/`](../../../.plans/codebase-audit-remediation/) on
`main`.

**Loop branch:** `feat/plans-codebase-audit-remediation`  
**Release branch:** `main`

**Prerequisite:** parent `codebase-audit` is integrated at or before `95a3615`.

## How to run

1. Confirm the plan suite is on `main`.
2. Bootstrap the loop branch using the chief-of-staff git model.
3. Launch chief of staff with plan folder `.plans/codebase-audit-remediation/`.
4. Run chapters 1 and 2 in parallel when worktree and test capacity allow; chapter 3 waits for
   both.
5. Keep C8 operator-owned: dry-run, approved apply, and read-only endpoint checks are recorded in
   the remediation ledger.
6. Open the release PR from the loop branch to `main` only after the ledger and `./ci.sh` gate are
   complete.

## Status

Planned — three chapters. C8 is blocked until the operator records production evidence.

## Exit criteria

- The emit-batch regression preserves earlier inserts after a uniqueness race.
- Both drill-down pages announce loading and `--max-tasks 0` exits with usage failure.
- Query options and `CompletenessChips` each have one source of truth.
- T3/G2 exceptions and parent hand-off status are explicit in the ledgers.
- C8 is either verified after operator cleanup or explicitly carried forward.
- `./ci.sh` is green on the loop branch.

