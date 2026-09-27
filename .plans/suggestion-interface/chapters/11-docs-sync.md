---
name: "Chapter 11 — Docs sync"
overview: "Record the suggestion interface as shipped, fill the crawlers-jobs and social-moderation strand pointers to the new submit contract, and document the API-key issuance flow for crawler operators."
todos:
  - id: strands
    content: "Point crawlers-jobs/ and social-moderation/ READMEs at this suite"
    status: pending
  - id: ops
    content: "docs/operations/suggestion-api.md: payload shapes, error codes, idempotency"
    status: pending
  - id: status
    content: "STATUS.md and plan statuses"
    status: pending
isProject: false
---

# Chapter 11 — Docs sync

**Repo:** `redtape` (docs only) · **Branch:** `docs/suggestions-sync` · **Status:** planned

**Depends on:** [6](06-machine-submit-endpoint.md), [8](08-requirement-edge-kind.md), [9](09-web-suggestion-form.md), [10](10-web-suggestion-list-and-detail.md) · **Architecture:** [../00-architecture.md](../00-architecture.md) · **Rollout:** [../01-rollout.md](../01-rollout.md)

---

## Goal

Planning docs match the shipped suggestion API, and the crawler suite (next) has a concrete contract to
build against instead of a stub strand.

## Design decisions

- **`docs/operations/suggestion-api.md`**: the request/response shapes for both kinds, the 401/409/422 error
  bodies, the `Idempotency-Key` contract, and a copy-pasteable `curl` example using an issued API key. This
  is the document the crawler suite's chapter 2 (API client) is built against.
- `docs/planning/directions/crawlers-jobs/README.md` and `docs/planning/directions/social-moderation/README.md`
  gain a paragraph linking here instead of staying pure stubs.
- `STATUS.md` gets a dated line; `.plans/README.md` and this suite's rollout/chapters flip to `shipped`.

## Files

**Add** — `docs/operations/suggestion-api.md`.

**Edit** — `docs/planning/STATUS.md`, `docs/planning/directions/crawlers-jobs/README.md`,
`docs/planning/directions/social-moderation/README.md`, `.plans/README.md`,
`.plans/suggestion-interface/01-rollout.md` and chapters.

## Red tests

| Check | Asserts |
| --- | --- |
| Link check | Every relative link resolves |
| Status grep | No doc still calls suggestions "not started" |
| Example grep | The `curl` example's JSON is valid (piped through `python -m json.tool`) |

## Green

Write the operations doc; edit the rest; run the checks.

## Refactor gate

Docs only; nothing to gate beyond the checks.

## Verification

Link, status and JSON-validity checks; `git diff --stat` shows docs only.

## Out of scope

Code changes.

## Git workflow

Branch `docs/suggestions-sync`; `docs(planning): record the suggestion interface as shipped`; one PR.
