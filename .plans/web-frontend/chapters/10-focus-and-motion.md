---
name: "Chapter 10 — Focus and motion"
overview: "Theme-aligned focus rings and shared hover transition props on cards and interactive controls; style.css focus-visible uses accent ring token."
todos:
  - id: focus-css
    content: "Update style.css focus-visible to focus.ring semantic"
    status: done
  - id: hover
    content: "DocumentCard and header link _hover use duration tokens"
    status: done
  - id: disabled
    content: "Ensure disabled selects/buttons skip hover lift"
    status: done
  - id: tests
    content: "DocumentCard hover/disabled tests"
    status: done
isProject: false
---

# Chapter 10 — Focus and motion

**Repo:** `redtape` (`apps/web`) · **Branch:** `feat/web-visual-focus-motion` · **Status:** done

**Depends on:** [6](06-document-card.md) · **Architecture:** [../00-architecture.md](../00-architecture.md) §5 · **Rollout:** [../01-rollout.md](../01-rollout.md)

---

## Goal

Interactive polish is consistent: focus outlines use accent-derived `focus.ring` (including global
`:focus-visible` in [style.css](../../apps/web/src/style.css)); document cards and header wordmark
use theme duration/easing tokens on `_hover`. Disabled controls do not animate hover lift.

## Design decisions

**No port of test-storage `chakra.tsx`.** Export a minimal `transitionProps` object or inline
`transition` using `durations.normal` token string from theme — single file under
`theme/transitions.ts` if reused ≥2 times.

**Card hover from chapter 6 refined here.** Chapter 6 may ship basic hover; this chapter binds
motion tokens explicitly and adds tests.

**Do not add pointless one-line wrappers** around Chakra props unless the same `_hover` block repeats
three times (rule of three).

**Implementation note:** `theme/transitions.ts` exports `hoverMotion` (duration `normal`, easing
`easeOut` tokens), used by both `DocumentCard` and the `AppLayout` wordmark (two uses, so it stays
shared); each site sets its own `transitionProperty`. The header wordmark lives in `AppLayout.tsx`
(no `AppHeader.tsx` exists). `LocationSelect.tsx` needed no change: Chakra's select trigger has no hover
lift, and the disabled test pins that. The `focus.ring` semantic already existed; the theme test
pins it. Reduced-motion media query was skipped (out of scope) and remains an optional follow-up.

## Files

**Add**

| Path | Contents |
| --- | --- |
| `apps/web/src/theme/transitions.ts` | Optional shared hover/focus transition strings |
| `DocumentCard.test.tsx` additions | Disabled/hover tests (extend existing file) |

**Edit**

| Path | Change |
| --- | --- |
| `apps/web/src/style.css` | `:focus-visible` uses CSS var from Chakra/emotion or explicit accent ring |
| `apps/web/src/features/documents/components/documents-list/DocumentCard.tsx` | Tokenized transition |
| `apps/web/src/components/layout/AppHeader.tsx` | Wordmark hover transition |
| `apps/web/src/features/locations/components/location-picker/LocationSelect.tsx` | Disabled: no erroneous hover styles |

## Red tests

| Test | Asserts |
| --- | --- |
| `DocumentCard · card root includes motion transition prop` | Transition references theme duration (e.g. `200ms` / `durations.normal`) |
| `LocationSelect · disabled select does not enable hover lift` | `disabled` true on trigger; no transform in `_hover` when disabled |
| `theme · focus.ring semantic is defined` | Token resolves non-empty |

## Green

1. Add/update `transitions.ts`.
2. Wire `_hover` on card and wordmark.
3. Update global focus CSS.
4. Extend tests.

## Refactor gate

If `transitions.ts` is one constant used once, inline instead — avoid pointless wrapper per
code-structure.mdc.

Report outcome.

## Verification

```bash
cd apps/web
npm run test -- src/features/documents/components/documents-list/DocumentCard.test.tsx src/features/locations/components/location-picker/LocationSelect.test.tsx src/theme/theme.test.ts
cd ../.. && ./ci.sh
```

Manual: Tab through list cards and header controls; focus ring visible in light and dark.

## Out of scope

Page transition animations. Reduced-motion media query (optional follow-up; note in gaps if skipped).

## Git workflow

```bash
git checkout -b feat/web-visual-focus-motion
```

```text
feat(web): align focus ring and hover motion with theme tokens
```
