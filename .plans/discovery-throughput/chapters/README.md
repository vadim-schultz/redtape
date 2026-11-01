# Discovery throughput chapters

The chief-of-staff execution order is defined in [../01-rollout.md](../01-rollout.md).

| # | Chapter | Purpose |
| --- | --- | --- |
| 1 | [Budget reallocation (2000/1000/1000)](01-budget-reallocation.md) | Raise the scheduled/CI Actions-minutes split in code defaults and docs |
| 2 | [Same-day pipeline scheduling](02-same-day-pipeline-scheduling.md) | Split and retime the five discovery workflows so every hop completes same-day |
| 3 | [Optional situation codes](03-optional-situation-codes.md) | Stop discarding an entire LLM page extraction over a missing `situation_codes` |
| 4 | [Completeness-first priority claim](04-completeness-priority-claim.md) | Rank task claims by page completeness within each priority tier |
| 5 | [Operator docs sync](05-operator-docs-sync.md) | Bring every operator-facing doc in line with chapters 1–4's shipped shape |
| 6 | [Schedule activation](06-schedule-activation.md) | Turn on all five discovery schedules via `gh variable set` |

Each chapter has: Goal, Design (concrete file paths and decisions), Tests/TDD loops (or, for YAML-only and docs-only chapters, the equivalent parse/grep check), Verification, Refactor gate, Commits, and Out of scope. Chapters 1–4 are independent and may be implemented in any order; chapter 5 waits on all four; chapter 6 waits on chapter 5 and is the only chapter whose final step is live `gh` commands rather than a code commit.
