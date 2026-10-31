---
name: "Chapter 4 — Sources accordion"
overview: "Wrap the sources list (the procedure pages that back a candidate) in a Chakra v3 Accordion, collapsed by default and titled with the existing, unused 'Sources' i18n key, so the document-focused page doesn't expose bureaucratic-process framing by default."
todos:
  - id: accordion
    content: "Wrap CandidateSources in a collapsed-by-default Accordion titled candidates.sources"
    status: pending
isProject: false
---

# Chapter 4 — Sources accordion

**Repo:** `redtape` (`apps/web`) · **Branch:** `feat/candidate-view-polish-sources-accordion` · **Status:** planned
**Depends on:** none · **Architecture:** [../00-architecture.md](../00-architecture.md) (section 6) · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/plans-candidate-view-polish` · **Release branch:** `main`

## Goal

`CandidateEvidence.tsx` renders `CandidateSources` directly beneath the screenshot, always visible, with no heading of its own — the procedure links at the bottom of the page are presumably the bureaucratic processes a document belongs to, and the site is meant to be document-focused, not process-focused. Defer that framing behind a collapsed, clearly-labelled disclosure, without touching the sources data itself.

## Design decisions

- **Component.** Introduce Chakra v3's `Accordion` (`Accordion.Root`, `Accordion.Item`, `Accordion.ItemTrigger`, `Accordion.ItemIndicator`, `Accordion.ItemContent`) — the first use of `Accordion` anywhere in `apps/web/src` (confirmed empty repo search). Follow the same composition style `SectionCard.tsx` uses for `Card.Root` (compose Chakra's parts directly, no new generic wrapper component unless a second accordion use appears later — rule of three).
- **Placement.** In `CandidateEvidence.tsx`, wrap the existing `<CandidateSources sources={sources} />` call in the accordion; the screenshot stays outside it, always visible. The accordion's single item trigger shows the existing `candidates.sources` text ("Sources"/"Quellen" — already defined, currently unused).
- **Default state.** Collapsed by default on every page load (`defaultValue={[]}` or equivalent, not derived from any stored preference — decision D6 in [gaps-and-decisions.md](../gaps-and-decisions.md)).
- **Accessibility.** Chakra's `Accordion` parts already provide the correct ARIA wiring (`aria-expanded`, `aria-controls`, keyboard toggling) — rely on them rather than hand-rolling disclosure semantics. Confirm the trigger is reachable by keyboard and that `CandidateSources`'s own list markup (`<ul>`/`<li>`) is preserved inside `Accordion.ItemContent`.
- **No change to `CandidateSources.tsx` itself** — its list markup, links, role badges and excerpts are unchanged; only what wraps it changes.

## Files

**Edit**

- `apps/web/src/features/candidates/components/CandidateDetailView/CandidateEvidence.tsx`
- its test file

**Do not edit**

- `CandidateSources.tsx`, `CandidateScreenshot.tsx`
- `candidates.sources`, `candidates.evidence`, or any `source_role_*` i18n key (reused as-is)

## Red tests

| Test | Asserts |
| --- | --- |
| `the sources accordion is collapsed by default` | Happy: on initial render, the sources list content is not in the accessibility tree / not visible, and the trigger's expanded state is false. |
| `the accordion trigger is titled Sources` | Happy: the trigger's accessible name is `candidates.sources` ("Sources" in en). |
| `expanding the accordion reveals the sources list` | Happy: a user click (or Enter/Space via keyboard) on the trigger reveals the existing `CandidateSources` content (links, role badges, excerpts) unchanged. |
| `the screenshot stays outside the accordion and always visible` | Negative: the screenshot renders regardless of the accordion's expanded state. |
| `collapsing after expanding hides the sources again` | Negative: toggling the trigger a second time re-collapses the content. |

## Green

1. Import Chakra's `Accordion` parts in `CandidateEvidence.tsx`.
2. Wrap the existing `<CandidateSources />` render in `Accordion.Root`/`Item`/`ItemTrigger`/`ItemContent`, titled with `t("candidates.sources")`, collapsed by default.
3. Confirm the screenshot section is unaffected (still a sibling, not inside the accordion).

## Refactor gate

Audit `CandidateEvidence.tsx`: confirm the accordion composition reads cleanly inline (it's one item, so no extraction is needed yet — note explicitly if a second use case later would justify a shared `Disclosure` wrapper, per the rule of three). Check keyboard operability was actually exercised by the tests (via `userEvent`, not a raw click only). Report the outcome.

## Verification

```bash
cd apps/web
npm run test -- src/features/candidates/components/CandidateDetailView/CandidateEvidence --run
npm run lint
npm run format:check
npm run typecheck
npm run build
cd ../..
./ci.sh
```

## Commits

`test(web): collapse the sources list behind an accordion`, `feat(web): defer the sources list behind a collapsed Sources accordion`.

## Out of scope

Any change to what sources data is captured, computed, or how `CandidateSources` renders a source; a persisted open/closed preference; a domains/life-situations browsing view that might later reuse this data differently (future work, noted in [gaps-and-decisions.md](../gaps-and-decisions.md)).

## Git workflow

```bash
git checkout feat/plans-candidate-view-polish && git pull
git checkout -b feat/candidate-view-polish-sources-accordion
```

Open the chapter PR into `feat/plans-candidate-view-polish`.
