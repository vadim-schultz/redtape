---
name: "Chapter 3 — Plain-language ingress/egress headings"
overview: "Promote the existing plain-language subtitle copy ('Documents you need first' / 'Documents that need this one') to the ingress/egress section headings themselves, and drop the now-redundant subtitle line, in en and de."
todos:
  - id: i18n
    content: "Swap ingress/egress heading copy for the existing subtitle copy in en.json and de.json"
    status: pending
  - id: component
    content: "Drop the now-redundant subtitle line and *_subtitle keys from NeighbourSection"
    status: pending
isProject: false
---

# Chapter 3 — Plain-language ingress/egress headings

**Repo:** `redtape` (`apps/web`) · **Branch:** `feat/candidate-view-polish-neighbour-language` · **Status:** planned
**Depends on:** none · **Architecture:** [../00-architecture.md](../00-architecture.md) (section 5) · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/plans-candidate-view-polish` · **Release branch:** `main`

## Goal

`NeighbourSection.tsx` renders heading `candidates.ingress`/`candidates.egress` ("Ingress"/"Egress") and, immediately below it, a separate subtitle (`candidates.ingress_subtitle`/`egress_subtitle`, already "Documents you need first"/"Documents that need this one" in `en.json`, and the German equivalents in `de.json`). The graph terminology is too technical for a heading; the plain-language phrasing the candidate-view suite already wrote is one line too low. Make the plain-language copy the heading, and remove the redundant line.

## Design decisions

- **i18n.** In `en.json` and `de.json`, change `candidates.ingress` to the current `ingress_subtitle` text ("Documents you need first" / "Dokumente, die du zuerst brauchst") and `candidates.egress` to the current `egress_subtitle` text ("Documents that need this one" / "Dokumente, die dieses Dokument brauchen"). Remove `candidates.ingress_subtitle` and `candidates.egress_subtitle` (no longer referenced once the component change below lands). `candidates.ingress_empty`/`egress_empty` are untouched.
- **Component.** In `NeighbourSection.tsx`, drop the `<Text color="muted">{t(keys.subtitle)}</Text>` line and the `subtitle` field from the `KEYS` map; the heading alone now carries the plain-language text. `aria-labelledby` still points at the heading, so the section's accessible name is unaffected.
- **No change to meaning or direction.** The internal `NeighbourKind = "ingress" | "egress"` type, the prop name, and the API's `ingress`/`egress` fields are unchanged — this is a string and one line of markup, nothing structural. Candidate-view's D2 (what ingress/egress mean) stands as written.

## Files

**Edit**

- `apps/web/src/i18n/fallback/en.json` (`candidates.ingress`, `candidates.egress`; remove `candidates.ingress_subtitle`, `candidates.egress_subtitle`)
- `apps/web/src/i18n/fallback/de.json` (same keys)
- `apps/web/src/features/candidates/components/CandidateDetailView/NeighbourSection.tsx`
- its test file, and any snapshot/i18n-key-coverage test asserting the old key set (check `fallback.test.ts` and `NeighbourSection`'s own test)

**Do not edit**

- The API, the `ingress[]`/`egress[]` field names, or `CandidateNeighbour`
- `NeighbourCard.tsx`, `FlowDiagram` components (they don't render this heading)
- Any other `candidates.*` key

## Red tests

| Test | Asserts |
| --- | --- |
| `the ingress heading reads the plain-language text` | Happy: the section heading's accessible text is "Documents you need first" (en) — not "Ingress". |
| `the egress heading reads the plain-language text` | Happy: the section heading's accessible text is "Documents that need this one" (en) — not "Egress". |
| `the section renders no separate subtitle line` | Negative: only one text node (the heading) carries the plain-language copy; the old two-line heading+subtitle structure is gone. |
| `the empty-state text is unchanged` | Negative: `candidates.ingress_empty`/`egress_empty` still render exactly as before when the list is empty. |
| `both locales resolve the new heading keys and drop the removed ones` | Happy: `en.json`/`de.json` both have the new `ingress`/`egress` values; negative: `ingress_subtitle`/`egress_subtitle` are absent from both files and nothing else in the codebase references them (grep check in the test or as a manual step noted in the PR). |

## Green

1. Update `en.json` and `de.json`: new heading text, remove the two subtitle keys.
2. Remove the subtitle `Text` and the `subtitle` field from `NeighbourSection.tsx`'s `KEYS` map.
3. Update or remove any test/fixture that referenced the old "Ingress"/"Egress" heading text or the subtitle keys.

## Refactor gate

Audit `NeighbourSection.tsx`: with the subtitle line gone, confirm the component is still well under its size budget and the `KEYS` map reads cleanly with one field instead of two. Grep the repo for any remaining reference to `ingress_subtitle`/`egress_subtitle` to confirm nothing else depended on them. Report the outcome.

## Verification

```bash
cd apps/web
npm run test -- src/features/candidates/components/CandidateDetailView/NeighbourSection src/i18n --run
npm run lint
npm run format:check
npm run typecheck
npm run build
cd ../..
./ci.sh
```

## Commits

`test(web): promote the plain-language ingress/egress headings`, `feat(web): use plain-language headings for ingress and egress`.

## Out of scope

Any change to the ingress/egress data model, edge direction, or the candidate-view suite's D2; the neighbour card itself; any other `candidates.*` string.

## Git workflow

```bash
git checkout feat/plans-candidate-view-polish && git pull
git checkout -b feat/candidate-view-polish-neighbour-language
```

Open the chapter PR into `feat/plans-candidate-view-polish`.
