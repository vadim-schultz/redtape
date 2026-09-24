---
name: "Chapter 8 — Location picker"
overview: "Location picker framed in Card.Root; select labels use Field compound; query behavior unchanged."
todos:
  - id: card-frame
    content: "Wrap LocationPicker content in Card.Root"
    status: pending
  - id: field-labels
    content: "LocationSelect uses Field.Root and Field.Label"
    status: pending
  - id: tests
    content: "LocationPicker and LocationSelect tests"
    status: pending
isProject: false
---

# Chapter 8 — Location picker

**Repo:** `redtape` (`apps/web`) · **Branch:** `feat/web-visual-location-picker` · **Status:** planned

**Depends on:** [2](02-theme-system.md) · **Architecture:** [../00-architecture.md](../00-architecture.md) §2 · **Rollout:** [../01-rollout.md](../01-rollout.md)

---

## Goal

The jurisdiction filter reads as a card on the canvas: `Card.Root` + `Card.Header`/`Card.Body` as
appropriate, `surface.base`, border tokens. Each cascade select keeps `Select.Root` namespace; labels
use `Field.Root` / `Field.Label` instead of bare `Text`. State/district/municipality query wiring
unchanged.

## Design decisions

**Do not extract LocationSelectRow unless refactor gate requires.** Three select blocks pre-exist;
audit counts four decision paths (three selects + reset header). Extract shared row component only if
containing `LocationPicker` exceeds structure rules after styling edits.

**Hardcoded English labels** (`State`, `District`, `City`) remain until i18n — styling only.

## Files

**Edit**

| Path | Change |
| --- | --- |
| `apps/web/src/features/locations/components/location-picker/LocationPicker.tsx` | Card wrapper; remove redundant Box border if Card supplies it |
| `apps/web/src/features/locations/components/location-picker/LocationSelect.tsx` | Field.Label; input border tokens |
| `apps/web/src/features/locations/components/location-picker/LocationPickerHeader.tsx` | Optional token tweaks |

**Add**

| Path | Contents |
| --- | --- |
| `LocationPicker.test.tsx` | Disabled cascade tests |
| `LocationSelect.test.tsx` | Field + select render |

## Red tests

| Test | Asserts |
| --- | --- |
| `LocationPicker · renders three labeled selects on a card surface` | Three combobox/select triggers; card root present |
| `LocationSelect · district disabled without state` | `disabled` true when parent state empty |
| `LocationSelect · city disabled without district` | `disabled` true when district empty |
| `LocationPicker · reset clears selection when canReset` | Reset button calls handler (mock `onMunicipalityChange`) |

## Green

Wrap picker; migrate labels to Field; apply semantic surface/input colors.

## Refactor gate

Count arms in `LocationPicker`: reset handler, three onChange handlers, three select blocks. If total
logical paths for “render select row” >2, extract `LocationSelectField` parameterized by label,
value, options, disabled, onChange — re-run tests after extraction.

## Verification

```bash
cd apps/web
npm run test -- src/features/locations/components/location-picker/
cd ../.. && ./ci.sh
```

## Out of scope

Deleting duplicate `features/locations/components/LocationPicker.tsx` (STATUS.md hygiene). i18n labels.

## Git workflow

```bash
git checkout -b feat/web-visual-location-picker
```

```text
feat(web): frame location picker in Card and Field labels
```
