# Web frontend visual alignment — gaps and decisions

**Architecture:** [00-architecture.md](00-architecture.md) · **Rollout:** [01-rollout.md](01-rollout.md)

---

## Settled decisions

### D1 — Structure from test-storage, brand from RedTape

Copy the **token layout** from `rsb-test-storage/frontend/src/theme/` (primitive tokens, semantic
tokens, shadows, motion, text styles). Do **not** copy R&S blue (`#00549F`). Recolor `primary`,
`accent`, `nav`, and light-mode canvas to the red board anchors below. `rsb-test-storage` is
read-only; port by copy into `apps/web`.

### D2 — Red palette anchors

| Role | Hex | Use |
| --- | --- | --- |
| Deep | `#5D001E` | Header/nav in light mode, darkest primary step, dark-mode depth |
| Canvas | `#E3E2DF` | Light `bg.canvas`, page background |
| Blush | `#E3AFBC` | Subtle surfaces, muted fills, secondary accents |
| Wine | `#9A1750` | `primary.500`, interactive default, links |
| Accent | `#EE4C7C` | `accent.500`, focus ring, high-emphasis highlights |

Dark mode inverts onto deep burgundy and wine — no second brand palette.

### D3 — Typography split

| Role | Face | Source |
| --- | --- | --- |
| Headings, section titles, wordmark | [Iceberg](https://fonts.google.com/specimen/Iceberg) | `@fontsource/iceberg` (weight 400 only) |
| Body, captions, UI labels | Inter | `@fontsource/inter` (same as test-storage) |
| Mono | JetBrains Mono | `@fontsource/jetbrains-mono` |

Iceberg has a single weight. Heading text styles use `fontWeight: normal`; emphasis comes from size,
letter-spacing, and color. Browser-synthesized bold on Iceberg is a defect.

### D4 — Native Chakra, namespace imports

Use Chakra v3 compound APIs: `Card.Root`, `Select.Root`, `EmptyState.Root`, `Alert.Root`,
`Breadcrumb.Root`, `Field.Root`. Do not import flat aliases (`CardRoot`, `CardTitle`). Do not
reimplement a component Chakra already ships. Custom wrappers only when they add a guard, token
binding, or multi-step behavior — not one-line renames.

### D5 — Scope of this suite

In scope: existing Wave 2 routes (`/documents`, `/documents/:id`), `AppLayout`, location picker,
locale switcher styling.

Out of scope (other strands / TBD child plans): dependency tree, social proposals, auth, activity
bar, data tables, new API endpoints, translating hardcoded `"Server error"`, `"State"`, `"District"`,
`"City"` (i18n strand).

### D6 — Reference import style is rejected

`WorkflowCard` in test-storage uses `CardRoot` from a flat import path. RedTape chapters use
`Card` namespace imports per D4 even when copying interaction patterns (hover lift, shadows).

---

## Open seams (not blocking visual chapters)

| Seam | Placeholder | Forcing condition |
| --- | --- | --- |
| Product branding beyond palette | Strand README still says "TBD" | Marketing sign-off; update strand README when settled |
| Dedicated 404 route vs redirect | Today `*` redirects to `/documents` | Chapter 1 introduces an explicit not-found view for unknown paths |
| `docs/planning/directions/web-frontend/01–04` TBD files | This suite is `.plans/web-frontend/`, not a replacement for product IA chapters | Expand strand files when building tree/social |
