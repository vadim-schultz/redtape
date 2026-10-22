---
name: "Chapter 5 — T4 handoff and operations docs sync"
overview: "Document the manual T4-to-pending-suggestion boundary, bounded queue operations, and the future crawler/evidence/moderation seams."
todos:
  - id: handoff
    content: "Document T4, emit preview, skip reasons, and pending suggestion behavior"
    status: pending
  - id: runbooks
    content: "Synchronize discovery-layer, discovery-online, and scheduled-job operator guidance"
    status: pending
  - id: loop-doc
    content: "Add the discovery-operations chief-of-staff loop document and final smoke checklist"
    status: pending
  - id: docs-check
    content: "Run link/reference checks and record the final ledger outcome"
    status: pending
isProject: false
---

# Chapter 5 — T4 handoff and operations docs sync

**Repo:** `redtape` (`docs/operations`, `.plans/discovery-operations`) · **Branch:** `docs/discovery-operations-handoff` · **Status:** planned

**Depends on:** [01](01-representative-row-smoke.md)–[04](04-admin-icon-navigation.md) · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/discovery-operations`

## Goal

Make the operational boundary after T4 unambiguous:

```text
T4 → inspect preview → manual machine emit → pending suggestion
```

The process stops there. This suite does not vote, promote, attach evidence, capture screenshots, or automatically emit scheduled work.

## Handoff contract

Document these facts for operators:

- T4 is an emit-readiness milestone, not a canonical-document state.
- Emit is a machine API operation:

  ```text
  POST /api/v1/discovery/machine/catalogue/<catalogue-service-id>/emit
  ```

- The admin pipeline's emit preview is read-only and does not itself emit.
- `new_document` claims are eligible only when title and official URL fields are present.
- `metadata` claims are preview-only in the current implementation.
- `new_requirement` claims are skipped until both document UUIDs resolve.
- Emit is idempotent by claim identity; replay returns the existing suggestion rather than creating a duplicate.
- The resulting suggestion remains `pending` until a future moderation/promotion suite acts on it.

The runbook must instruct operators to emit one verified row first, inspect the response counts and suggestion ID, and avoid bulk emit until the representative smoke is clean.

## Documentation targets

When this chapter is implemented, synchronize:

- [`docs/operations/discovery-layer.md`](../../../docs/operations/discovery-layer.md): staging vocabulary, T0–T4 meaning, representative smoke, manual emit, and the distinction between catalogue state, task history, claims, and canonical documents;
- [`docs/operations/discovery-online.md`](../../../docs/operations/discovery-online.md): bounded repeatable drain, run reports, queue metrics, stale lease handling, and failure triage;
- [`docs/operations/scheduled-jobs.md`](../../../docs/operations/scheduled-jobs.md): the discovery maintenance job's bounded behavior and the fact that scheduled jobs do not auto-emit;
- [`docs/operations/loops/discovery-operations.md`](../../../docs/operations/loops/discovery-operations.md): chief-of-staff execution instructions, loop branch, chapter order, and release protocol;
- [`.plans/README.md`](../../README.md), only when the suite is actually shipped, to record its status and deferred work.

Do not rewrite existing source-canon documents unless the smoke exposes a factual contradiction. Keep government endpoint facts in `docs/discovery/government-data-sources.md`.

## Final smoke checklist

1. An allowlisted admin can open Catalogue, Coverage, Tasks, and a valid pipeline detail route.
2. The Catalogue and Coverage surfaces show current rows and the agreed queue/run metrics.
3. The Tasks surface can distinguish pending, claimed, completed, and failed work.
4. A selected representative row has a recorded source, task IDs, fetch attempt, entity/claim results, and T3/T4 stage.
5. Emit preview shows resolvable payloads and explicit skip reasons.
6. One manual emit creates or replays a `pending` suggestion.
7. A bounded drain report records its run ID, counts, stop reason, and remaining state.
8. A failed or interrupted run is not reported as the last successful run.
9. Non-admin and unavailable-probe states do not reveal discovery navigation.
10. No step requires direct database access from the ingest worker.

## TDD and documentation gate

This is primarily a docs chapter. If documentation tests exist, add or update paired checks:

- `discovery operations docs mention bounded drain and manual emit` — happy documentation contract;
- `discovery operations docs do not claim crawler/evidence/promotion is shipped` — negative scope contract.

Run link/reference checks and the relevant package suite after any documentation test change. Report the refactor outcome as “docs-only; no code refactor needed” unless implementation work was incorrectly pulled into this chapter.

## Explicit deferrals

Keep these as named future suites rather than hidden TODOs:

- full `apps/crawler` package, source registry, extractors, and frontier adapter;
- robots-aware broad crawling and link following;
- Playwright screenshots and evidence storage;
- automatic emit;
- voting, moderation, and canonical promotion;
- LLM extraction and freshness crawling.
