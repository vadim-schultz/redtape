---
name: Floating Nav — Gaps and decisions
overview: "Settled decisions and open seams for replacing the toolbar with floating controls."
isProject: false
---

# Floating Nav — Gaps and decisions

**Architecture:** [00-architecture.md](00-architecture.md) · **Rollout:** [01-rollout.md](01-rollout.md)

## Settled

| # | Decision |
| --- | --- |
| D1 | The Matrix view is removed from the web app only (route, nav link, components, matrix hook, axis/cell utils, `matrix.*` keys). The backend matrix endpoint, the domain/situation hooks, `DocumentFilters` and `buildDocumentsHref` stay: filters and tag badges use them, and the matrix can return later. |
| D2 | "Swiss red" is the existing `primary.500` (`#DA291C`) token, not a new colour. The R takes it via a semantic token so dark mode may use a lighter step if contrast demands. |
| D3 | The brand button links to `/` (which redirects to `/documents`), so it stays correct if a real landing page arrives. |
| D4 | Floating buttons overlay content; there is no reserved bar. Mitigations: opaque circle surface with shadow, and top padding on `main`. |
| D5 | Colour mode is a `Switch` inside the menu with sun (left) and moon (right). Language is a submenu. Nothing else in the menu for now. |
| D6 | No `banner` landmark after the change; `main` remains, and both floating controls carry accessible names. |
| D7 | The Iceberg font, `brand` font token and `appTitle` text style are removed because the wordmark was their only use (verified by grep; re-verify in chapter 2). |
| D8 | The supplied R SVG is used as a component: white background `<rect>` removed, fill changed from `#1f3a5f` to `currentColor`, viewBox `0 0 65 77` kept. |

## Open seams

- **Overlap on very long titles.** Page titles start below the buttons through `main` padding; if a page
  needs a full-bleed header later, it must account for the fixed circles.
- **Menu growth.** If more items arrive, revisit whether the menu needs grouping.
- **Dormant matrix endpoint.** Decide later whether to delete it and its API tests.
- **Test for Chakra submenu.** Ark's submenu positioning is not exercised by jsdom; tests assert roles and
  keyboard behaviour, not geometry.
