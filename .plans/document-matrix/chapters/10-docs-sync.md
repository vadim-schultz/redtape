---
name: "Chapter 10 — Docs sync"
overview: "Update STATUS, strand READMEs and the data-model chapter to reflect the shipped matrix; add a mobile seam note."
todos:
  - id: status
    content: "STATUS.md entry"
    status: pending
  - id: strands
    content: "Web, data-model, mobile READMEs point to the matrix suite"
    status: pending
  - id: suite
    content: "Mark chapters done in rollout and architecture; update .plans/README"
    status: pending
isProject: false
---

# Chapter 10 — Docs sync

**Repo:** `redtape` (docs only) · **Branch:** `docs/matrix-sync` · **Status:** planned

**Depends on:** [7](07-list-filter-chips.md), [8](08-matrix-page.md), [9](09-tags-on-card-and-detail.md) · **Rollout:** [../01-rollout.md](../01-rollout.md)

---

## Goal

Planning docs describe what exists: the matrix is documented as shipped, the mobile strand knows the
taxonomy it should reuse, and nothing links to a stale "category tags" idea.

## Design decisions

**Pointers, not copies.** Strand docs link to `.plans/document-matrix/` rather than restating it.

**Record real outcomes.** Each chapter's Status flips to `done` with the refactor-gate outcome written
in, as in [web-frontend chapter 2](../../web-frontend/chapters/02-theme-system.md).

## Files (edit only)

| Path | Change |
| --- | --- |
| `docs/planning/STATUS.md` | Dated entry: matrix shipped, endpoints, seeded counts |
| `docs/planning/directions/data-model-migrations/02-documents-and-requirements.md` | Metadata bullet points to the taxonomy tables, not jsonb tags |
| `docs/planning/directions/web-frontend/README.md` | Matrix page and filters listed under IA |
| `docs/planning/directions/mobile-flutter/README.md` | Vault organizes by the same `domain` / `life_situation` slugs from `GET /domains`, `/life-situations`; sync is a later chapter |
| `docs/planning/directions/backend-api/README.md` | New endpoints |
| `.plans/README.md`, `.plans/document-matrix/01-rollout.md`, `00-architecture.md` | Status lines, chapter table |

## Red tests

Docs have no unit tests; the "red" is a failing link check.

| Check | Asserts |
| --- | --- |
| Link check over `.plans/` and `docs/` | Every relative link resolves |
| Chapter table vs `chapters/` listing | Filenames match, statuses consistent |
| Grep `category tags` in planning docs | No stale reference remains |

## Green

Edit until checks pass.

## Refactor gate

Remove duplicated explanations between strand READMEs and this suite; keep one canonical description
(architecture doc).

## Verification

```bash
grep -rn "category tags" docs .plans
# link check script or manual open of each edited file
./ci.sh
```

## Out of scope

New product decisions, any code.

## Git workflow

```bash
git checkout main && git pull
git checkout -b docs/matrix-sync
```

```text
docs(planning): record document matrix as shipped and link strands
```
