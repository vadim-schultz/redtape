---
name: "Chapter 5 — Floating shell"
overview: "Remove the sticky header; mount the brand button top-left and a burger menu button top-right as fixed circles; the menu holds the colour switch and language submenu; main gets clearance padding."
todos:
  - id: menu
    content: "AppMenu: burger trigger, Menu.Root, colour switch, separator, language submenu"
    status: pending
  - id: floating
    content: "FloatingControls: fixed placement with safe-area offsets"
    status: pending
  - id: layout
    content: "AppLayout without header; main top padding"
    status: pending
  - id: i18n
    content: "common.menu key in four bundles"
    status: pending
  - id: cleanup
    content: "Delete ColorModeToggle and LocaleSwitcher"
    status: pending
isProject: false
---

# Chapter 5 — Floating shell

**Repo:** `redtape` (`apps/web`, `apps/api` seed data) · **Branch:** `feat/floating-nav-shell` · **Status:** planned

**Depends on:** [1](01-remove-matrix.md), [2](02-brand-button.md), [3](03-color-mode-switch.md), [4](04-language-submenu.md) · **Architecture:** [../00-architecture.md](../00-architecture.md) · **Rollout:** [../01-rollout.md](../01-rollout.md)

---

## Goal

No toolbar. Two floating circular buttons: the R on the left, a burger on the right that opens the menu.

## Design decisions

**Fixed placement.** `FloatingControls` renders two `position="fixed"` slots: `top` and `left` / `right` =
`{ base: 3, md: 4 }` plus `env(safe-area-inset-*)`, `zIndex="sticky"`. Menu content uses Chakra's popover
layer, above the buttons.

**Burger.** `IconButton rounded="full"` 44px, same surface, border and shadow as `BrandButton` (share one
style constant or recipe). Icon `FaBars`; aria-label `common.menu` (new key). Chakra `Menu.Root` with
`Menu.Trigger asChild`; `positioning` anchors bottom-end so the menu opens inward on narrow screens.

**Menu content.** `ColorModeSwitch` row, `Menu.Separator`, `LocaleSubmenu`. Nothing else (D5).

**Layout.** [AppLayout](../../../apps/web/src/components/layout/AppLayout.tsx) loses the
`<Box as="header">` block, the `Container`/`HStack` wrapper and the `nav.bg` header styling. `main` keeps
`flex="1"`, gains top padding `calc(44px + spacing)` so content clears the circles. `ColdStartNotice`
stays first in `main`. The pre-Chakra [LoadingShell](../../../apps/web/src/app/LoadingShell.tsx) is checked
for a matching header and simplified if it draws one.

**Landmarks.** No `banner`; keep `main` (D6).

## Files

**Add** — `components/layout/{FloatingControls,AppMenu}.tsx` (+ tests).

**Edit** — `AppLayout.tsx` + `AppLayout.test.tsx`, `LoadingShell.tsx` if needed, translation bundles
(`common.menu`).

**Delete** — `ColorModeToggle.tsx`, `LocaleSwitcher.tsx` and their tests (replaced by chapters 3 and 4).

## Red tests

| Test | Asserts |
| --- | --- |
| `AppLayout · renders no banner landmark` | Header removed, negative |
| `AppLayout · renders children inside main` | Kept from today |
| `FloatingControls · shows the brand link and the menu button` | Both by accessible name |
| `FloatingControls · buttons are fixed-position circles` | Style props / data attributes |
| `AppMenu · burger opens a menu with the colour switch and the language item` | Roles |
| `AppMenu · toggling the colour switch keeps the menu open` | Integration with chapter 3 |
| `AppMenu · choosing a language closes the menu and updates locale` | Integration with chapter 4 |
| `AppMenu · Escape closes and returns focus to the burger` | Keyboard |
| `AppMenu · language item is absent when the locales request fails` | Negative |
| `AppLayout · has no toolbar links (matrix, browse) left` | Nothing stale |
| `fallback · common.menu exists in en and de and matches API seed` | i18n parity |

## Green

1. `AppMenu` (burger, switch, submenu), test-first.
2. `FloatingControls` positioning.
3. Swap into `AppLayout`, remove header, add `main` padding, delete old components.

## Refactor gate

One component per file, ≤ ~100 LOC, methods ~5 LOC. No unused exports (`ColorModeToggle`, `LocaleSwitcher`).

## Verification

Unit tests, gate commands, `./ci.sh`. Manual on a 360px viewport and desktop, light and dark: buttons do not
overlap the first content line, menu opens inside the viewport, submenu reachable by touch and keyboard.

## Out of scope

New menu items; hide-on-scroll behaviour.

## Git workflow

Branch `feat/floating-nav-shell`; `test(web): describe floating shell`, then
`feat(web): replace toolbar with floating brand and menu buttons`; one PR.
