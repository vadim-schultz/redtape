---
name: "Chapter 6 — Docs sync"
overview: "Record the floating navigation as shipped, mark the matrix page superseded, and fix stale status and palette statements in the planning docs."
todos:
  - id: readme
    content: "Update .plans/README.md status lines"
    status: pending
  - id: matrix-docs
    content: "Mark document-matrix chapter 8 and decisions as superseded"
    status: pending
  - id: planning
    content: "Update docs/planning STATUS and web-frontend direction"
    status: pending
  - id: stale
    content: "Fix stale web-frontend status and palette (D2)"
    status: pending
isProject: false
---

# Chapter 6 — Docs sync

**Repo:** `redtape` (docs only) · **Branch:** `docs/floating-nav-sync` · **Status:** planned

**Depends on:** [5](05-floating-shell.md) · **Architecture:** [../00-architecture.md](../00-architecture.md) · **Rollout:** [../01-rollout.md](../01-rollout.md)

---

## Goal

Planning docs match the shipped UI. Same shape as
[document-matrix chapter 10](../../document-matrix/chapters/10-docs-sync.md).

## Design decisions

- Rollout rows and chapter meta lines in this folder flip to `done`.
- [document-matrix chapter 8](../../document-matrix/chapters/08-matrix-page.md) and its architecture §6 get a
  one-line note: "Superseded by [floating-nav chapter 1](../../floating-nav/chapters/01-remove-matrix.md);
  matrix page removed from the web app." The history stays.
- [docs/planning/directions/web-frontend/README.md](../../../docs/planning/directions/web-frontend/README.md):
  remove the "matrix page at `/matrix`" wording, link this folder, and correct "Chapters 1–3 are done …
  Continue at chapter 4" (chapter 4 is done).
- `.plans/README.md`: correct the same stale web-frontend status; keep the new folder's Status line current.
- [web-frontend gaps D2](../../web-frontend/gaps-and-decisions.md): replace the old wine/deep palette values
  with the shipped Swiss red `#DA291C` scale, and note the Iceberg wordmark was retired.
- `docs/planning/STATUS.md`: dated update line.

## Files

**Edit** — `.plans/README.md`, `.plans/floating-nav/01-rollout.md` and chapters,
`.plans/document-matrix/chapters/08-matrix-page.md`, `.plans/document-matrix/00-architecture.md`,
`.plans/web-frontend/gaps-and-decisions.md`, `.plans/web-frontend/01-rollout.md` (chapter 4 row),
`docs/planning/STATUS.md`, `docs/planning/directions/web-frontend/README.md`.

## Red tests

| Check | Asserts |
| --- | --- |
| Link check | Every relative link in edited files resolves to an existing file |
| Status grep | No doc still claims the matrix page is live or "chapters 1–3 done" |

## Green

Edit docs; run a link-check script over `.plans/` and `docs/planning/`.

## Refactor gate

Docs only; nothing to gate beyond the link check.

## Verification

Link check; `git diff --stat` shows docs only.

## Out of scope

Code changes.

## Git workflow

Branch `docs/floating-nav-sync`; `docs(planning): record floating nav as shipped`; one PR.
