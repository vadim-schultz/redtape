---
name: Voting Moderation — Gaps and decisions
overview: "Settled decisions and open seams for votes, thresholds, promotion and the audit log."
isProject: false
---

# Voting Moderation — Gaps and decisions

**Architecture:** [00-architecture.md](00-architecture.md) · **Rollout:** [01-rollout.md](01-rollout.md)

## Settled

| # | Decision |
| --- | --- |
| D1 | **One vote per user per suggestion, upserted.** Changing your mind changes the row; it does not add a second vote. Rejected: allowing multiple votes per user (defeats the point of a threshold) and immutable votes (people misclick). |
| D2 | **The submitter cannot vote on their own suggestion.** Enforced in the service, not the database (would need a trigger); tested explicitly. |
| D3 | **Tally is always computed from `suggestion_vote`, never cached.** A cached counter that can drift is worse than a `COUNT` query at this scale (seam below covers when that stops being true). |
| D4 | **Threshold triggers the transition synchronously, in the vote request.** No scheduled job, no eventual consistency: the voter who crosses the line sees the suggestion move in the same response. |
| D5 | **Promotion is part of the status transition, not a separate step a moderator triggers afterward.** `approved` always means "already in the catalogue"; there is no in-between state where a suggestion is approved but not yet promoted. |
| D6 | **Moderator override always promotes or simply rejects; it never sets `approved` without promotion running.** The override endpoint calls the same `transition_to` as the threshold path (§7 of the architecture). |
| D7 | **The event log is append-only and untyped beyond `event_type` + JSONB `data`.** A new event kind is a new enum value and a new `data` shape, not a new table — mirrors the suggestion payload's kind-per-JSONB-shape pattern. |
| D8 | **Thresholds are symmetric settings, not per-jurisdiction or per-kind.** Simple to reason about; a seam below covers outgrowing it. |
| D9 | **A submitter's identity is not exposed on the vote or event endpoints beyond what suggestion-interface already exposes** (display name only, D7 of that suite). |

## Open seams

| Seam | Placeholder | Forcing condition |
| --- | --- | --- |
| Vote count query cost | Plain `COUNT` per read | A suggestion accumulates thousands of votes; add a materialized tally then, matching the matrix endpoint's own scale seam |
| Threshold tuning per jurisdiction or kind | One global pair of settings | Real usage shows municipalities need different thresholds |
| Abuse: vote brigading, sockpuppet accounts | Not addressed (S4 in the program plan) | First observed manipulation |
| Reopening a rejected suggestion | Not possible; a new suggestion must be submitted | Users ask for it |
| Un-promoting (reverting a bad approval) | Manual: edit the resulting `Document` directly; no "undo" | A wrongly promoted document reaches production |
| Notifying the submitter of the outcome | Not built | Email/notification infrastructure exists |
