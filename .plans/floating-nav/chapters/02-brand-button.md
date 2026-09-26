---
name: "Chapter 2 — Brand button"
overview: "A circular button containing the gothic R SVG in Swiss red that links to the front page; removes the Iceberg wordmark, its text style, font token and dependency."
todos:
  - id: mark
    content: "BrandMark svg component (currentColor, no background rect)"
    status: pending
  - id: button
    content: "BrandButton: circular link to / with accessible name"
    status: pending
  - id: token
    content: "Semantic token for the mark colour (primary.500, dark contrast checked)"
    status: pending
  - id: cleanup
    content: "Remove appTitle text style, brand font token and @fontsource/iceberg"
    status: pending
isProject: false
---

# Chapter 2 — Brand button

**Repo:** `redtape` (`apps/web`) · **Branch:** `feat/floating-nav-brand-button` · **Status:** planned

**Depends on:** none · **Architecture:** [../00-architecture.md](../00-architecture.md) §2, §4 · **Rollout:** [../01-rollout.md](../01-rollout.md)

---

## Goal

Replace the "Redtape" wordmark with a circle holding the gothic **R**, coloured with the same Swiss red as
the rest of the brand. Clicking it goes to the front page.

## Design decisions

**SVG as a component.** The supplied file (`1456Gutenberg-Bold-R.svg`, viewBox `0 0 65 77`) has a white
`<rect>` background and a hardcoded `#1f3a5f` fill. `BrandMark` keeps only the `<path>`, sets
`fill="currentColor"`, and is `aria-hidden` (the button carries the name). Color comes from the parent so
the mark follows the theme token.

**Colour token.** Add `brand.mark` semantic token = `primary.500` (`#DA291C`) in light; in dark use
`primary.400` only if the contrast test against `nav.bg` (`gray.900`) demands it (D2).

**Circle button.** Chakra `IconButton asChild` wrapping a router `Link to="/"`; `rounded="full"`, 44px,
`nav.bg` surface, `nav.border` border, subtle shadow, `hoverMotion`. Placement is chapter 5; this
component is position-agnostic.

**Font cleanup.** Grep confirmed the wordmark is the only use of Iceberg: remove `appTitle` in
[textStyles.ts](../../../apps/web/src/theme/textStyles.ts), the `brand` font token in
[theme/index.ts](../../../apps/web/src/theme/index.ts), the import in `theme/fonts.ts`, the
`@fontsource/iceberg` dependency, and update theme tests and comments.

## Files

**Add** — `apps/web/src/components/layout/BrandMark.tsx`, `BrandButton.tsx` (+ tests),
semantic token entry in `theme/semantic-tokens/`.

**Edit** — `theme/textStyles.ts`, `theme/index.ts`, `theme/fonts.ts`, `package.json` / lockfile, theme tests.
(The current header keeps a plain text link until chapter 5 replaces it; the `appTitle` removal
therefore moves the header to `pageTitle`-free plain `Heading` styling only if needed to stay green.)

## Red tests

| Test | Asserts |
| --- | --- |
| `BrandButton · links to /` | `href="/"` |
| `BrandButton · has accessible name nav.home` | Role link with label, svg is `aria-hidden` |
| `BrandMark · fills with currentColor and has no background rect` | Negative on the source SVG quirks |
| `BrandButton · mark colour resolves to Swiss red in light mode` | Token → `#DA291C` |
| `theme · brand.mark meets 3:1 contrast on nav.bg in light and dark` | Contrast for both modes |
| `theme · no appTitle text style or brand font token` | Cleanup, negative |

## Green

1. `BrandMark`, then `BrandButton`; each test-first.
2. Token; contrast test decides the dark step.
3. Remove Iceberg pieces; theme tests updated.

## Refactor gate

One component per file, each under ~100 LOC. `npm ls @fontsource/iceberg` is empty.

## Verification

Unit tests, gate commands, `./ci.sh`. Manual: render `BrandButton` in both colour modes.

## Out of scope

Placement and stacking (chapter 5); a favicon update from the same SVG (noted as follow-up).

## Git workflow

Branch `feat/floating-nav-brand-button`; `test(web): describe brand button`, then
`feat(web): add brand R button and drop Iceberg`; one PR.
