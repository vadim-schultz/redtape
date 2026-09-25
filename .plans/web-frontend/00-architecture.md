---
name: Web Frontend Visual Alignment — Architecture
overview: "Visual contract for restyling apps/web: red Chakra theme with Iceberg headings and Inter body, semantic tokens ported from test-storage structure, native namespace imports, and polished Wave 2 screens without new product features."
isProject: true
---

# Web Frontend Visual Alignment — Architecture

**Repo:** `redtape` (`apps/web`). **Reference (read-only):** `rsb-test-storage/frontend/src/theme/`.

**Sibling docs:** [01-rollout.md](01-rollout.md) — chapter sequence · [gaps-and-decisions.md](gaps-and-decisions.md) — settled brand · [chapters/](chapters/) — executable plans · Product IA (tree, social): [docs/planning/directions/web-frontend/README.md](../../docs/planning/directions/web-frontend/README.md).

**Status:** chapters 1–4 done; chapters 5–10 planned.

---

## 1. Problem statement

Wave 2 shipped working document list/detail UI and a location filter, but the app mounts Chakra
`defaultSystem` in [AppBootstrap.tsx](../../apps/web/src/app/AppBootstrap.tsx). Screens use generic
`Heading size`, invalid `color="muted"`, and a flat header. The result reads as an unstyled template.

The target is the **same information architecture** with a deliberate product skin: red-dominated
palette, Iceberg display type, Inter body (matching test-storage), semantic surfaces and shadows, and
Chakra compound components — without copying test-storage domain chrome (lifecycle matrix, status
bar, Nucleus title, R&S blue).

---

## 2. Screen inventory (in scope)

| Surface | Key files | Visual job |
| --- | --- | --- |
| Bootstrap / providers | `app/AppBootstrap.tsx`, `contexts/*` | Custom `system`, color mode, unchanged data providers |
| App shell | `components/layout/AppLayout.tsx`, `LocaleSwitcher.tsx` | Sticky `nav.bg`, Iceberg wordmark, canvas main |
| Documents list | `DocumentsListPage`, `DocumentsListView`, `DocumentsListQueryStatus`, `DocumentCard` | Page title, card grid, loading/empty/error |
| Location filter | `location-picker/*` | Card-framed `Select` + `Field` labels |
| Document detail | `DocumentDetailView`, `DocumentHeader`, `DocumentBreadcrumb`, requirements | Breadcrumb, section headers, requirement cards/links |
| Loading shell | `main.tsx` `MinimalAppShell` | Align spinner/colors with theme tokens (chapter 4+) |

Routes and hooks stay unchanged. No new paths except an explicit **not-found** view for unknown URLs
(chapter 1).

---

## 3. Brand palette

Anchors from the red board ([gaps-and-decisions.md](gaps-and-decisions.md) D2):

```text
#5D001E  deep     nav (light), primary.900-ish
#E3E2DF  canvas   bg.canvas (light)
#E3AFBC  blush    subtle surfaces, muted accents
#9A1750  wine     primary.500, interactive.default
#EE4C7C  accent   accent.500, focus.ring base
```

**Primary scale:** generate 50–950 steps between blush/wine/deep (same *shape* as test-storage
`customColors.primary`, different hex endpoints). **`primary.500` must equal `#9A1750`.**

**Accent scale:** centered on `#EE4C7C`.

**Semantic tokens:** port roles from test-storage `semantic-tokens/colors.ts` — `bg.*`, `surface.*`,
`text.*`, `border.*`, `interactive.*`, `focus.*`, `primary.*`, `accent.*`, `status.*`, `nav.*`,
`input.*` — and rewire `{colors.primary.*}` references to the new primary scale. Light canvas uses
`#E3E2DF` for `bg.canvas` / `bg.subtle` where the reference used gray-50.

---

## 4. Typography

| Token | Font stack |
| --- | --- |
| `fonts.heading` | `'Space Grotesk', system-ui, sans-serif` |
| `fonts.brand` | `'Iceberg', system-ui, sans-serif` (wordmark only) |
| `fonts.body` | `'Inter', system-ui, -apple-system, sans-serif` |
| `fonts.mono` | `'JetBrains Mono', ui-monospace, …` |

Load via `theme/fonts.ts` importing `@fontsource/iceberg`, `@fontsource/inter`,
`@fontsource/jetbrains-mono` (Inter weights 400–700 as in test-storage).

