---
name: "Chapter 11 — Docs sync"
overview: "Record the crawler as shipped, replace the crawlers-jobs strand's discovery-related TBD child plans with links here, and note the freshness mode as still open."
todos:
  - id: strand
    content: "crawlers-jobs/README.md child-plan table"
    status: pending
  - id: status
    content: "STATUS.md and plan statuses"
    status: pending
isProject: false
---

# Chapter 11 — Docs sync

**Repo:** `redtape` (docs only) · **Branch:** `docs/crawler-sync` · **Status:** planned

**Depends on:** [10](10-github-actions-schedule.md) · **Architecture:** [../00-architecture.md](../00-architecture.md) · **Rollout:** [../01-rollout.md](../01-rollout.md)

---

## Goal

The `crawlers-jobs` strand's stub points at what actually shipped, and is honest that only the discovery
mode exists.

## Design decisions

- [docs/planning/directions/crawlers-jobs/README.md](../../../docs/planning/directions/crawlers-jobs/README.md):
  `03-discovery-crawler.md` becomes a link to [00-architecture.md](../00-architecture.md) and
  [06-first-extractor.md](06-first-extractor.md); `04-ethics-and-compliance.md` links to
  [03-polite-fetcher.md](03-polite-fetcher.md) and its robots.txt/rate-limit/user-agent decisions;
  `01-job-runner-and-scheduling.md` links to [10-github-actions-schedule.md](10-github-actions-schedule.md).
  `02-freshness-crawler.md` stays TBD, now with a one-line note that this program deliberately built
  discovery first (D1 in [gaps-and-decisions.md](../gaps-and-decisions.md)).
- This is the program's **last** suite; `.plans/README.md` gets a closing note that the six-suite pipeline
  (ci-foundation, auth, suggestion-interface, evidence-storage, voting-moderation, crawlers) is complete,
  linking each suite once more in dependency order for a reader arriving fresh.
- `STATUS.md`, this suite's rollout and chapters flip to `shipped`.

## Files

**Edit** — `docs/planning/directions/crawlers-jobs/README.md`, `docs/planning/STATUS.md`,
`.plans/README.md`, `.plans/crawlers/01-rollout.md` and chapters.

## Red tests

| Check | Asserts |
| --- | --- |
| Link check | Every relative link resolves |
| Status grep | No doc still lists discovery-crawler or job-runner-and-scheduling as TBD |

## Green

Edit docs; run the checks.

## Refactor gate

Docs only; nothing to gate.

## Verification

Link and status checks; `git diff --stat` shows docs only.

## Out of scope

Code changes; the freshness crawler.

## Git workflow

Branch `docs/crawler-sync`; `docs(planning): record the discovery crawler as shipped`; one PR.
