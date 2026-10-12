---
name: Frontend UI menu — Architecture
overview: "Refine floating chrome and the app menu: remove a stray list chevron, single R menu trigger, eggs-style KeyValueRow panel with profile, documents, colour and language rows."
isProject: false
---

# Frontend UI menu — Architecture

**Rollout:** [01-rollout.md](01-rollout.md) · **Decisions:** [gaps-and-decisions.md](gaps-and-decisions.md) · **Chapters:** [chapters/](chapters/)

---

## 1. Why

The documents list shows a non-functional expand chevron beside the count. Floating chrome still uses two
circles (brand left, burger right) from [floating-nav](../floating-nav/00-architecture.md), while product
direction is one **R** control that opens the menu. The menu is a vertical list of `Menu.Item`s; the eggs
app uses a clearer **1 : 3** key–value row layout for panel settings.

## 2. Target UI

```
┌──────────────────────────────────────┐
│                                  (R) │   one fixed circle, opens menu
│                                      │
│   Documents list + filters           │
└──────────────────────────────────────┘

Menu panel (KeyValueRow × 4):
  Profile     | ✉  G  (or user icon when signed in)
  Documents   | Documents link · Suggest link
  Colour mode | sun — switch — moon
  Language    | 🇬🇧  🇩🇪  (ghost; selected highlighted)
```

| Element | Behaviour |
| --- | --- |
| Menu trigger | Top-right `IconButton` with `BrandMark`, `aria-label` = `common.menu`, `{...floatingSurface}`. No `FaBars`. No separate left home link — home via Documents row. |
| Profile row | Anonymous: `FaEnvelope` and `FaGoogle` → `/login` (UI-only; no OAuth). Authenticated: `FaRegUser` + compact sign-out (today’s account behaviour). Unconfigured: row omitted. |
| Documents row | Links to `/documents` and `/suggest`. |
| Colour row | Existing `ColorModeSwitch`; toggling does **not** close the menu. |
| Language row | Inline flag ghost buttons from `useLocalesQuery`; replaces nested `LocaleSubmenu`. |

## 3. Component tree (target)

```
FloatingControls
└─ AppMenu (Menu.Root, BrandMark trigger)
   └─ AppMenuPanel (VStack)
      ├─ ProfileMenuRow      (KeyValueRow)
      ├─ DocumentsMenuRow    (KeyValueRow)
      ├─ ColorModeMenuRow      (KeyValueRow + ColorModeSwitch)
      └─ LanguageMenuRow       (KeyValueRow + flag buttons)

apps/web/src/components/ui/KeyValueRow.tsx   (ported from eggs)
```

Replaced or inlined: `AccountMenuItem`, `SuggestMenuItem`, `LocaleSubmenu` as separate menu items.

## 4. Visual contract

- Reuse [`floatingSurface.ts`](../../apps/web/src/components/layout/floatingSurface.ts) for the trigger.
- `KeyValueRow`: `templateColumns="1fr 3fr"`, `data-testid="key-value-row"`, `alignItems="center"` (eggs).
- Menu content width: comfortable for two flag buttons and auth icons (~min width similar to eggs popover).

## 5. Accessibility

- Menu trigger keeps `common.menu`; keyboard behaviour via Chakra/Ark (unchanged expectations from [`AppMenu.test.tsx`](../../apps/web/src/components/layout/AppMenu.test.tsx)).
- Auth icons: accessible names (`auth.sign_in`, provider labels); decorative where redundant.
- Language flags: `aria-pressed` or radio semantics for the active locale.

## 6. Data and i18n

- New keys: `menu.profile`, `menu.colour_mode` (or reuse `common.toggle_color_mode` for label).
- Extend web fallback `en` / `de` and API seed if parity tests require.

## 7. Layering

Frontend only (`apps/web`). No API or auth backend changes. Google sign-in is **out of scope** (navigate to `/login` only).
