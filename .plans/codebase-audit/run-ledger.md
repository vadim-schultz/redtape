---
name: Codebase audit — Run ledger
overview: "Per-chapter evidence: branch and PR, red to green, refactor outcome, CI, status. Filled in by the chief of staff as chapters merge."
isProject: false
---

# Codebase audit — Run ledger

**Loop branch:** `feat/plans-codebase-audit`
**Release branch:** `main`
**Release PR:** _(filled when opened)_

Chapter PRs merge into the loop branch only. The chapter implementer does not edit this file; the chief of staff does.

| Chapter | Branch / PR | Red → green evidence | Refactor outcome | CI / smoke | Status |
| --- | --- | --- | --- | --- | --- |
| T1 step 1. pydocstyle config | | | | | planned |
| T1 step 2. docstring slices | | | | | planned |
| T2. Any gate | | | | | planned |
| T3. Architecture guards | | | | | planned |
| A1. Vote and promotion errors | | | | | planned |
| A2. Single emit pipeline | | | | | planned |
| A3. Ingest run lifecycle | | | | | planned |
| A4. Lifespan locale load | | | | | planned |
| B1. Locale and i18n | | | | | planned |
| B2. Suggestion core | | | | | planned |
| B3. Layering and guards | | | | | planned |
| B4. Discovery performance | | | | | planned |
| B5. List query params | | | | | planned |
| B6. OpenPLZ typing | | | | | planned |
| B7. Stored normalised URL (optional) | | | | | planned |
| I1. Ingest client facade | | | | | planned |
| I2. Ingest typing | | | | | planned |
| I3. Ingest operations layer | | | | | planned |
| I4. Ingest Typer CLI | | | | | planned |
| I5. API and ingest contract | | | | | planned |
| W1. Admin query plumbing | | | | | planned |
| W2. Shared UI blocks | | | | | planned |
| W3. Boundary types | | | | | planned |
| W4. Admin containers | | | | | planned |
| G1. Test gaps | | | | | planned |
| G2. Close baselines | | | | | planned |

## Remediation follow-up

The post-merge remediation suite is tracked separately in
[`.plans/codebase-audit-remediation/run-ledger.md`](../codebase-audit-remediation/run-ledger.md).
Its Chapters 1 and 2 are locally integrated on 2026-11-04 and close verified follow-up seams R1–R5
from the remediation review. This cross-reference does not mark any parent chapter complete:
parent T3/G2 evidence and the remaining parent release gates are still planned until their own
evidence is recorded.

## Baseline at audit time (2026-11-02, `main` at `0e713cc`)

| Measure | `apps/api` (app + scripts) | `apps/discovery-ingest` |
| --- | --- | --- |
| Classes over 100 lines (informational) | 7 + 1 | 2 |
| Methods over 5 lines (informational) | 444 + 72 | 409 |
| Parameters over 3 | 38 + 10 | 47 |
| `D` violations | 367 | 28 |
| `Any` annotations | 21 | 67 |

## Release gate

- [ ] All chapters recorded with red to green evidence and refactor outcome.
- [ ] `D` and `ANN401` baselines are empty in `apps/api` and `apps/discovery-ingest`.
- [ ] `./ci.sh` passes on the loop branch.
- [ ] `.github/workflows/discovery-*.yml` run unchanged against the new CLI.
- [ ] Release PR opened from `feat/plans-codebase-audit` to `main`.
