---
name: Floating Nav — Architecture
overview: "Replace the sticky top toolbar with two circular floating buttons (brand R, burger menu), move colour mode and language into the menu, remove the Matrix view, and drop the Iceberg wordmark font."
isProject: false
---

# Floating Nav — Architecture

**Rollout:** [01-rollout.md](01-rollout.md) · **Decisions:** [gaps-and-decisions.md](gaps-and-decisions.md) · **Chapters:** [chapters/](chapters/)

---

## 1. Why

The header in [AppLayout](../../apps/web/src/components/layout/AppLayout.tsx) holds a wordmark, a matrix
link, a locale select and a colour toggle. It costs a full row of vertical space on every screen, crowds
phone widths, and the Iceberg wordmark clashes with Inter (body) and Space Grotesk (headings). The Matrix
page is also confusing for an average user; the domain / life-situation filter chips on the documents list
([DocumentFilters](../../apps/web/src/features/documents/components/documents-list/document-filters/DocumentFilters.tsx))
are the clearer path.

## 2. Target UI

```
┌──────────────────────────────────────┐
│ (R)                              (≡) │   two fixed circles, no bar
│                                      │
│   page content uses full width       │
└──────────────────────────────────────┘
```

| Element | Behaviour |
| --- | --- |
| Brand button (top-left) | Circle containing the gothic **R** SVG in Swiss red (`primary.500`, `#DA291C`). Links to `/` (redirects to `/documents`). |
| Menu button (top-right) | Circle with burger icon. Opens a Chakra `Menu`. |
| Menu → colour mode | A `Switch` row: sun icon on the left, moon on the right. Off = light, on = dark. Toggling does not close the menu. |
| Menu → language | Sub-menu ([Chakra Menu submenu](https://chakra-ui.com/docs/components/menu#submenu)) listing locales from `/api/v1/locales`; the active one is checked. |

No other navigation. The Matrix link and route are gone.

## 3. Component tree (one per file)

```
AppLayout
├─ FloatingControls
│  ├─ BrandButton            (BrandMark svg + RouterLink "/")
│  └─ AppMenu                (Menu.Root, burger trigger)
│     ├─ ColorModeSwitch     (Switch + FaSun / FaMoon)
│     ├─ Menu.Separator
│     └─ LocaleSubmenu       (Menu.Root nested, Menu.TriggerItem)
└─ main  (ColdStartNotice + children)
```

`ColorModeToggle` and the select-based `LocaleSwitcher` are replaced, not kept alongside.

## 4. Visual contract

- **Colour.** The R uses the existing `primary` scale (Swiss red `#DA291C`) through a semantic token; no new
  hex values. The circle surface reuses `nav.bg` / `nav.border` so it reads in both modes. Swiss red stays
  off backgrounds ([navigation.ts](../../apps/web/src/theme/semantic-tokens/navigation.ts)).
- **Typography.** The `appTitle` text style, the `brand` font token and `@fontsource/iceberg` are removed.
  Inter and Space Grotesk remain.
- **Size and placement.** 44px circles (touch target), `position: fixed`, offset by spacing plus
  `env(safe-area-inset-*)`, `zIndex="sticky"` (below the menu popover and dialogs). A subtle shadow
  separates the circles from scrolling content.
- **Content clearance.** `main` gets top padding equal to the button size plus offset, so the first
  content line never sits under a button.

## 5. Accessibility

- No `banner` landmark any more; `main` stays. The brand link and menu trigger have accessible names
  (`nav.home`, new `common.menu`).
- Menu is keyboard operable through Chakra/Ark (Enter/Space/arrows open, Esc closes, Right arrow opens
  the language submenu, Left/Esc returns).
- The switch has an accessible name (`common.toggle_color_mode`); sun and moon icons are decorative
  (`aria-hidden`) so the state is conveyed by the switch's checked state.
- Focus rings use the existing focus tokens; contrast of the R on the circle surface is tested in
  light and dark.

## 6. Data and i18n

- No API change. The locale list still comes from the `["locales"]` query; failure hides the language item.
- New key `common.menu` in all four bundles (web fallback `en`/`de`, API seed `en`/`de`; a parity test
  enforces this). Keys `nav.matrix` and `matrix.*` are removed from all four.

## 7. Out of scope

Additional menu items (about, account), a landing page, backend matrix endpoint removal, list-card tags.
