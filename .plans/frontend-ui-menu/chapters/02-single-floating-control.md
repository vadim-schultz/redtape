---
name: "Chapter 2 — Single floating R control"
overview: "Remove the left brand link; menu trigger uses BrandMark instead of FaBars — one fixed circle top-right."
todos:
  - id: floating
    content: "FloatingControls: right slot only"
    status: pending
  - id: trigger
    content: "AppMenu: BrandMark trigger, not FaBars"
    status: pending
  - id: tests
    content: "Update FloatingControls, AppMenu, App tests"
    status: pending
isProject: false
---

# Chapter 2 — Single floating R control

**Repo:** `redtape` (`apps/web`) · **Branch:** `feat/frontend-ui-menu-single-control` · **Status:** planned

**Depends on:** [1](01-remove-list-chevron.md) · **Architecture:** [../00-architecture.md](../00-architecture.md) §2 · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/plans-frontend-ui-menu` · **Release branch:** `main`

---

## Goal

Consolidate floating chrome: one circle top-right opens the menu with the gothic R. No left home link; no burger icon.

## Design decisions

**Trigger.** `IconButton` + `BrandMark`, `aria-label` = `common.menu`, `{...floatingSurface}`.

**Layout.** Drop left `BrandButton` from `FloatingControls`. Adjust `AppLayout` top padding if needed (still one 44px control).

**Home.** Navigation to documents moves to chapter 4 Documents row; until then users reach `/` via bookmarks or chapter 4.

## Files

**Edit** — `FloatingControls.tsx`, `FloatingControls.test.tsx`, `AppMenu.tsx`, `AppLayout.tsx`, `App.test.tsx`.

## Red tests

| Test | Asserts |
| --- | --- |
| `FloatingControls · renders only the menu trigger on the right` | No `nav.home` link; one menu button |
| `FloatingControls · buttons are fixed-position circles` | Single fixed circle |
| `AppMenu · trigger shows brand mark not bars` | Brand mark present; no burger |
| `App.test.tsx` | No separate home link in chrome (update if asserted today) |

## Green

Implement trigger and layout changes; tests green.

## Refactor gate

`FloatingControls` + `AppMenu`; report outcome.

## Verification

```bash
cd apps/web
npm run test -- src/components/layout/FloatingControls.test.tsx src/components/layout/AppMenu.test.tsx src/app/App.test.tsx
cd ../.. && ./ci.sh
```

## Git workflow

```bash
git checkout feat/plans-frontend-ui-menu && git pull
git checkout -b feat/frontend-ui-menu-single-control
```

```text
test(web): single R menu trigger in floating chrome

feat(web): replace dual floating controls with brand menu trigger
```

Open PR **into `feat/plans-frontend-ui-menu`**.
