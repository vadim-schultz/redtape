---
id: C14
depends_on:
  - C13
touches:
  - .plans/category-taxonomy-remediation/run-ledger.md
execution: chief-of-staff
todos:
  - ch14-release-gate
---

# Chapter 14 — Release gate and PR (live)

**Suite:** [README](README.md) · **Architecture:** [../00-architecture.md](../00-architecture.md) · **Rollout:** [../01-rollout.md](../01-rollout.md) · **Ledger:** [../run-ledger.md](../run-ledger.md)
**Release PR:** [PR 370](https://github.com/vadim-schultz/redtape/pull/370)

**Batch:** B7 · **Execution:** chief-of-staff · **Status:** planned

## Goal

Release the loop branch to `main` through PR 370, once every chapter is integrated and production has been checked. Confirm that merging triggers no deploy. Merge only after the user approves.

This is a release step for the chief of staff. No implementer runs it.

## Boundaries

- `execution`: chief-of-staff.
- `touches`: the ledger, and PR 370 (updated, not a file change).
- Do not force-push, skip hooks, or amend a pushed commit.
- Do not merge without explicit user approval.

## Checks

1. `./ci.sh` on `feat/plans-category-taxonomy-migration` exits 0 from the repository root. Record the run.
2. PR 370 targets `main` and is updated as the release PR. Record its description, which lists the chapters.
3. Confirm that merging to `main` triggers no deploy. This repository has no deploy workflow. Check the external GitOps path, and record what it watches and what it deploys.
4. Confirm that C13 passed or that its blocks are resolved by the user.
5. Get explicit user approval to merge. Record the approval.
6. Merge, then record the merge commit and the release in the ledger.

## Pass and block rules

- **Pass:** `./ci.sh` is green, no deploy triggers on merge, C13 passed, and the user approved the merge.
- **Block:** any red CI check, an unexplained deploy path, an unresolved C13 block, or no user approval. Do not merge.

## Red and green (as evidence)

- **Happy path (pass):** every pass rule above is met, and the release is recorded.
- **Negative path (block):** any block rule applies. The merge does not happen, and the ledger records the reason.

## Gate

- The live-gate checklist for C14 in [../run-ledger.md](../run-ledger.md) is complete.
- The release is recorded with the merge commit, or the block is recorded with its reason.

## Notes

- PR 370 is the release PR, so C14 updates it. Chapter PRs merge into the loop branch, not into `main`.
- C0 fixes the failing test that blocks PR 370 CI. Confirm that C0 is integrated before C14 runs.
