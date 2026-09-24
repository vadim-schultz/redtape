---
name: "Chapter 4 — App shell"
overview: "Sticky header on nav tokens, canvas main, Iceberg appTitle wordmark linking home, locale switcher and color toggle in the header cluster."
todos:
  - id: header
    content: "Extract or restyle AppHeader with nav.bg, border, sticky"
    status: completed
  - id: layout
    content: "AppLayout bg.canvas, main region, container widths"
    status: completed
  - id: loading
    content: "MinimalAppShell uses theme-aligned colors"
    status: completed
  - id: tests
    content: "AppLayout.test.tsx for header, main, wordmark link"
    status: completed
isProject: false
---

# Chapter 4 — App shell

**Repo:** `redtape` (`apps/web`) · **Branch:** `feat/web-visual-app-shell` · **Status:** done

**Depends on:** [2](02-theme-system.md), [3](03-color-mode.md) · **Architecture:** [../00-architecture.md](../00-architecture.md) §2 · **Rollout:** [../01-rollout.md](../01-rollout.md)

---

## Goal

The app frame matches the visual contract: deep/wine header band (`nav.bg`), `#E3E2DF` canvas main,
Iceberg `RedTape` wordmark linking to `/`, locale switcher and color toggle aligned in the header.
Empty page content still shows header + main landmarks.

## Design decisions

**Split header from AppLayout optional.** Reference uses `AppLayout/AppHeader.tsx`. Either extract
`AppHeader.tsx` or keep single file under ~100 LOC — extract if layout file grows past threshold.

**Wordmark is `Heading` + `textStyle="appTitle"` + `RouterLink`.** Not raw `size="md"`. Hover uses
`interactive.hover` token.

**No test-storage chrome.** No breadcrumb bar, status bar, lifecycle icons, or settings gear.

**Sticky header.** `position="sticky"`, `top={0}`, `zIndex="sticky"`, `nav.border` bottom border.

## Files

**Add**

| Path | Contents |
| --- | --- |
| `apps/web/src/components/layout/AppHeader.tsx` | Optional extraction |
| `apps/web/src/components/layout/AppLayout.test.tsx` | Shell tests |

**Edit**

| Path | Change |
| --- | --- |
| `apps/web/src/components/layout/AppLayout.tsx` | Canvas bg, sticky header, compose Header |
| `apps/web/src/main.tsx` | `MinimalAppShell` token-aligned colors |
| `apps/web/src/components/layout/LocaleSwitcher.tsx` | Spacing/size to match header cluster (no logic change) |

**Do not edit** — document list/card components (chapters 5–7).

## Red tests

| Test | Asserts |
| --- | --- |
| `AppLayout · renders RedTape with appTitle in the header` | Header contains wordmark; `textStyle` or computed font family includes Iceberg |
| `AppLayout · wordmark links to home` | Link `href`/`to` is `/` |
| `AppLayout · renders main landmark with children` | `main` contains passed children |
| `AppLayout · renders header when children empty` | Header + main both present with empty fragment child |
| `AppLayout · includes color mode toggle control` | Button with aria-label for color mode |

## Green

1. Restyle `AppLayout` with semantic backgrounds.
2. Implement header row: wordmark, `LocaleSwitcher`, `ColorModeToggle`.
3. Update loading shell colors.
4. Component tests via `renderWithProviders`.

## Refactor gate

- **AppLayout orchestration.** If header + main + container logic exceeds ~5 lines per function,
  extract `MainContent` box — mirror reference only if file >100 LOC.

Report outcome; re-run layout tests after extraction.

**Outcome:** `AppLayout.tsx` stayed a single ~45-line file — header, cluster, and main composition
each read as flat JSX with no branching, well under the extraction threshold, so no separate
`AppHeader.tsx` was added. Wordmark uses Chakra's `Heading asChild` wrapping `RouterLink` (not a
plain anchor wrapper) so `textStyle="appTitle"` and the `_hover` → `interactive.hover` token apply
directly to the rendered `<a>`. `LocaleSwitcher` picked up `size="sm"` on `Select.Root` to match the
`ColorModeToggle` button height in the cluster — no logic change. `MinimalAppShell` in `main.tsx`
swapped its blue/gray placeholder palette for the brand hex values directly (deep `#5D001E`, canvas
`#E3E2DF`, blush `#E3AFBC`, wine `#9A1750`) since it renders before `ChakraProvider` mounts and has
no access to semantic tokens; no test was added for it per the chapter's Red tests table. Full suite
re-run: 26 passed (7 files).

## Verification

```bash
cd apps/web
npm run test -- src/components/layout/AppLayout.test.tsx
npm run build
cd ../.. && ./ci.sh
npm run dev
```

Manual checklist:

- [ ] Header sticky on scroll
- [ ] Canvas background visible on list page
- [ ] Dark mode flips header and canvas semantically
- [ ] Wordmark navigates to `/` (redirects to documents)

## Out of scope

Page titles on list/detail (chapter 5). Document cards.

## Git workflow

```bash
git checkout -b feat/web-visual-app-shell
```

```text
feat(web): restyle app shell with nav tokens and Iceberg wordmark

test(web): assert AppLayout header, main, and home link
```
