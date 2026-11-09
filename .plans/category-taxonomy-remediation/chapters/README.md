# Category taxonomy remediation — Chapters

**Architecture:** [../00-architecture.md](../00-architecture.md) · **Rollout:** [../01-rollout.md](../01-rollout.md) · **Gaps and decisions:** [../gaps-and-decisions.md](../gaps-and-decisions.md) · **Ledger:** [../run-ledger.md](../run-ledger.md)

Each chapter file carries frontmatter with `id`, `depends_on`, `touches`, `execution`, and `todos`. The schedule comes from `depends_on` and `touches` (see [../01-rollout.md](../01-rollout.md)). Chapter order in this index is for reading only.

| ID | Chapter | Execution | depends_on | Batch | Status |
| --- | --- | --- | --- | --- | --- |
| C0 | [CI baseline](00-ci-baseline.md) | chapter-implementer | none | B0 | planned |
| C1 | [Contract artifact under `apps/api`](01-artifact-under-api.md) | chapter-implementer | C0 | B1 | planned |
| C2 | [Replay merge rule (M1)](02-replay-merge.md) | chapter-implementer | C1 | B2 | planned |
| C3 | [Retirement migration gate (H1)](03-retirement-gate.md) | chapter-implementer | C2 | B3 | planned |
| C4 | [Machine crosswalk and ingest fetch (M2)](04-machine-crosswalk.md) | chapter-implementer | C1 | B2 | planned |
| C5 | [Completeness decision (M3)](05-completeness-decision.md) | chapter-implementer | C0 (blocked on D-R4) | B1 or B3 | blocked (D-R4) |
| C6 | [Chip opacity and staged copy (M4, L4)](06-chip-and-staged-copy.md) | chapter-implementer | C0 | B1 | planned |
| C7 | [Ingest legacy removal (M6)](07-ingest-legacy-removal.md) | chapter-implementer | C4, C8 | B3 | planned |
| C8 | [Compatibility boundary (M7)](08-compat-boundary.md) | chief-of-staff | none | B0 (any time before C7) | planned |
| C9 | [Review-state leaves (M8)](09-review-leaves.md) | chapter-implementer | C1 | B2 | planned |
| C10 | [Reference scan and gates (M5)](10-reference-scan.md) | chapter-implementer | C3, C7 | B4 | planned |
| C11 | [API and web spec cleanup (L5, L6, L7)](11-api-web-spec.md) | chapter-implementer | C4 | B3 | planned |
| C12 | [Docs and decision sync (L1, L2, L3, L8)](12-docs-decision-sync.md) | chapter-implementer | C3, C5, C6, C7, C9, C10, C11 | B5 | planned |
| C13 | [Production preflight (live, read-only)](13-production-preflight.md) | chief-of-staff | C10, C11, C12 | B6 | planned |
| C14 | [Release gate and PR (live)](14-release-gate.md) | chief-of-staff | C13 | B7 | planned |

## Reading order for implementers

1. [../00-architecture.md](../00-architecture.md): the rules every chapter enforces.
2. The chapter file for your assignment.
3. [../gaps-and-decisions.md](../gaps-and-decisions.md): decisions you must consume and may not change.

Chapter implementers do not edit the ledger, the release PR, or another chapter's file.
