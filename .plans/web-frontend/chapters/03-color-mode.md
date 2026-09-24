---
name: "Chapter 3 — Color mode"
overview: "Wire next-themes through components/ui/color-mode.tsx and replace the ColorModeProvider placeholder so semantic tokens respond to light and dark class."
todos:
  - id: next-themes
    content: "Add next-themes dependency and ColorModeProvider"
    status: completed
  - id: toggle
    content: "ColorModeToggle component with Button + icons"
    status: completed
  - id: bootstrap
    content: "Mount provider in AppBootstrap; remove placeholder ColorModeContext passthrough"
    status: completed
  - id: tests
    content: "useColorMode tests with mocked next-themes"
    status: completed
isProject: false
---

# Chapter 3 — Color mode

**Repo:** `redtape` (`apps/web`) · **Branch:** `feat/web-visual-color-mode` · **Status:** done

**Depends on:** [2](02-theme-system.md) · **Architecture:** [../00-architecture.md](../00-architecture.md) §6.3 · **Rollout:** [../01-rollout.md](../01-rollout.md)

---

## Goal

Light/dark mode works via `class` on `document.documentElement`, driving Chakra semantic tokens with
`_dark` values. A ghost `Button` toggle switches modes. Placeholder
[ColorModeContext.tsx](../../apps/web/src/contexts/ColorModeContext.tsx) is replaced by real
`next-themes` integration ported from `rsb-test-storage/frontend/src/components/ui/color-mode.tsx` (read-only reference).

## Design decisions

**next-themes, not a custom store.** Matches test-storage and Chakra v3 docs. Alternative: manual
`localStorage` + React context — more code, same behavior.

**Toggle lives in ui module; mount in shell chapter 4.** This chapter ships the provider + toggle
component + tests; chapter 4 places toggle in header unless you mount early for manual QA (either
order is fine if header placement completes in 4).

**Forced theme handling.** When `forcedTheme` is set, `toggleColorMode` must not throw; test
documents no-op behavior.

## Files

**Add**

| Path | Contents |
| --- | --- |
| `apps/web/src/components/ui/color-mode.tsx` | `ColorModeProvider`, `useColorMode` (port from reference) |
| `apps/web/src/components/layout/ColorModeToggle.tsx` | Ghost `Button`, sun/moon icons |
| `apps/web/src/components/ui/color-mode.test.tsx` | Hook behavior with mocked `useTheme` |

**Edit**

| Path | Change |
| --- | --- |
| `apps/web/package.json` | `next-themes` |
| `apps/web/src/contexts/ColorModeContext.tsx` | Re-export from ui module or delete and update imports |
| `apps/web/src/app/AppBootstrap.tsx` | Wrap tree with `ColorModeProvider` |
| `apps/web/src/test/renderWithProviders.tsx` | Include `ColorModeProvider` |

**Do not edit** — semantic token definitions (chapter 2 except fixing missing `_dark` if tests fail).

## Red tests

| Test | Asserts |
| --- | --- |
| `useColorMode · exposes light as default in test stub` | Mock returns `light`; hook reports `colorMode === 'light'` |
| `useColorMode · toggle requests dark theme` | `toggleColorMode` calls `setTheme('dark')` when resolved light |
| `useColorMode · forced theme rejects toggle without throwing` | When `forcedTheme` set, toggle is no-op, no exception |
| `ColorModeToggle · renders sun icon in light mode` | Accessible label present; icon matches mode |

## Green

1. Add `next-themes`; port provider/hook.
2. Implement toggle button (not yet in header — or add to AppLayout if doing manual check).
3. Replace placeholder provider in bootstrap and test helper.
4. Unit tests with vi.mock on `next-themes`.

## Refactor gate

- **Two color-mode files.** If both `contexts/ColorModeContext.tsx` and `ui/color-mode.tsx` exist,
  collapse to one export path — ✅ likely: delete context folder re-export or make context a one-line
  re-export only if import paths are widespread.

Report outcome; re-run `npm run test -- src/components/ui/color-mode.test.tsx`.

**Outcome:** deleted `contexts/ColorModeContext.tsx`. `ColorModeProvider` and `useColorMode` live only in `components/ui/color-mode.tsx`. `toggleTheme` holds the forced-theme no-op; `iconFor` holds the sun/moon choice. No further split — both files stay under 50 lines, and each decision has two arms. Narrow suite re-run: 4 passed.

## Verification

```bash
cd apps/web
npm run test -- src/components/ui/color-mode.test.tsx
npm run build
cd ../.. && ./ci.sh
# Manual: toggle class on html; bg.canvas flips between #E3E2DF and dark semantic
```

## Out of scope

Header layout and sticky nav (chapter 4). Restyling LocaleSwitcher.

## Git workflow

```bash
git checkout -b feat/web-visual-color-mode
```

```text
feat(web): wire next-themes color mode provider and toggle

test(web): cover useColorMode toggle and forced-theme no-op
```
