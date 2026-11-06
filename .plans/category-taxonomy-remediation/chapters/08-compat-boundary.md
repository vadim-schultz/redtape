---
id: C8
depends_on: []
touches:
  - .plans/category-taxonomy-remediation/run-ledger.md
  - .plans/category-taxonomy-remediation/gaps-and-decisions.md
execution: chief-of-staff
todos:
  - ch08-compat-boundary
---

# Chapter 8 — Compatibility boundary and worker drain (M7)

**Suite:** [README](README.md) · **Architecture:** [../00-architecture.md](../00-architecture.md) · **Rollout:** [../01-rollout.md](../01-rollout.md) · **Ledger:** [../run-ledger.md](../run-ledger.md)
**Decisions:** O4 in [../gaps-and-decisions.md](../gaps-and-decisions.md)

**Batch:** B0 (any time before C7) · **Execution:** chief-of-staff · **Status:** planned

## Goal

Before the legacy axes are removed from ingest (C7), confirm which senders still use them. Record the compatibility boundary date and the window in which cached web bundles get 404 or 422 responses.

This is live, read-only work for the chief of staff. No implementer runs it, and no code changes.

## Boundaries

- `execution`: chief-of-staff. Do not delegate to a chapter-implementer.
- `touches`: the ledger and the gaps file only.
- Read-only. Do not change a worker, a deployment, a bundle, or a database.

## Checks

1. Read the worker run records (the recorded runs for each worker version in use). For each one, confirm that the payload carries category codes only. Record the run identifiers and the versions.
2. If any run sends `domain_codes` or `situation_codes`, record it as a blocker for C7. C7 stays blocked until that worker is updated or drained.
3. Record the web bundle versions that are deployed. For each one, record whether it sends the removed `domain`, `situation`, or `group` parameters.
4. Record the O4 boundary date after which those parameters return a 422 that names the parameter.
5. Record the window in which cached bundles get 404 or 422 responses. Note that D-R8 accepts unfiltered lists for old bookmarked URLs.

## Red and green (as evidence)

- **Happy path (gate passes):** every worker run sends category codes only, and the O4 boundary date is recorded. C7 may start.
- **Negative path (gate fails):** any run sends a legacy field, or the boundary is not recorded. C7 is blocked and the ledger says why.

## Gate

- The ledger has a completed C8 entry with the run identifiers, versions, and dates.
- The gaps file has the O4 boundary date and the cached-bundle window recorded.
- The O4 row in [../gaps-and-decisions.md](../gaps-and-decisions.md) reads as decided with that date.

## Notes

- C8 has no dependencies. It can run early, and it must finish before C7 starts.
- The ledger records the 404 and 422 window explicitly (M7).
