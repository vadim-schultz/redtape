# Discovery operations (chief of staff)

This suite is orchestrated as a **chief of staff** plan.

Plan suite folder: `.plans/discovery-operations/` (architecture, rollout, chapters, ledger).

**Loop branch:** `feat/discovery-operations`
**Release branch:** `main`

## How to run

1. Launch **chief of staff** with plan folder `.plans/discovery-operations/`.
2. Run one chapter-implementer per chapter, in the order of
   [`01-rollout.md`](../../../.plans/discovery-operations/01-rollout.md): row smoke, queue
   observability, bounded drain, admin icon navigation, T4 handoff docs.
3. Each chapter PR targets the loop branch only.
4. When the ledger is complete, open the release PR from the loop branch to `main`.

## What the suite delivered

- `discovery_run` table, run lifecycle on the machine API, and `stale_runs` in coverage metrics.
- Bounded drain: `--max-tasks`, `--max-batches`, `--time-budget-seconds`, with a stop reason.
- Icon controls for Catalogue, Coverage, and Tasks under the existing admin probe.
- Operator docs for the T4 handoff: [discovery-layer.md](../discovery-layer.md),
  [discovery-online.md](../discovery-online.md), [scheduled-jobs.md](../scheduled-jobs.md).

## Known gaps

- The chapter 1 smoke is partial (T0, T1, T2 and fixture contract tests). A persisted T4 row and a
  manual emit were not verified against a running API.
- Drain reports `remaining` as unknown; no queue-summary route exists for the worker.
- A manual multi-batch drain and an interrupted-claim lease-reclaim check were not performed.

## Final smoke checklist

Run against a non-production stack first, and record the result of each step.

1. An allowlisted admin can open Catalogue, Coverage, Tasks, and a valid pipeline detail route.
2. Catalogue and Coverage show current rows, queue counts, `stale_claims`, `stale_runs`, and
   `last_successful_run`.
3. Tasks distinguishes pending, claimed, completed, and failed work.
4. A representative row with a `fim_id` has a recorded source, task IDs, fetch attempt, entity and
   claim results, and a T3 or T4 stage.
5. Emit preview shows resolvable payloads and explicit skip reasons.
6. One manual emit creates or replays a `pending` suggestion; record counts and suggestion ID.
7. A bounded drain report records its `run_id`, counts, and `stop_reason`.
8. A failed or interrupted run is not shown as the last successful run.
9. Non-admin and unavailable-probe sessions show no discovery navigation.
10. No step needs direct database access from the ingest worker.

## Out of scope (named future suites)

- Full `apps/crawler` package, source registry, extractors, and frontier adapter.
- Robots-aware broad crawling and link following.
- Playwright screenshots and evidence storage.
- Automatic emit.
- Voting, moderation, and canonical promotion.
- LLM extraction and freshness crawling.
