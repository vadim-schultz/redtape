---
name: "Chapter 9 — Docs sync"
overview: "Record evidence storage as shipped, correct the docs that listed R2/Supabase Storage as an open choice, and link the evidence API contract for the crawlers suite."
todos:
  - id: stack
    content: "01-stack-and-free-tier.md: R2 is chosen, not proposed"
    status: pending
  - id: api-doc
    content: "docs/operations/suggestion-api.md gains the evidence endpoints"
    status: pending
  - id: status
    content: "STATUS.md and plan statuses"
    status: pending
isProject: false
---

# Chapter 9 — Docs sync

**Repo:** `redtape` (docs only) · **Branch:** `docs/evidence-sync` · **Status:** planned

**Depends on:** [7](07-web-evidence-viewer.md), [8](08-r2-runbook-and-provisioning.md) · **Architecture:** [../00-architecture.md](../00-architecture.md) · **Rollout:** [../01-rollout.md](../01-rollout.md)

---

## Goal

Planning docs match the shipped storage layer, and the evidence upload contract is written down where the
crawler suite's chapter 8 (evidence submission) will look for it.

## Design decisions

- [docs/planning/01-stack-and-free-tier.md](../../../docs/planning/01-stack-and-free-tier.md): replace "R2
  or Supabase Storage" with "Cloudflare R2 (shipped, see [evidence-storage](../00-architecture.md))".
- [docs/operations/suggestion-api.md](../../../docs/operations/suggestion-api.md) (from
  [suggestion-interface chapter 11](../../suggestion-interface/chapters/11-docs-sync.md)) gains a section
  for the two evidence endpoints, with the same `curl` style.
- `STATUS.md`, `.plans/README.md`, this suite's rollout and chapters flip to `shipped`.

## Files

**Edit** — `docs/planning/01-stack-and-free-tier.md`, `docs/operations/suggestion-api.md`,
`docs/planning/STATUS.md`, `.plans/README.md`, `.plans/evidence-storage/01-rollout.md` and chapters.

## Red tests

| Check | Asserts |
| --- | --- |
| Link check | Every relative link resolves |
| Status grep | No doc still presents object storage as an open decision |

## Green

Edit docs; run the checks.

## Refactor gate

Docs only; nothing to gate.

## Verification

Link and status checks; `git diff --stat` shows docs only.

## Out of scope

Code changes.

## Git workflow

Branch `docs/evidence-sync`; `docs(planning): record evidence storage as shipped`; one PR.
