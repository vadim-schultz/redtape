---
name: "Chapter 12 — Docs sync"
overview: "Record voting and moderation as shipped, and replace the social-moderation strand's four TBD child plans with links into this suite, reconciling 'proposal' with 'suggestion'."
todos:
  - id: strand
    content: "social-moderation/README.md child-plan table points at this suite"
    status: pending
  - id: vocab
    content: "Note the proposal → suggestion naming reconciliation"
    status: pending
  - id: status
    content: "STATUS.md and plan statuses"
    status: pending
isProject: false
---

# Chapter 12 — Docs sync

**Repo:** `redtape` (docs only) · **Branch:** `docs/voting-sync` · **Status:** planned

**Depends on:** [10](10-web-vote-controls.md), [11](11-web-moderation-queue.md) · **Architecture:** [../00-architecture.md](../00-architecture.md) · **Rollout:** [../01-rollout.md](../01-rollout.md)

---

## Goal

The `social-moderation` strand, a stub since before this program began, points at real, shipped chapters
instead of TBD files (verified stub content in
[docs/planning/directions/social-moderation/README.md](../../../docs/planning/directions/social-moderation/README.md)).

## Design decisions

- The strand's child-plan table row for `01-proposal-state-machine.md` becomes a link to
  [05-status-transitions.md](05-status-transitions.md) and [00-architecture.md §4](../00-architecture.md);
  `02-voting-and-thresholds.md` → [04-tally-and-thresholds.md](04-tally-and-thresholds.md);
  `03-audit-log-schema.md` → [08-suggestion-event-log.md](08-suggestion-event-log.md);
  `04-moderator-workflows.md` → [09-moderator-override-endpoints.md](09-moderator-override-endpoints.md)
  and [11-web-moderation-queue.md](11-web-moderation-queue.md). The strand keeps its own file names as
  redirects (one line each: "See …") rather than being deleted, so old links do not break.
- A short note at the top of the strand's README: the strand said "proposal"; the shipped system says
  "suggestion" (matching [suggestion-interface](../../suggestion-interface/00-architecture.md)'s
  vocabulary) — same concept, the implementation's name is authoritative going forward.
- `docs/planning/directions/crawlers-jobs/README.md`'s dependency line on `social-moderation` is confirmed
  still accurate (crawlers still need the suggestion API, not the vote/moderation layer directly) or
  corrected if not.
- `STATUS.md`, `.plans/README.md`, this suite's rollout and chapters flip to `shipped`.

## Files

**Edit** — `docs/planning/directions/social-moderation/README.md`,
`docs/planning/directions/crawlers-jobs/README.md`, `docs/planning/STATUS.md`, `.plans/README.md`,
`.plans/voting-moderation/01-rollout.md` and chapters.

## Red tests

| Check | Asserts |
| --- | --- |
| Link check | Every relative link resolves |
| Status grep | No doc still lists the four child plans as TBD |

## Green

Edit docs; run the checks.

## Refactor gate

Docs only; nothing to gate.

## Verification

Link and status checks; `git diff --stat` shows docs only.

## Out of scope

Code changes.

## Git workflow

Branch `docs/voting-sync`; `docs(planning): record voting and moderation as shipped`; one PR.
