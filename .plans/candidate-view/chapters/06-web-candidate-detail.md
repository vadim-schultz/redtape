---
name: "Chapter 6 — Web candidate detail"
overview: "Add the public /candidates/:id page: title, description with attribution, tags and completeness checklist, Ingress and Egress neighbour-card lists, an evidence section with the screenshot and sources, and explicit skeleton, error and not-found states."
todos:
  - id: slice
    content: "Add detail types, the service, the detail hook and the queryKeys entry."
    status: pending
  - id: view
    content: "Build CandidateDetailView sections: header, checklist, Ingress and Egress lists, evidence."
    status: pending
  - id: states-route
    content: "Add skeleton, error and not-found handling, the route and the strings."
    status: pending
isProject: false
---

# Chapter 6 — Web candidate detail

**Repo:** `redtape` (`apps/web`) · **Branch:** `feat/candidate-view-web-detail` · **Status:** planned  
**Depends on:** [05-web-candidate-list.md](05-web-candidate-list.md) · **Architecture:** [../00-architecture.md](../00-architecture.md) (sections 2, 4, 5, 6) · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/plans-candidate-view` · **Release branch:** `main`

## Goal

`/candidates/:id` shows one candidate the way the front page shows a document, plus its place in the
dependency graph. Top to bottom: the title; the description with "from the source page: {procedure}";
domain and situation tags; the five-item completeness checklist; section **Ingress** ("needed first", the
documents it requires) as a list of neighbour cards; section **Egress** ("needed by", the documents that
require it) as a list of neighbour cards; a **Flow** section slot that chapter 7 fills; section **Evidence**
with the screenshot and the sources. Every neighbour card links to that candidate's own page (D9). The
"staged, unreviewed" banner appears on the page (D16). Nothing is editable.

## Design decisions

- **Types mirror chapter 3.** `CandidateDetail`: `id`, `key`, `title`, `description`, `description_source`,
  `status`, `domains[]`, `situations[]`, `completeness`, `complete` and the nested `flags` object, `ingress[]`,
  `egress[]`, `sources[]`, `screenshot` (`{url, fetched_at}` or `null`). `CandidateNeighbour`: `id`, `title`,
  `description`, `condition`, `is_optional`, `excerpt`, `basis`. `CandidateSource`: `procedure_title`,
  `portal_url`, `role`, `excerpt`. The wire names are used as they are.
- **Ingress and egress are the API's lists.** The page does not recompute direction (D2). Section subtitles
  are `candidates.ingress_subtitle` ("Documents you need first") and `candidates.egress_subtitle`
  ("Documents that need this one"); section headings keep the graph terms `Ingress` and `Egress` next to the
  plain text. An empty list shows `candidates.ingress_empty` or `egress_empty` ("No documents staged"), not
  an empty box.
- **Neighbour card** is a compact fixed-height variant of `AppCard` (`height` from one named constant,
  `NEIGHBOUR_CARD_HEIGHT`, exported for chapter 7). It shows the title (clamped to one line, full title in the
  `title` attribute is not used: the title also appears in the link's accessible name), one clamped
  description line, and, when present, the edge `condition` and an "optional" badge. The `excerpt` (the
  evidence quote) is shown on the card's second line only when there is no description. The whole card links
  to `/candidates/${id}`.
- **Header** reuses `Heading`/`textStyle` from the documents detail header. Tags are static badges (no links;
  filtered candidate lists are a later seam). The description block is a quote-styled paragraph followed by
  the attribution line; with no description the block is omitted, not shown empty.
- **Checklist** is `CompletenessChips` from chapter 5 in a vertical variant (`orientation` prop), with the
  count "n of 5" in text.
- **Evidence section.** The screenshot is a plain `<img src="/api/v1/candidates/{id}/screenshot">` through
  the API base used by `apiRequest` (a helper `candidateScreenshotUrl(id)` in the service), with `alt` text
  `candidates.screenshot_alt` including the title, `loading="lazy"`, a fixed aspect-ratio box so the layout
  does not jump, and an `onError` fallback to the text `candidates.screenshot_missing`. When the detail says
  `screenshot` is `null` no request is made and the same text shows. `fetched_at` is shown with
  `formatRelativeTime`. Sources are a list: procedure title as an external link to `portal_url` (when
  present), role chip, excerpt. The route sets a long browser cache by the API's headers; the client adds
  nothing.
- **Flow slot.** The page renders `<FlowSection />` between the cards and the evidence. This chapter ships it
  as a heading plus a short "diagram follows" placeholder-free implementation: the section is simply omitted
  until chapter 7 adds the component. Do not ship placeholder text to users; chapter 7 adds the section.
- **States.** Skeleton while loading (`CandidateDetailSkeleton`, exported for the route fallback as
  `DocumentDetailSkeleton` is); a 404 from the API renders the shared `NotFoundView`; other errors render
  `QueryError` with retry. The back button returns to `/candidates` and keeps the list's URL state by using
  history back when the previous entry is the list, else the plain link.
- **Route** `/candidates/:id` is added to `src/app/routes.tsx` next to `/candidates`, `lazy` with its own
  Suspense and the skeleton, no guard. Query key `candidates.detail(id, locale)`.
- **i18n.** Add `candidates.ingress`, `ingress_subtitle`, `ingress_empty`, `egress`, `egress_subtitle`,
  `egress_empty`, `optional`, `condition_label`, `evidence`, `screenshot_alt`, `screenshot_missing`,
  `screenshot_fetched`, `sources`, `source_role_required`, `source_role_form`, `source_role_issued`,
  `checklist_title`, `checklist_count`, `back_to_list`, `not_found_title` to `en.json` and `de.json`.

## Files

**Create**

- `apps/web/src/features/candidates/types/detail.ts` (re-exported from `types/index.ts`)
- `apps/web/src/features/candidates/services/candidatesApi.ts` gains `fetchCandidate(id)` and
  `candidateScreenshotUrl(id)` (edit)
- `apps/web/src/features/candidates/hooks/useCandidateDetailQuery.ts`
- `apps/web/src/features/candidates/components/CandidateDetailView/` (`CandidateDetailView.tsx`,
  `CandidateHeader.tsx`, `CandidateChecklist.tsx`, `NeighbourSection.tsx`, `NeighbourCard.tsx`,
  `CandidateEvidence.tsx`, `CandidateScreenshot.tsx`, `CandidateSources.tsx`,
  `CandidateDetailQueryStatus.tsx`, `CandidateDetailSkeleton.tsx`, `index.ts`)
- `apps/web/src/features/candidates/containers/CandidateDetailPage.tsx`
- a test file beside each of the above

**Edit**

- `apps/web/src/features/candidates/components/CompletenessChips/CompletenessChips.tsx` (vertical variant)
- `apps/web/src/app/queryKeys.ts`, `apps/web/src/app/routes.tsx`
- `apps/web/src/i18n/fallback/en.json`, `de.json`
- `apps/web/src/app/routes.*.test.tsx` or `App.test.tsx`

**Do not edit**

- `features/documents` and its detail view
- the diagram (chapter 7) and the admin features
- backend files

## Red tests

| Test | Asserts |
| --- | --- |
| `candidate detail renders header, description and attribution` | Happy: title heading, description text and "from the source page: {procedure}" appear; tags render as badges. |
| `candidate detail omits an absent description` | Negative: `description` null renders no empty block and no attribution line. |
| `candidate checklist lists five flags and the count` | Happy: a candidate with three true flags shows "3 of 5" and five items, two announced as missing. |
| `ingress section lists neighbour cards` | Happy: two ingress items render two links to `/candidates/<neighbour id>` with title, condition and an "optional" badge on the optional one. |
| `egress section lists neighbour cards` | Happy: egress items render under the Egress heading with the "needed by" subtitle; ingress items never appear there. |
| `empty ingress and egress show the empty text` | Negative: both lists empty render two section headings with "No documents staged" and no card links. |
| `neighbour card falls back to the excerpt without a description` | Negative: a neighbour with `description` null shows its edge excerpt on the second line; one with a description does not. |
| `evidence shows the screenshot with alt text` | Happy: `screenshot` set renders one `<img>` whose `src` ends with `/api/v1/candidates/<id>/screenshot`, `alt` contains the title, and `fetched_at` text. |
| `evidence falls back when the screenshot is missing or fails` | Negative: `screenshot: null` renders the missing text and no `<img>`; a present screenshot whose image errors swaps to the missing text. |
| `sources list links to the portal page` | Happy: each source renders procedure title as a link to `portal_url` with its role chip; negative: a source with no `portal_url` renders plain text. |
| `candidate detail shows the loading skeleton` | Happy: pending query shows the skeleton with a busy status, not blank. |
| `candidate detail shows not-found for a 404` | Negative: the API 404 renders the not-found view, not the generic error. |
| `candidate detail shows a retryable error` | Negative: a 503 renders the error with a retry that refetches. |
| `candidate detail keeps the banner in every state` | Happy: the unreviewed banner is present in populated, error and not-found. |
| `app routes /candidates/:id without a guard` | Happy: an anonymous visitor reaches the page; negative: `/candidates/` with no id still resolves to the list, and `/candidates/a/b` is not-found. |
| `candidates detail strings exist in en and de` | Happy: every new key resolves in both bundles. |

## Green

1. Add the detail types, `fetchCandidate`, `candidateScreenshotUrl`, the query key and the hook.
2. Build the neighbour card and `NeighbourSection` (title, subtitle, list or empty text); export
   `NEIGHBOUR_CARD_HEIGHT`.
3. Build the header, the checklist (vertical `CompletenessChips`), the evidence parts and the sources list.
4. Compose `CandidateDetailView`, the status wrapper, the skeleton and the container; register the route.
5. Add the strings to both bundles; make the route and i18n tests pass.
6. Run the narrow suite after each step.

## Refactor gate

Audit the whole `CandidateDetailView` folder and the `CompletenessChips` change. The view composes small
sections; no file passes about one hundred lines, no component takes more than about three props (group
`ingress`/`egress`/`sources` by passing the section its own typed slice rather than the whole detail).
The neighbour card and the list card of chapter 5 share the `AppCard` base and the title/description
typography: if a third card appears, extract the shared text block; with two, keep them separate and say so.
Check the import direction, that the screenshot URL helper lives in `services`, that components receive
the URL as a prop, and that `src/architecture.test.ts` passes. Report the outcome and rerun the narrow suite.

## Verification

```bash
cd apps/web
npm run test -- src/features/candidates src/app --run
npm run lint
npm run format:check
npm run typecheck
npm run build
cd ../..
./ci.sh
```

## Out of scope

- The flow diagram (chapter 7) and any diagram placeholder text
- Clickable tags, voting, emit, editing, edge review
- Screenshot zoom or a lightbox; thumbnails
- Translating staged titles (open seam)

## Git workflow

```bash
git checkout feat/plans-candidate-view && git pull
git checkout -b feat/candidate-view-web-detail
```

Suggested commits:

```text
test(web): define the candidate detail sections and states
feat(web): add the public candidate item page
feat(web): show ingress and egress neighbour cards
```

Open the chapter PR into `feat/plans-candidate-view`.
