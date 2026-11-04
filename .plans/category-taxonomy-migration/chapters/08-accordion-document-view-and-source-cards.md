---
name: "Chapter 8 — Accordion document view and source cards"
overview: "Present every document-detail section as an accessible accordion item and render sources as visually subordinate cards, with the requested initial expansion state."
id: C8
depends_on:
  - C7
touches:
  - apps/web/src/features/candidates/components/CandidateDetailView/
  - apps/web/src/features/candidates/components/FlowDiagram/
  - apps/web/src/features/candidates/components/
  - apps/web/src/features/candidates/utils/
  - apps/web/src/components/data-display/
  - apps/web/src/i18n/fallback/
  - apps/web/src/test/
execution: chapter-implementer
todos:
  - id: accordion-shell
    content: "Compose five accessible accordion items with the first three open and evidence/sources closed by default."
    status: pending
  - id: section-content
    content: "Move ingress, egress, flow, evidence, and sources content under the accordion without losing empty states or responsive behavior."
    status: pending
  - id: source-cards
    content: "Render one visually subordinate source card per source with clear external links and source metadata."
    status: pending
  - id: tests
    content: "Add default-state, keyboard, empty-state, responsive, source-card, and no-completeness regression tests."
    status: pending
---

# Chapter 8 — Accordion document view and source cards

**Repo:** `redtape` (`apps/web`)
**Depends on:** [Chapter 7](07-public-document-metadata-cleanup.md) · **Architecture:** [../00-architecture.md](../00-architecture.md) · **Decisions:** [../gaps-and-decisions.md](../gaps-and-decisions.md) · **Rollout:** [../01-rollout.md](../01-rollout.md)

## Goal

Make every document-detail section an accordion item:

1. documents you need first;
2. documents that need this one;
3. flow;
4. evidence;
5. sources.

The first three are expanded on initial render. Evidence and sources are collapsed. All five remain discoverable and keyboard accessible, including on narrow viewports.

Sources are currently a visually undifferentiated list. Render one source card per `CandidateSource`, using the document-card visual language where possible and a quieter second-level card when source fields do not represent a document.

## Design decisions

- `CandidateDetailContent` owns one accordion root and composes the five item bodies; section components own only their content.
- Use stable item values (`ingress`, `egress`, `flow`, `evidence`, `sources`) and a default value containing the first three.
- User toggles are local state unless a later requirement makes evidence/source deep links necessary. Do not put expansion state into category URLs.
- The Flow item remains present below the `md` breakpoint. The diagram may use a responsive composition or an accessible empty/fallback view, but the section must not disappear because of a display breakpoint.
- Evidence contains screenshot content and its own evidence empty state. Sources are a child of the sources item, not a second accordion nested inside evidence.
- Each source card has one clear source title/link, source role, excerpt, optional condition, and optional link metadata. External links retain `target`, `rel`, and accessible names.
- Prefer an existing `AppCard`/document-card shell. If `CandidateSource` lacks document fields, create a small `SourceCard` variant with lower visual weight instead of forcing a misleading document card.
- The completeness section is not replaced by an accordion item. The progress circle remains wherever chapter 7 preserves it.

## Files