**Text styles** (port names from test-storage `theme/index.ts`):

| Style | Font | Notes |
| --- | --- | --- |
| `appTitle` | brand | Wordmark; Iceberg is single-weight, `fontWeight: normal`, red |
| `pageTitle` | heading | List/detail H1; bold, red (large text only) |
| `sectionHeader` | heading | Section headings on the canvas; near-black |
| `subsectionHeader` | heading | Card titles; near-black |
| `body`, `caption` | body | Descriptions, counts |
| `mono`, `code` | mono | IDs if shown later |

Red is reserved for large text (`appTitle`, `pageTitle`); section and card headings are near-black.

**Cards.** Every card uses `components/data-display/AppCard` (linked cards lift on hover). The detail page shows one card per document / required document, with section headings on the bare canvas.

---

## 5. Motion and elevation

Port shadow tokens (`subtle`, `card`, `elevated`, `dropdown`, `modal`) and motion durations/easings
from test-storage `tokens/shadows.ts` and `tokens/motion.ts`. Document cards use `shadow="card"` and
`_hover` with `shadow="elevated"` and optional `translateY(-2px)` — same interaction language as
test-storage workflow cards, implemented with `Card.Root` namespace imports.

Focus: `focus.ring` semantic token derived from accent (`#EE4C7C` at ~40% alpha). Global
`:focus-visible` in [style.css](../../apps/web/src/style.css) references Chakra CSS variables where
possible.

---

## 6. Component rules

### 6.1 Namespace imports

```tsx
import { Card, Select, EmptyState, Alert, Breadcrumb, Field, Button } from '@chakra-ui/react';

<Card.Root bg="surface.base" shadow="card">
  <Card.Body>
    <Card.Title textStyle="pageTitle">{title}</Card.Title>
    <Card.Description color="text.secondary">{description}</Card.Description>
  </Card.Body>
</Card.Root>
```

Forbidden at call sites in chapters 6–10: `CardRoot`, `CardBody`, `CardTitle` flat imports.

### 6.2 Prefer Chakra over custom markup

| Need | Use |
| --- | --- |
| Document row | `Card.Root` + link wrapper |
| Empty list | `EmptyState.Root` / `EmptyState.Content` |
| Load failure | `Alert.Root` + `status.error` tokens |
| Jurisdiction path | `Breadcrumb.Root` |
| Select label | `Field.Root` + `Field.Label` |
| Loading | `Skeleton` |

Do not port test-storage `components/ui/chakra.tsx` adapter module; bind motion via `_hover`
transition props and theme duration tokens.

### 6.3 Color mode

`next-themes` with `attribute="class"`, wired through `components/ui/color-mode.tsx` (pattern from
test-storage). Semantic tokens use `_dark` condition values like the reference.

---

## 7. Testing contract

After chapter 1:

- **Runner:** Vitest + jsdom, config in `vite.config.ts`.
- **Render helper:** `src/test/renderWithProviders.tsx` mounts the same stack as `AppBootstrap` (or
  a slim variant with `MemoryRouter`).
- **Theme tests:** assert token values and text-style weights without rendering full pages where a
  unit test suffices.
- **Component tests:** colocated `*.test.tsx` beside changed components; happy + negative pairs per
  [tdd.mdc](../../.cursor/rules/tdd.mdc).

Gate: `cd apps/web && npm test`, then `./ci.sh` from repo root.

---

## 8. Non-goals

- New features (tree, proposals, votes, auth).
- Replacing hand-written API types with OpenAPI codegen.
- DataTable, pagination chrome, or matrix navigation from test-storage.
- Copying R&S `#00549F` or "Nucleus Verification" branding.
- Monorepo `@/` alias unless chapter 1 adds it for consistency with tests (optional; use relative
  imports if alias not present today).

---

## 9. File layout (target)

```text
apps/web/src/
  theme/
    index.ts              createSystem export
    fonts.ts              fontsource imports
    tokens/               colors (red primary/accent), shadows, motion
    semantic-tokens/      ported roles, recolored
  components/
    layout/               AppLayout, AppHeader (split from monolith), LocaleSwitcher
    ui/color-mode.tsx     next-themes + useColorMode
  test/
    setup.ts
    renderWithProviders.tsx
```

Feature folders keep their structure; chapters restyle in place.
