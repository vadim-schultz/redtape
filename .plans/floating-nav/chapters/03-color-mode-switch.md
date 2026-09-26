---
name: "Chapter 3 — Colour-mode switch"
overview: "Replace the colour-mode toggle button with a Chakra Switch flanked by a sun (left) and a moon (right), built to sit inside a menu without closing it."
todos:
  - id: switch
    content: "ColorModeSwitch with sun/moon icons, checked = dark"
    status: completed
  - id: menu-row
    content: "Menu-embeddable row that does not close the menu on toggle"
    status: completed
  - id: remove-old
    content: "Delete ColorModeToggle"
    status: pending
isProject: false
---

# Chapter 3 — Colour-mode switch

**Repo:** `redtape` (`apps/web`) · **Branch:** `feat/floating-nav-color-switch` · **Status:** shipped

**Depends on:** none · **Architecture:** [../00-architecture.md](../00-architecture.md) §2, §5 · **Rollout:** [../01-rollout.md](../01-rollout.md)

---

## Goal

Light / dark becomes a switch: sun on the left, moon on the right, thumb position shows the mode.

## Design decisions

**Chakra `Switch`.** Compound parts `Switch.Root`, `Switch.HiddenInput`, `Switch.Control`, `Switch.Thumb`,
with `FaSun` and `FaMoon` (react-icons, already a dependency) as sibling icons either side. The active side
is emphasised through colour tokens; icons are `aria-hidden`.

**State.** `checked = colorMode === "dark"`; `onCheckedChange` calls `setColorMode` from
[color-mode.tsx](../../../apps/web/src/components/ui/color-mode.tsx). Behind `forcedTheme`, `setColorMode`
is a no-op and the switch is disabled.

**Menu row.** Rendered as a `Menu.Item`-like row (`closeOnSelect={false}`, `onSelect` prevented) so
toggling leaves the menu open and the effect is visible. Keyboard: Space/Enter toggles.

**Accessible name.** `common.toggle_color_mode` (existing key) on the hidden input.

## Files

**Add** — `apps/web/src/components/layout/ColorModeSwitch.tsx` (+ test).

**Delete** — `ColorModeToggle.tsx` once unused (its usage in the header is replaced in chapter 5; until then
the header keeps importing it, so deletion happens in chapter 5's commit).

## Red tests

| Test | Asserts |
| --- | --- |
| `ColorModeSwitch · unchecked in light mode` | Checkbox role, `checked=false` |
| `ColorModeSwitch · click switches to dark and sets the dark class` | Mode changes on `<html>` |
| `ColorModeSwitch · click again returns to light` | Round trip |
| `ColorModeSwitch · renders sun and moon icons on each side` | Order in DOM: sun, switch, moon |
| `ColorModeSwitch · has accessible name and hides icons from AT` | Name present, icons `aria-hidden` |
| `ColorModeSwitch · disabled when the theme is forced` | Negative: no mode change |
| `ColorModeSwitch · toggling inside a menu keeps the menu open` | Covered in chapter 5 integration |

## Green

1. Switch with state wiring; then icons; then forced-theme disabled state.
2. Menu-row wrapper.

## Refactor gate

Component ≤ ~100 LOC, methods ~5 LOC, no nesting beyond one level.

## Verification

Unit tests, gate commands, `./ci.sh`.

## Out of scope

A "system" third option; mounting in the menu (chapter 5).

## Git workflow

Branch `feat/floating-nav-color-switch`; `test(web): describe colour-mode switch`, then
`feat(web): add colour-mode switch`; one PR.

## Progress notes

- `ColorModeSwitch` is Sun, `Switch`, Moon with `checked = dark`; icons are `aria-hidden` and dimmed when inactive.
- `useColorMode` gained `isForced` so the switch can disable itself under `forcedTheme` (additive, existing tests untouched).
- The menu-row wrapper is deferred to chapter 5: `Menu.Item` needs a `Menu.Root`, which does not exist until the shell is
  built, so `closeOnSelect={false}` cannot be tested here. `ColorModeToggle` deletion stays in chapter 5 as planned.
- Refactor gate: component is ~30 LOC, no nesting beyond one level.
- Tests must run via `npm test` (sets `--no-experimental-webstorage`; plain `npx vitest` fails on Node 26).
