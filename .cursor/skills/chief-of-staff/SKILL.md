---
name: chief-of-staff
description: >-
  Orchestrate a Redtape plan suite from .plans/ by scheduling independent
  chapter-implementer agents in parallel whenever dependencies and file
  ownership permit, then integrating their reviewable changes into the loop
  branch.
---

# Chief of staff

Use this skill when the user asks to execute or coordinate a plan suite under
[`.plans/`](../../../.plans/). The chief of staff owns orchestration,
integration, live gates, and the suite ledger. A `chapter-implementer` owns one
implementation chapter in one isolated worktree.

The canonical plan shape is
[`.plans/PLAN_TEMPLATE.md`](../../../.plans/PLAN_TEMPLATE.md). Treat a
suite's `01-rollout.md` as its execution contract, not as a list that must be
followed serially.

## Operating contract

1. Read `00-architecture.md`, `01-rollout.md`, `gaps-and-decisions.md` when
   present, every chapter index, and the relevant chapter plans before
   scheduling work.
2. Confirm the loop branch, release branch, prerequisite, and local CI command.
   Do not create chapter branches from a stale base.
3. Build the schedule from each chapter's `depends_on` and `touches` metadata.
   A chapter list, filename order, or prose ordering is not a dependency.
4. Start every ready chapter whose declared dependencies are satisfied and whose
   `touches` sets do not conflict in the same batch. Launch independent
   `chapter-implementer` sub-agents in parallel, one per isolated worktree.
5. Keep chapters with shared files serial unless the rollout explicitly
   partitions ownership and defines the integration order.
6. A failed chapter blocks only its dependents. Continue unrelated ready
   chapters, report the failure, and do not hide it by weakening tests or
   changing the plan.
7. After an implementer reports success, inspect its diff and gate, merge or
   rebase it into the loop branch in the declared integration order, and then
   update the ledger. Integration may be serial even when implementation was
   parallel.
8. Start a dependent chapter only after its dependency is integrated into the
   loop branch and its contract is still valid.
9. Run live production checks, release steps, and other `execution:
   chief-of-staff` work yourself. Never delegate those to a
   `chapter-implementer`.
10. Do not let implementers edit the suite ledger, release PR, or unrelated
    chapters. Pass [the corporate build environment](corporate-build-env.md)
    to every implementer assignment when it applies.

## Scheduling rules

Use the smallest dependency-aware batch:

```text
ready = chapters with every depends_on chapter integrated
batch = ready chapters with disjoint touches and no unresolved conflict
launch all batch members concurrently
integrate completed members one at a time
repeat
```

The batch is not required to be full when local resources or CI capacity are
limited, but avoid serial execution merely because it is simpler. Prefer the
chapters on the longest remaining dependency path when a capacity limit forces
prioritisation. Record any intentional reduction in concurrency and its reason
in the ledger or rollout notes.

For every implementer assignment, include:

- the exact chapter path and chapter ID;
- the loop branch and isolated-worktree requirement;
- the chapter's goal, `depends_on`, `touches`, and do-not-edit boundaries;
- the paired red tests, green implementation, and refactor gate;
- the narrow verification command and full local CI command;
- relevant skill files and the corporate build environment block;
- the instruction to return the diff summary, test evidence, refactor outcome,
  and any integration conflict.

When a chapter finishes, verify the paired happy and negative paths, the
refactor outcome, the declared file boundary, and the chapter gate before
marking it integrated. Do not start a dependent chapter from an unverified
worktree.

## Required plan metadata

Every new or substantially revised suite follows
[`.plans/PLAN_TEMPLATE.md`](../../../.plans/PLAN_TEMPLATE.md). In particular,
`01-rollout.md` must contain:

- a complete dependency graph;
- a chapter scheduling matrix with `depends_on`, `touches`, execution owner,
  gate, and status;
- an explicit `## Parallel batches` section listing all chapters in each
  concurrently runnable batch and why the batch is safe;
- an integration order for chapters that touch shared files;
- a critical-path summary and the per-chapter gate.

Every executable chapter must declare in frontmatter:

```yaml
id: C1
depends_on: []
touches:
  - apps/example/
execution: chapter-implementer
```

Use `execution: chief-of-staff` for live gates, production checks, release
operations, and other work that must stay with the orchestrator. Use stable
chapter IDs in `depends_on`, not display names or list positions.

If an older suite lacks this metadata, derive a temporary schedule from its
dependency graph and file boundaries before launching agents, then record the
derived batches in `01-rollout.md`. Do not assume an old numbered execution
list is intentionally sequential.

## Completion

A suite is complete only when:

- every implementable chapter is integrated into the loop branch or explicitly
  recorded as blocked, deferred, or rejected;
- every chapter reports its paired tests, refactor-gate outcome, and local CI;
- the ledger records implementation order, integration order, conflicts, and
  failures;
- chief-of-staff live gates are complete or explicitly handed to the user;
- the release gate passes and the release PR targets the declared release
  branch.
