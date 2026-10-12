---
name: "Chapter 1 — Remove list chevron"
overview: "Remove the non-functional expand chevron beside the document count on /documents and add a regression test."
todos:
  - id: investigate
    content: "Identify DOM source of chevron beside count label"
    status: pending
  - id: test
    content: "QueryStatusView populated count row has no expand control"
    status: pending
  - id: fix
    content: "Remove chevron; keep count as muted Text"
    status: pending
isProject: false
---

# Chapter 1 — Remove list chevron

**Repo:** `redtape` (`apps/web`) · **Branch:** `feat/frontend-ui-menu-remove-chevron` · **Status:** planned

**Depends on:** none · **Architecture:** [../00-architecture.md](../00-architecture.md) · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/plans-frontend-ui-menu` · **Release branch:** `main`

---

## Goal

On `/documents` with a populated list, a down chevron appears on the right aligned with the count (e.g.
“4 documents”). It does nothing. Remove it.

## Design decisions

**Investigate first.** Source may not grep as `chevron` — inspect live DOM next to `QueryStatusView` →
`PopulatedList` count `Text`. Check `DocumentsListView`, theme slots, or leaked select indicators.

**Count row stays minimal.** Muted `Text` + list body; no collapse affordance unless behaviour is implemented later.

## Files

**Edit** — `apps/web/src/components/feedback/QueryStatusView.tsx`, `QueryStatusView.test.tsx`; optionally
`DocumentsListQueryStatus.test.tsx`.

## Red tests

| Test | Asserts |
| --- | --- |
| `QueryStatusView · populated count row has no expand control` | No expand/collapse control or `aria-expanded` toggle beside count; count and items still render |
| (optional) `DocumentsListQueryStatus · populated count row has no expand control` | Same at feature boundary |

## Green

Remove the chevron source; re-run narrow tests.

## Refactor gate

`QueryStatusView` / `PopulatedList` containing entity; report outcome.

## Verification

```bash
cd apps/web
npm run test -- src/components/feedback/QueryStatusView.test.tsx src/features/documents/components/documents-list/DocumentsListQueryStatus.test.tsx
cd ../.. && ./ci.sh
```

## Git workflow

```bash
git checkout feat/plans-frontend-ui-menu && git pull
git checkout -b feat/frontend-ui-menu-remove-chevron
```

```text
test(web): document count row has no expand chevron

fix(web): remove stray chevron beside document list count
```

Open PR **into `feat/plans-frontend-ui-menu`**, not `main`.
