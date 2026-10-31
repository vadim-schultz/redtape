---
name: "Chapter 5 — Sitewide body panel"
overview: "Wrap every routed page's content in AppLayout with a surface.base panel (border.base, shell shadow), the same visual language SectionCard already uses, so there is a consistent, visible boundary between page canvas and page body across the whole app."
todos:
  - id: panel
    content: "Wrap AppLayout's {children} in a surface.base/border.base/shadow panel"
    status: pending
  - id: smoke
    content: "Manual check across representative pages (documents list, candidates list, document detail, discovery admin catalogue) for layout regressions"
    status: pending
isProject: false
---

# Chapter 5 — Sitewide body panel

**Repo:** `redtape` (`apps/web`) · **Branch:** `feat/candidate-view-polish-body-panel` · **Status:** planned
**Depends on:** none · **Architecture:** [../00-architecture.md](../00-architecture.md) (section 7) · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/plans-candidate-view-polish` · **Release branch:** `main`

## Goal

`AppLayout.tsx` puts both the outer shell and `<main>`/`Container` on `bg.canvas`, so every page's content sits directly on the same background as the page itself — there is no visual boundary anywhere in the app between "canvas" and "body". The theme already has the tokens for exactly this distinction (`surface.base`, `border.base`, the `shell` shadow used by `SectionCard`); apply them once, at the shell, so every routed page gets the boundary without each page component changing.

## Design decisions

- **Single integration point.** Change `AppLayout.tsx` only: keep the outer `VStack`/`FloatingControls` and the page background (`bg.canvas`) as they are, but wrap `{children}` (inside the existing `Container`, or immediately around it — chapter author picks whichever keeps `ColdStartNotice` and the padding behaving sensibly) in a new panel `Box` using `backgroundColor="surface.base"` (or `surface`, matching `SectionCard`'s token), `borderWidth="1px"`, `borderColor="border"` (matching `border.base`), and `shadow="shell"` (or `card`, whichever reads better against the full page — try both, pick one, note the choice in the PR).
- **No new tokens.** Reuse exactly what `SectionCard.tsx` already uses (`backgroundColor="surface"`, `borderWidth="1px"`, `borderColor="border"`, `shadow="shell"`) — do not invent a new semantic token for this.
- **Padding.** The panel needs internal padding so content doesn't touch its own border; reuse or adapt the existing `Container`'s `pb={8}` plus new top/side padding on the panel itself, consistent with `SectionCard`'s `Card.Body` spacing.
- **No opt-out in v1.** Every routed page gets the panel uniformly (decision, [gaps-and-decisions.md](../gaps-and-decisions.md) open seam) — do not add a prop or per-route override unless the manual smoke below finds a page that's genuinely broken by it, in which case note that page and raise the opt-out as a follow-up rather than scope-creeping this chapter.
- **Light and dark.** Confirm the `surface`/`border`/`shell` tokens already resolve correctly in both modes (they're existing tokens with mode-aware definitions in `theme/semantic-tokens/`) — no new dark-mode-specific styling should be needed.

## Files

**Edit**

- `apps/web/src/components/layout/AppLayout.tsx`
- its test file (create if one doesn't already exist; check first — `AppLayout` is a thin shell, a snapshot-style or structural test may be new)

**Do not edit**

- `SectionCard.tsx`, `AppCard.tsx`, any theme token file (reuse as-is)
- Individual page/feature components — the point of this chapter is that none of them need to change
- `FloatingControls.tsx`, `ColdStartNotice.tsx`

## Red tests

| Test | Asserts |
| --- | --- |
| `AppLayout wraps its children in a surface panel` | Happy: the rendered output has a container around `{children}` with `surface`/`surface.base` background, a border, and a shadow — distinct from the outer `bg.canvas` element. |
| `the outer shell still uses the canvas background` | Negative: the outermost container (outside the new panel) still resolves to `bg.canvas`, so the boundary is visible, not just a uniform recolor. |
| `ColdStartNotice and FloatingControls render unaffected` | Negative: both still render in their existing positions relative to the new panel (FloatingControls outside/above it, `ColdStartNotice` inside, at the top of the panel). |
| `the panel renders in both color modes` | Happy: rendering under light and dark mode providers both resolve a panel background distinct from the canvas background in that mode. |

## Green

1. Add the panel `Box` inside `AppLayout.tsx`, wrapping `{children}` (and `ColdStartNotice`, matching its current position) with the `surface`/`border`/`shadow` tokens.
2. Adjust padding so content doesn't visually collide with the new border.
3. Run the existing `AppLayout`/`App.test.tsx` suite to catch any snapshot or structural regression; update expectations deliberately, not by blindly accepting a snapshot diff.

## Refactor gate

Audit `AppLayout.tsx`: it should remain a small, readable shell — if the panel logic grows beyond a few lines, consider whether it belongs in a small named sub-component, but default to inline given the file's current size. Report the outcome.

## Manual smoke (part of this chapter, not deferred)

Before merging, visually check at least these pages in both light and dark mode, at a few widths: `/documents` (list), `/candidates` (list), `/documents/:id` or `/candidates/:id` (detail), and one discovery admin page (e.g. the catalogue). Confirm the panel reads as an intentional, consistent boundary, not a layout break — pay particular attention to any page with a wide table or edge-to-edge content, per the open seam in [gaps-and-decisions.md](../gaps-and-decisions.md). Record what was checked in the PR description.

## Verification

```bash
cd apps/web
npm run test -- src/components/layout src/app --run
npm run lint
npm run format:check
npm run typecheck
npm run build
cd ../..
./ci.sh
```

## Commits

`test(web): define the sitewide body panel`, `feat(web): wrap page content in a surface panel distinct from the canvas`.

## Out of scope

A per-page opt-out mechanism (open seam, noted for follow-up if the manual smoke finds a page that needs one); any new design token; changes to `SectionCard`, `AppCard`, or any individual page's own internal layout.

## Git workflow

```bash
git checkout feat/plans-candidate-view-polish && git pull
git checkout -b feat/candidate-view-polish-body-panel
```

Open the chapter PR into `feat/plans-candidate-view-polish`.
