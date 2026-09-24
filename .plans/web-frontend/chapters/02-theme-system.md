---
name: "Chapter 2 — Theme system"
overview: "Port test-storage token layout into apps/web with red primary/accent, Iceberg heading and Inter body fonts, text styles, shadows, and motion; mount custom system on ChakraProvider."
todos:
  - id: tokens
    content: "theme/tokens and semantic-tokens recolored to red anchors"
    status: completed
  - id: fonts
    content: "fonts.ts with fontsource iceberg, inter, jetbrains-mono"
    status: completed
  - id: system
    content: "createSystem export; AppBootstrap uses system not defaultSystem"
    status: completed
  - id: tests
    content: "theme/token tests for primary.500, bg.canvas, heading weight"
    status: completed
isProject: false
---

# Chapter 2 — Theme system

**Repo:** `redtape` (`apps/web`) · **Branch:** `feat/web-visual-theme-system` · **Status:** done

**Depends on:** [1](01-test-harness.md) · **Architecture:** [../00-architecture.md](../00-architecture.md) §3–5 · **Rollout:** [../01-rollout.md](../01-rollout.md)

---

## Goal

Chakra runs a RedTape `system`: wine primary (`#9A1750`), accent (`#EE4C7C`), canvas `#E3E2DF`,
Iceberg on heading tokens, Inter on body. `defaultSystem` is gone from `AppBootstrap`. Token tests
lock anchor hex values and forbid bold heading text styles.

## Design decisions

**Port structure, replace hex.** Copy file layout from `rsb-test-storage/frontend/src/theme/` and
rewrite `tokens/colors.ts` primary/accent scales. Do not symlink or import from test-storage.

**Primary.500 is `#9A1750`.** Generate 50–950 steps between blush, wine, and deep `#5D001E` using the
same step *pattern* as reference primary scale (lighter steps toward blush `#E3AFBC`, darker toward
deep).

**Iceberg weight discipline.** `textStyles.appTitle`, `pageTitle`, `sectionHeader` set
`fontFamily: 'heading'` and `fontWeight: 'normal'` (or omit weight). Alternative: bold headings —
rejected ([gaps-and-decisions.md](../gaps-and-decisions.md) D3).

**Split textStyles if `index.ts` exceeds ~100 LOC.** Extract `textStyles.ts` during port (reference
`index.ts` already mixes concerns).

## Files

**Add**

| Path | Contents |
| --- | --- |
| `apps/web/src/theme/index.ts` | `defineConfig` + `createSystem` |
| `apps/web/src/theme/fonts.ts` | fontsource imports |
| `apps/web/src/theme/tokens/index.ts`, `colors.ts`, `shadows.ts`, `motion.ts` | Red primary/accent; shadows/motion from reference |
| `apps/web/src/theme/semantic-tokens/index.ts`, `colors.ts` | Ported roles; light `bg.canvas` → `#E3E2DF`; `nav.bg` uses deep/wine |
| `apps/web/src/theme/textStyles.ts` | Optional split from index |
| `apps/web/src/theme/theme.test.ts` | Token and textStyle assertions |

**Edit**

| Path | Change |
| --- | --- |
| `apps/web/package.json` | `@fontsource/iceberg`, `@fontsource/inter`, `@fontsource/jetbrains-mono` |
| `apps/web/src/app/AppBootstrap.tsx` | `import { system } from '../theme'`; `ChakraProvider value={system}` |
| `apps/web/src/test/renderWithProviders.tsx` | Same `system`, so tests mount the production theme |
| `apps/web/src/main.tsx` | Optional: align `MinimalAppShell` colors to canvas/wine (full polish ch.4) |

**Do not edit** — feature components (chapters 5–10). Delete placeholder `components/ui/color-mode.tsx` export of `theme: unknown` only if replacing in ch.3.

## Red tests

| Test | Asserts |
| --- | --- |
| `theme · primary.500 is wine #9A1750` | Parsed token value equals `#9A1750` |
| `theme · accent.500 is #EE4C7C` | Accent anchor |
| `theme · light bg.canvas is #E3E2DF` | Semantic token base value |
| `theme · heading font token names Iceberg` | `fonts.heading` stack includes Iceberg |
| `theme · body font token names Inter` | `fonts.body` stack includes Inter |
| `theme · pageTitle text style does not set bold weight` | `fontWeight` absent or `normal` |
| `theme · rejects unregistered semantic token lookup` | Accessing invented token yields undefined / test documents no value |

## Green

1. Copy reference token files; replace color scales and semantic wiring per architecture §3.
2. Add fontsource dependencies; import `fonts.ts` from `main.tsx` or theme entry.
3. Export `system`; switch `ChakraProvider`.
4. Theme unit tests reading exported config or using Chakra token resolution API as appropriate.

Fix invalid props in existing components only if build fails (`color="muted"` → `text.muted` or
`text.secondary`) — minimal mechanical fixes allowed in this chapter for green CI.

## Refactor gate

- **`semantic-tokens/colors.ts` size.** If over ~100 LOC, split by concern (`surfaces.ts`, `status.ts`)
  only when file exceeds threshold — reference is already large; splitting is likely ✅ outcome.
- **`theme/index.ts`.** Must not declare colors and textStyles if both grow — extract textStyles.

Report outcome; re-run `npm run test -- src/theme/theme.test.ts` after each split.

**Outcome:** split semantic colors by role at port (`surfaces`, `text`, `borders`, `interactive`, `focus`, `palettes`, `status`, `badge`, `navigation`, `fields`, `table`). `colors.ts` is the aggregate (28 lines). `textStyles.ts` holds heading styles at `fontWeight: normal`; `theme/index.ts` is 56 lines and only assembles the system. `mode()`, `palette()`, `statusColors()`, and `badgeColors()` cover the repeated light/dark shapes. Inlined the one-line `tokenValue` test wrapper. Narrow suite re-run after that inline: 7 passed.

## Verification

```bash
cd apps/web
npm run test -- src/theme/theme.test.ts
npm run typecheck && npm run build
cd ../.. && ./ci.sh
npm run dev   # confirm Inter body and Iceberg on manual Heading textStyle probe if added temporarily
```

## Out of scope

`next-themes` (chapter 3). Component-level `textStyle` usage (chapters 4–5). Card/shell layout.

## Git workflow

```bash
git checkout main && git pull
git checkout -b feat/web-visual-theme-system
```

```text
feat(web): add red Iceberg/Inter Chakra theme system

test(web): assert brand token anchors and heading weight discipline
```
