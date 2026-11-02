---
name: "Chapter 4 — Confidence circle"
overview: "Show each document's confidence as a Chakra ProgressCircle: the whole ring in a red, yellow or green band colour with the actual value as the darker sector."
todos:
  - id: bands
    content: "confidenceBand.ts: LOW_MAX 0.4, HIGH_MIN 0.7, bandFor, band to colorPalette"
    status: pending
  - id: circle
    content: "ConfidenceCircleView/ConfidenceCircle.tsx on ProgressCircle with Track muted, Range solid, ValueText percentage"
    status: pending
  - id: card
    content: "DocumentCard renders the circle"
    status: pending
  - id: tests
    content: "Boundary, palette, accessibility and clamping tests"
    status: pending
isProject: false
---

# Chapter 4 — Confidence circle

**Repo:** `redtape` (`apps/web`) · **Branch:** `feat/document-browse-confidence-circle` · **Status:** planned
**Depends on:** Chapter 3 ([03-documents-on-candidates.md](03-documents-on-candidates.md)) · **Architecture:** [../00-architecture.md](../00-architecture.md) §5 · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/plans-document-browse-confidence` · **Release branch:** `main`

## Goal

Every card on `/documents` carries a traffic-light circle: red for low, yellow for mid, green for high confidence. The ring is entirely in the band colour (the Chakra [colours](https://www.chakra-ui.com/docs/components/progress-circle#colors) pattern); the arc that marks the actual value is the darker part of it.

## Design

Paths under `apps/web/src/features/documents/`.

- `utils/confidenceBand.ts` (exported symbols get TSDoc — rule for `src/core`-style modules, applied here for clarity):
  - `export const LOW_MAX = 0.4`, `export const HIGH_MIN = 0.7`.
  - `export type ConfidenceBand = "low" | "mid" | "high"`; `bandFor(confidence: number): ConfidenceBand` — `< LOW_MAX` low, `< HIGH_MIN` mid, else high; non-finite input is treated as `0`; the value is clamped to `[0, 1]` first.
  - `export const BAND_PALETTE: Record<ConfidenceBand, "red" | "yellow" | "green">` and `percentOf(confidence): number` (rounded, clamped).
- `components/ConfidenceCircleView/ConfidenceCircle.tsx` (+ `index.ts` barrel, PascalCase folder): props `{ confidence: number }` only.
  ```tsx
  <ProgressCircle.Root value={percent} size="sm" colorPalette={BAND_PALETTE[band]} aria-label={...}>
    <ProgressCircle.Circle>
      <ProgressCircle.Track />
      <ProgressCircle.Range />
    </ProgressCircle.Circle>
    <ProgressCircle.ValueText />
  </ProgressCircle.Root>
  ```
  The recipe already paints `Track` with `colorPalette.muted` and `Range` with `colorPalette.solid` (`@chakra-ui/react` 3.37 `progress-circle` recipe), which is the "whole circle in the band colour, value as the darker sector" requirement. Verify that against `theme/` in a render test; do not override the recipe unless the muted tone is unreadable in dark mode — in that case add a slot-recipe override in `theme/` with a contrast assertion in `theme/theme.test.ts`.
  - `aria-label` and a visible/`title` text come from i18n: `documents.confidence_aria` ("Confidence {percent}%, {band}") and `documents.confidence_low|mid|high`.
- `DocumentCard.tsx` renders the circle at the trailing edge of the card header; the card stays one link (the circle is decorative plus labelled, not a second control).
- The detail page badge (`TagBadge` opacity gradient) is untouched.

## Tests

Happy path:
- `confidenceBand.test.ts`: `0.399 → low`, `0.4 → mid`, `0.699 → mid`, `0.7 → high`, `0 → low`, `1 → high`; `percentOf(0.456) → 46`.
- `ConfidenceCircle.test.tsx`: each band renders the matching `colorPalette` (assert through `emotionRules` / computed CSS variable of the track and range) and the percentage text; the root exposes `aria-valuenow`.
- `DocumentCard.test.tsx`: the card shows the circle with the card's confidence.

Negative path:
- `NaN`, `-0.2`, `1.7`, `Infinity` render without throwing, clamped to 0 or 100 and the right band.
- The circle is not a link or button: the card's only interactive element is the card link (`getAllByRole("link")` length unchanged).

## Verification

```bash
cd apps/web && npx vitest run src/features/documents/utils src/features/documents/components
./ci.sh
```

## Refactor gate

Scan `ConfidenceCircle.tsx` and `confidenceBand.ts` (Primitive Obsession on bare band strings → the `ConfidenceBand` type and palette record; Magic numbers → the two exported constants). Keep each function within 5 lines and the file under 100 lines.

## Commits

- `feat(web): confidence bands and a traffic-light ProgressCircle`
- `feat(web): show the confidence circle on each document card`

## Out of scope

Per-tag circles (D2 picks one circle per card); changing the thresholds; the detail page.
