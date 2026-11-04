---
name: "Chapter 3 — Evidence and operations"
overview: "Record integrated remediation evidence, update the ledgers honestly, and hand off the operator-only C8 cleanup without changing application code."
id: C3
depends_on:
  - C1
  - C2
touches:
  - .plans/codebase-audit-remediation/post-implementation-review.md
  - .plans/codebase-audit-remediation/run-ledger.md
  - .plans/codebase-audit-remediation/gaps-and-decisions.md
  - .plans/codebase-audit/run-ledger.md
execution: chief-of-staff
todos:
  - id: integrated-report
    content: "Write the final post-implementation report from integrated chapter evidence."
    status: pending
  - id: remediation-ledger
    content: "Fill the remediation ledger with PR, test, refactor, and CI evidence."
    status: pending
  - id: parent-handoff
    content: "Cross-link the parent audit's remaining exceptions without claiming unverified closure."
    status: pending
  - id: c8-handoff
    content: "Record the dry-run, approved apply, and endpoint verification procedure for C8."
    status: pending
isProject: false
---

# Chapter 3 — Evidence and operations

**Repo:** `redtape` · **Branch:** `docs/audit-remediation-evidence` · **Status:** planned  
**Depends on:** chapters 1 and 2 · **Architecture:** [../00-architecture.md](../00-architecture.md) · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/plans-codebase-audit-remediation` · **Release branch:** `main`

## Goal

Publish the integrated post-review report, complete the remediation ledger, and make the remaining
parent T3/G2 exceptions and C8 operator gate explicit. This chapter does not change `apps/`,
workflows, production configuration, or production data.

## Design decisions

- The report is narrative evidence; the ledger is the authoritative row-by-row tracking surface.
- A parent audit chapter without verifiable evidence remains planned, deferred, or partial. Do not
  mark it done because a follow-up chapter fixed one seam.
- C8 is closed only after the operator performs the dry run, approves the apply, and records the
  post-apply read-only endpoint checks.
- No production mutation is performed from this chapter.

## Files

| Path | Change |
| --- | --- |
| `post-implementation-review.md` | Update with integrated chapter evidence and final limitations. |
| `run-ledger.md` | Record branches/PRs, red → green evidence, refactor outcomes, CI, and C8 status. |
| `../codebase-audit/run-ledger.md` | Add a cross-reference only when the parent evidence can be verified. |
| `gaps-and-decisions.md` | Resolve or carry forward open decisions with owner and rationale. |

Do not edit any path under `apps/`, `.github/`, or `ci.sh`.

## Red acceptance checks

- Happy: chapters 1 and 2 have merged PR links, named tests, refactor outcomes, and CI evidence.
- Negative: the report refuses to claim a fix when the named regression test is absent or red.
- Happy: the ledger has a C8 operator row with the dry-run, apply, and endpoint-check fields.
- Negative: C8 remains blocked when only the cleanup script exists and no operator evidence is
  recorded.
- Happy: the chapter branch contains only plan/docs changes.
- Negative: any `apps/` diff fails the docs-only chapter review.

## Green

1. Copy verified chapter evidence into the report without copying unverified assumptions.
2. Fill the remediation ledger and cross-link, rather than rewrite, the parent audit ledger.
3. Record T3/G2 permanent exceptions with rationale and owner.
4. Record the operator procedure and leave the C8 row blocked until evidence exists.

## Refactor gate

Audit the documentation entities:

- the report contains findings and narrative, not a second ledger table;
- the ledger contains evidence rows, not duplicated prose from the report;
- each open decision has one owner and one next action;
- no docs-only section claims a runtime or production result it did not verify.

Report `Refactor gate: smells found -> duplicated report/ledger evidence, if any; refactorings
applied -> ...` or explicitly state that no documentation refactor was needed.

## Verification

```bash
git diff --name-only main...HEAD
rg '^apps/' <(git diff --name-only main...HEAD) && exit 1 || true
rg 'planned|blocked|merged|deferred' post-implementation-review.md run-ledger.md
```

Run the full `./ci.sh` gate on the integrated loop branch before release; this docs-only chapter
does not substitute for that gate.

## Operator handoff — C8

The chief of staff coordinates the operator-owned sequence:

1. Run `python -m scripts.remove_leaked_fixture_jurisdictions` in dry-run mode.
2. Inspect all reported references.
3. Obtain approval and run the same command with `--apply`.
4. Verify `GET /api/v1/districts?state=14` has 13 real districts and no `Kreis Beispiel`.
5. Verify `GET /api/v1/cities?district=146` has no `Musterstadt`.
6. Record timestamps, result summaries, and any references in [run-ledger.md](../run-ledger.md).

Implementers do not run step 3.

## Out of scope

Application fixes, workflow changes, production cleanup, a full parent-audit rerun, and opening the
release PR.

## Git workflow

```bash
git checkout feat/plans-codebase-audit-remediation && git pull
git checkout -b docs/audit-remediation-evidence
```

Use `docs(plans): ...` conventional commits. Open the chapter PR into the remediation loop branch,
not `main`.

