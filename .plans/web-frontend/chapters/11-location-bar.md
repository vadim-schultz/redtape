---
name: "Chapter 11 — Location bar"
overview: "Location picker becomes a compact card-less pill: static country segment (flag + localized name) followed by cascading State, District and City selects."
todos:
  - id: cascade-hook
    content: "Extract useLocationCascade from LocationPicker"
    status: done
  - id: segments
    content: "CountrySegment (flag + Intl.DisplayNames) and SelectSegment"
    status: done
  - id: bar
    content: "LocationBar pill with dividers and reset; rewire LocationPicker"
    status: done
  - id: i18n
    content: "location.* keys in de/en seed translations"
    status: done
  - id: cleanup
    content: "Remove LocationPickerHeader, LocationSelect*, legacy LocationPicker monolith"
    status: done
isProject: false
---

# Chapter 11 — Location bar

**Repo:** `redtape` (`apps/web`) · **Branch:** `feat/web-location-bar` · **Status:** done

**Depends on:** [8](08-location-picker.md), [10](10-focus-and-motion.md) · **Rollout:** [../01-rollout.md](../01-rollout.md)

## Goal

Replace the card of stacked, labelled selects with one compact rounded pill:
`( 🇩🇪 Deutschland | State | District | City )  ×`. Country is static (signals future multi-country
support); each select activates once the preceding one has a value.

## Design decisions

- **Cascade lives in `useLocationCascade`**, so `LocationPicker` only wires queries to `LocationBar`.
- **Country name** comes from `Intl.DisplayNames([locale], { type: "region" })`; no backend change.
  The flag is a derived emoji, isolated in `CountryFlag` so it can be swapped later.
- **Labels are placeholders and `aria-label`s** via new `location.*` keys (`label`, `state`,
  `district`, `city`, `reset`); this replaces the misused `documents.list_title` / `common.cancel`.
- **No placeholder item in the menu**; clearing is done with the `×` reset button.
- **No `SelectSegmentLoading` wrapper**: a one-use `Spinner` stays inline in `SelectSegment`.

## Component tree

```
location-picker/
  LocationPicker.tsx
  location-bar/
    LocationBar.tsx, SegmentDivider.tsx, ResetButton.tsx
    country-segment/  CountrySegment.tsx, CountryFlag.tsx
    select-segment/   SelectSegment.tsx
```

## Out of scope

Auto-opening the next select after a choice; a multi-country data source; the locale label that the
old header showed (the locale switcher already covers it).

## Verification

```bash
cd apps/web && npm test -- src/features/locations && cd ../.. && ./ci.sh
```
