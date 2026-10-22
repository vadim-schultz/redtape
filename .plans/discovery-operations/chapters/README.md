# Discovery operations chapters

The chief-of-staff execution order is defined in [../01-rollout.md](../01-rollout.md).

| # | Chapter | Purpose |
| --- | --- | --- |
| 1 | [Representative row end-to-end smoke](01-representative-row-smoke.md) | Prove ingest, drain, FIM enrichment, T3/T4, preview, and one manual emit |
| 2 | [Queue observability](02-queue-observability.md) | Define and expose queue, fetch, lease, source-failure, and run-health metrics |
| 3 | [Bounded repeatable worker drain](03-bounded-repeatable-drain.md) | Drain multiple finite batches or a finite time window without infinite looping |
| 4 | [Discovery admin icon navigation](04-admin-icon-navigation.md) | Replace the three discovery text links with accessible existing-library icons |
| 5 | [T4 handoff and operations docs sync](05-t4-handoff-and-docs-sync.md) | Document the pending-suggestion boundary and synchronize operator guidance |

The full crawler package, screenshots, evidence, voting, moderation, and canonical promotion are future suites. They may consume the stable identifiers and contracts produced here, but they are not implementation dependencies of these chapters.
