---
name: "Chapter 4 — Completeness-first priority claim"
overview: "Within the same priority tier, claim tasks for pages closest to complete first, so the fastest route to more complete pages is also the queue's default behavior."
todos:
  - id: page-completeness
    content: "Add a catalogue_service_id-keyed page-completeness subquery"
    status: pending
  - id: queue-order
    content: "Join it into list_pending_tasks_for_claim's ORDER BY, after priority"
    status: pending
  - id: tests
    content: "Add the subquery test and the two claim-order tests"
    status: pending
isProject: false
---

# Chapter 4 — Completeness-first priority claim

**Repo:** `redtape` (`apps/api`) · **Branch:** `feat/discovery-throughput-completeness-priority-claim` · **Status:** planned

**Depends on:** none · **Decisions:** D5, D6 · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/plans-discovery-throughput`

## Goal

Within the same priority tier, claim tasks for pages closest to complete first, so the fastest route to more complete pages is also the queue's default behavior. This explicitly supersedes [discovery-operations decision D7](../../discovery-operations/gaps-and-decisions.md)'s ordering clause — see this suite's D5.

## Design

Today's claim order is pure FIFO-by-priority: `apps/api/app/features/discovery/repository/tasks.py:20`, `QUEUE_ORDER = (DiscoveryTask.priority.asc(), DiscoveryTask.created_at.asc(), DiscoveryTask.id.asc())`, used by `list_pending_tasks_for_claim` (same file, ~lines 75-80), called from `TaskQueue.claim_pending`. No join to candidate/mention/edge/artifact tables exists in this path today.

- New file `apps/api/app/features/discovery/repository/task_page_completeness.py`: a page-level (`catalogue_service_id`-keyed) parallel to `candidate_completeness_flags.py`, built as plain existence/non-empty checks (simpler than the per-candidate version, per D6 — confirmed `DiscoveryCandidateMention`, `DiscoveryCandidateEdge`, and `DiscoveryArtifact` all carry `catalogue_service_id` directly):
  - `has_domain` / `has_situation` — a `DiscoveryCandidateMention` row for this `catalogue_service_id` with a non-empty `domain_codes` / `situation_codes` array.
  - `has_edges` — a `DiscoveryCandidateEdge` row with this `catalogue_service_id`.
  - `has_snapshot` / `has_screenshot` — a `DiscoveryArtifact` row with this `catalogue_service_id` and the matching `DiscoveryArtifactKind` (`HTML_SNAPSHOT` / `SCREENSHOT`).
  - Sum the five booleans into `page_completeness` (0–5) per `catalogue_service_id`, as a subquery a caller can outer-join and `coalesce(..., 0)` for pages with no rows at all.
- `apps/api/app/features/discovery/repository/tasks.py:20` — `QUEUE_ORDER` stops being a bare tuple. `list_pending_tasks_for_claim` outer-joins the new subquery on `DiscoveryTask.catalogue_service_id` and orders by `(DiscoveryTask.priority.asc(), func.coalesce(page_completeness.c.page_completeness, 0).desc(), DiscoveryTask.created_at.asc(), DiscoveryTask.id.asc())`. Priority stays the dominant sort key — this is additive tie-breaking within a tier, not a priority redesign.
- Update the module comment at `tasks.py:20` to state explicitly that this supersedes `discovery-operations` D7's ordering clause (per D5).

## Tests

- New `apps/api/tests/test_task_page_completeness.py` (mirrors the fixture style of the existing `candidate_completeness_flags` test): build catalogue rows with 0, partial, and 5 chips (via fixture mentions/edges/artifacts), assert the subquery's `page_completeness` column matches expectation per row, and that a page with no mentions/edges/artifacts at all coalesces to `0`, not a missing row.
- Extend the test file that covers `list_pending_tasks_for_claim` (e.g. `apps/api/tests/test_discovery_task_queue.py`) with:
  - `test_list_pending_tasks_for_claim_prefers_higher_completeness_within_the_same_priority` — two pending tasks of the same priority and kind; the older one's `catalogue_service_id` has 0 chips, the newer one's has 4; assert the 4-chip task claims first, inverting plain `created_at` order. Fails today under FIFO.
  - `test_list_pending_tasks_for_claim_still_respects_priority_over_completeness` — a lower-priority-number task with 0 chips still claims before a higher-priority-number task with 5 chips, proving priority still dominates.

Red: both new claim-order tests fail against the current `QUEUE_ORDER` tuple. Green: the join/order-by change makes all tests pass.

## Verification

```bash
cd apps/api && ./ci.sh
```

Post-deploy spot check: confirm via the admin/machine task-summary endpoint that claim order visibly favors near-complete pages under real data.

## Refactor gate

Audit `list_pending_tasks_for_claim` for added branching/nesting from the join; extract the join/order-by into a small named helper (e.g. `_claim_order(page_completeness)`) if the method grows past the repository's usual method-size convention. Record the outcome.

## Commits

- `feat(discovery-api): rank task claims by page completeness within each priority tier`

## Out of scope

Persisting/materializing completeness (deferred seam); changing the canonical per-candidate `completeness_subquery`/`completeness_order` used by candidate-browsing lists; changing priority constants themselves.
