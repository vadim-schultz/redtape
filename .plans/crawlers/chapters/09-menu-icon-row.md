---
name: "Chapter 9 — Menu icon row"
overview: "Render the Documents menu row's icons (browse, suggest, and all discovery links) in one unbroken HStack, and record the rule that every new navigation link is a react-icons button in that row."
todos:
  - id: single-row
    content: "DocumentsMenuRow uses one HStack; DiscoveryAdminMenuLinks returns icon buttons instead of its own HStack"
    status: pending
  - id: width
    content: "Pick and verify a width strategy so six icons fit"
    status: pending
  - id: convention
    content: "Write the navigation-link convention into the architecture doc"
    status: pending
isProject: false
---

# Chapter 9 — Menu icon row

**Repo:** `redtape` (`apps/web`) · **Branch:** `feat/crawlers-menu-icon-row` · **Status:** planned

**Depends on:** none (lands before [10](10-admin-documents-list.md)) · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/crawlers`

## Goal

In the start menu the "Documents" row shows its icons on two lines, which looks untidy. The cause is in [DocumentsMenuRow.tsx](../../../apps/web/src/components/layout/menu/DocumentsMenuRow.tsx): a `VStack` holds one `HStack` (browse, suggest) followed by [DiscoveryAdminMenuLinks](../../../apps/web/src/features/discovery-admin/components/DiscoveryAdminMenuLinks.tsx), which renders its own second `HStack`. The next chapter adds a sixth icon, so the row must be right first.

## Contract

- `DocumentsMenuRow` renders **one** `HStack` (`gap="1"`, `flexWrap="nowrap"`) inside `KeyValueRow` containing the browse and suggest buttons followed by the discovery links. The wrapping `VStack` goes away.
- `DiscoveryAdminMenuLinks` renders a fragment of `IconButton`s built from `DISCOVERY_MENU_LINKS` and no container of its own. Its three views keep their meaning: `links` renders the buttons, `unavailable` renders the existing muted hint in the same row, `hidden` renders nothing. The probe and authorization behaviour is untouched.
- **Width budget.** `KeyValueRow` uses `templateColumns="1fr 3fr"` inside `AppMenuPanel` (`minW="18rem"`, `p="3"`), which leaves roughly 189 px for the value column. Six `size="sm"` buttons need about 212 px (6 × 32 px plus five 4 px gaps). Choose one of: `size="xs"` buttons, a wider `AppMenuPanel` (`minW="22rem"`), or `templateColumns="auto 1fr"` for this row. Decide with a browser check at a phone viewport, because jsdom cannot assert wrapping. Record the choice and the measured widths in the ledger.
- **Convention (written into [00-architecture.md](../00-architecture.md) §9 and the docs sync):** every new navigation link is a `react-icons` `IconButton asChild` wrapping a `RouterLink`, with a translated `aria-label` and `title`, added to the config array and rendered in this single `HStack` row. Never a new row, never a text link.
- Icons come from the installed `react-icons/fa` family; no new dependency.

## TDD loops

### Loop A — One row

**Red** (new `apps/web/src/components/layout/menu/DocumentsMenuRow.test.tsx`)

1. `documents menu row renders browse suggest and discovery links in one container` — all link elements share the same parent element.
2. `documents menu row renders only browse and suggest when the discovery probe is hidden` — no extra container.
3. `documents menu row keeps the unavailable hint in the same row` — the hint's parent is the shared container.
4. `every link keeps its aria-label and title` — accessibility regression guard.

**Green:** remove the `VStack`, return the discovery buttons as a fragment.

**Refactor:** if the base buttons and the discovery buttons share markup, extract one `MenuIconLink` component and drive both from config. Keep each component under about a hundred lines.

### Loop B — Width

Not testable in jsdom. Verify in the browser at 360 px and desktop widths, in light and dark mode and both locales; attach the measured widths to the ledger.

## Verification

```bash
cd apps/web && npm run test -- src/components/layout/menu src/features/discovery-admin && npm run lint && npm run format:check && npm run typecheck && npm run build
gh pr checks --watch
```

Live gate: open the deployed menu as an allowlisted admin and as a signed-out user; the first shows one row of icons, the second shows two icons.

## Out of scope

The Documents destination itself (chapter 10), restyling other menu rows, changing the admin probe.