| Path | Change |
| --- | --- |
| `apps/web/src/features/candidates/components/CandidateDetailView/CandidateDetailContent.tsx` | Own the five-item accordion and requested default values. |
| `apps/web/src/features/candidates/components/CandidateDetailView/NeighbourSection.tsx` | Convert the ingress/egress heading/list body into accordion-compatible content without duplicate section headings. |
| `apps/web/src/features/candidates/components/FlowDiagram/FlowSection.tsx` | Provide the flow item body and remove the breakpoint that hides the whole section. |
| `apps/web/src/features/candidates/components/FlowDiagram/FlowDiagram.tsx` | Preserve diagram layout and add responsive/accessible fallback as needed. |
| `apps/web/src/features/candidates/components/CandidateDetailView/CandidateEvidence.tsx` | Split screenshot/evidence body from the sources item; do not own a nested sources accordion. |
| `apps/web/src/features/candidates/components/CandidateDetailView/CandidateSources.tsx` | Render one source card per source. |
| `apps/web/src/features/candidates/components/CandidateDetailView/SourceCard.tsx` | Add a second-level source-card presentation if the shared document card cannot represent source data safely. |
| `apps/web/src/features/candidates/components/CandidateDetailView/NeighbourCard.tsx` | Reuse existing card grammar without introducing nested links. |
| `apps/web/src/features/candidates/components/CandidateDetailView/CandidateDetailSkeleton.tsx` | Match the new accordion structure during loading. |
| `apps/web/src/i18n/fallback/{de,en}.json` | Add/adjust accordion labels, source-card labels, and empty states. |
| `apps/web/src/features/candidates/components/CandidateDetailView/CandidateDetailContent.test.tsx` | Test all five items and default expansion. |
| `apps/web/src/features/candidates/components/CandidateDetailView/NeighbourSection.test.tsx` | Preserve ingress/egress content and empty states. |
| `apps/web/src/features/candidates/components/CandidateDetailView/CandidateEvidence.test.tsx` | Test evidence content and collapsed default. |
| `apps/web/src/features/candidates/components/CandidateDetailView/CandidateSources.test.tsx` | Test one card per source, links, role, excerpt, and empty state. |
| `apps/web/src/features/candidates/components/FlowDiagram/FlowSection.test.tsx` | Test flow item visibility, diagram, empty state, and responsive fallback. |
| `apps/web/src/features/candidates/containers/CandidateDetailPage.test.tsx` | Test integrated headings, default expansion, and no completeness section. |

## Red tests

### Happy path

- `detail view · renders five accordion items` asserts all requested labels and stable item values.
- `detail view · opens ingress, egress, and flow by default` asserts `aria-expanded=true` for the first three.
- `detail view · keeps evidence and sources collapsed by default` asserts `aria-expanded=false` for the last two while their triggers remain available.
- `sources · renders one subordinate card per source` asserts source title/link, role, excerpt, and optional condition.
- `flow · remains an accordion item on narrow viewports` asserts the section is not removed by CSS breakpoint logic.

### Negative path

- `detail view · does not render a completeness item or checklist` asserts chapter 7's removal remains intact.
- `accordion · collapsed bodies are not exposed as expanded content` asserts the component uses the accessible Chakra accordion contract.
- `sources · missing portal URL remains readable without an invalid link` asserts procedure title still renders as text.
- `sources · empty source list shows an explicit empty state` asserts no blank card/list is produced.
- `flow · no dependencies shows the localized empty state` asserts no invalid SVG or misleading diagram.

## Green

1. Add integrated accordion tests before changing composition.
2. Move existing ingress, egress, flow, evidence, and source bodies beneath stable accordion items.
3. Set default expansion and preserve keyboard trigger/content semantics.
4. Extract/reuse the card shell and render source cards with lower visual weight.
5. Update skeleton, responsive behavior, translations, and integrated tests.

## Refactor gate

Audit the entire detail composition:

- the parent owns accordion state and children own content only;
- no section owns a duplicate heading or nested accordion;
- the five item values are centralized and not copied as strings;
- source mapping and source-card rendering are separate units;
- card links and source links are not nested;
- flow layout is separate from accordion orchestration;
- no breakpoint removes a requested section;
- empty/error/loading states have one owner each;
- component props remain small and types describe actual source/neighbor data.

Report the refactor outcome and rerun the narrow suite after each extraction.

## Verification

```bash
cd apps/web
npm test -- src/features/candidates/components/CandidateDetailView \
  src/features/candidates/components/FlowDiagram \
  src/features/candidates/containers/CandidateDetailPage.test.tsx
npm run lint && npm run format:check && npm run typecheck && npm run build
cd ../..
./ci.sh
```

Record accordion default-state, keyboard, responsive, and source-card evidence in [../run-ledger.md](../run-ledger.md).

## Out of scope

Taxonomy migration, category chip semantics, public staging/completeness field removal, new source ingestion, embeddings, entity identification, and redesign of the flow graph geometry.

## Git workflow

```bash
git checkout feat/plans-category-taxonomy-migration && git pull
git checkout -b feat/accordion-document-view
```

```text
test(web): describe accordion document sections and source cards
feat(web): organize document detail sections as accordions
```
