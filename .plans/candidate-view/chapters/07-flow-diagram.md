---
name: "Chapter 7 — Flow diagram"
overview: "Add the hand-rolled SVG flow diagram to the candidate item page: a column of ingress cards, smooth converging arrows into the central card, and diverging arrows to the egress cards, positioned by a pure layoutFlow function that the cards and the paths share."
todos:
  - id: layout
    content: "Write the pure layoutFlow function with geometry constants and table-driven tests."
    status: pending
  - id: component
    content: "Build FlowDiagram: positioned compact cards plus the SVG paths and arrowhead marker."
    status: pending
  - id: integrate
    content: "Add the Flow section to the item page with the responsive fallback, text alternative and empty note."
    status: pending
isProject: false
---

# Chapter 7 — Flow diagram

**Repo:** `redtape` (`apps/web`) · **Branch:** `feat/candidate-view-flow-diagram` · **Status:** planned  
**Depends on:** [06-web-candidate-detail.md](06-web-candidate-detail.md) · **Architecture:** [../00-architecture.md](../00-architecture.md) (section 7) · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/plans-candidate-view` · **Release branch:** `main`

## Goal

Below the Ingress and Egress card lists the item page has a **Flow** section: a left column of the ingress
documents, smooth arrows leading to the central card of this candidate, and from it smooth arrows diverging
to a right column of the egress documents. It is the cheapest thing to render on the frontend: plain SVG and
plain HTML, no library (D10, D15). Every card in the diagram is still a real link to that candidate's page.

## Design decisions

- **Pure layout, no DOM measurement.** `layoutFlow(ingressCount, egressCount, geometry?)` returns
  `{width, height, nodes, paths}`. It has no React, no browser API and is the only place coordinates are
  computed. The component positions HTML cards with `nodes` and draws `paths` in an SVG of the same size.
- **Geometry constants** (one `FLOW_GEOMETRY` object, overridable in tests):

  | Constant | Value | Meaning |
  | --- | --- | --- |
  | `cardWidth` | 220 | width of every card, side and centre |
  | `cardHeight` | `NEIGHBOUR_CARD_HEIGHT` (chapter 6), 72 | height of every card including the centre card |
  | `rowGap` | 16 | vertical gap between cards in a column |
  | `columnGap` | 120 | horizontal space between a side column and the centre column |
  | `padding` | 8 | space around the whole drawing so arrowheads are not clipped |

- **Formulas.** Let `columnHeight(n) = n * cardHeight + max(n - 1, 0) * rowGap`, `inner = max(columnHeight(ingress),
  columnHeight(egress), cardHeight)`, `height = inner + 2 * padding`, `width = 3 * cardWidth + 2 * columnGap + 2 * padding`.
  A column of `n` cards starts at `top = padding + (inner - columnHeight(n)) / 2` (vertically centred in the
  taller column), card `i` has `y = top + i * (cardHeight + rowGap)`. The centre card has
  `y = padding + (inner - cardHeight) / 2`. `x` of the ingress column is `padding`, of the centre
  `padding + cardWidth + columnGap`, of the egress column `padding + 2 * (cardWidth + columnGap)`. An empty
  column has no nodes; the centre card is always present.
- **Arrows are cubic Beziers** from an edge midpoint to an edge midpoint. Ingress card `i`: start
  `(x_in + cardWidth, y_i + cardHeight / 2)`, end `(x_c, y_c + cardHeight / 2)`. Egress card `j`: start
  `(x_c + cardWidth, y_c + cardHeight / 2)`, end `(x_out, y_j + cardHeight / 2)`. Path data
  `M x1 y1 C xm y1, xm y2, x2 y2` with `xm = (x1 + x2) / 2`, numbers rounded to one decimal so snapshot
  strings are stable. Ingress paths converge on one point of the centre card's left edge and egress paths
  diverge from one point of its right edge; the arrowhead is an SVG `<marker>` (`orient="auto"`) on the path
  end. Because ends are pulled `markerWidth` short, the geometry has `arrowInset` (6) subtracted from `x2`.
- **Return shape.** `nodes: {role: "ingress" | "centre" | "egress", index, x, y}[]` in DOM order (ingress,
  centre, egress), `paths: {from: "ingress" | "centre", index, d}[]`. `index` points into the candidate's
  `ingress[]` or `egress[]`. The component maps them without recomputing anything.
- **Component.** `FlowDiagram` takes `{candidate}` (a typed slice `{title, ingress, egress}`; three props at
  most): an outer `Box` with `position="relative"`, `width`/`height` from the layout and `maxWidth="100%"`
  with horizontal overflow on a scroll region, an absolutely positioned `<svg>` for the paths behind, and
  the cards absolutely positioned by `nodes`. Cards are the compact `NeighbourCard` of chapter 6 (link
  semantics unchanged), the centre card is a static `AppCard` with the brand accent border and the title.
  Colours come from semantic tokens only (`border.emphasized` for paths, `fg.muted` for arrowheads, the
  brand accent for the centre card), so light and dark work with no branches.
- **Responsive.** The diagram wrapper is `display={{ base: "none", md: "block" }}`. Below `md` the Ingress and
  Egress lists above it carry the information; the Flow heading is hidden with it so no empty heading is
  left behind.
- **Accessibility.** The SVG is `aria-hidden` and decorative; the wrapper has `role="group"` with
  `aria-label` from `candidates.flow_summary` ("{n} documents needed first, {m} documents that need this
  one"); the cards stay real links in DOM order ingress, centre, egress. No information exists only in the
  arrows. Arrow animation, if any, respects `prefers-reduced-motion`; none is required.
- **Empty and one-sided cases.** With no ingress and no egress the section shows
  `candidates.flow_empty` ("No dependencies staged for this document") instead of a lone centre card. With only
  one side, the other column is empty and the centre card stays centred vertically; the layout still reserves
  the empty column's width so the centre does not jump between candidates.
- **Large neighbourhoods.** The diagram caps drawn nodes per side at `MAX_FLOW_NODES = 12` and adds a final
  "+{n} more, see the list above" text node (not a card) in the column; `layoutFlow` takes the already
  capped counts and a `hidden` count it returns for the caller. The lists above remain complete.

## Files

**Create**

- `apps/web/src/features/candidates/utils/layoutFlow.ts` (pure function, types, `FLOW_GEOMETRY`)
- `apps/web/src/features/candidates/utils/layoutFlow.test.ts`
- `apps/web/src/features/candidates/components/FlowDiagram/` (`FlowDiagram.tsx`, `FlowPaths.tsx`,
  `FlowCards.tsx`, `FlowSection.tsx`, `index.ts`) with a test beside each

**Edit**

- `apps/web/src/features/candidates/components/CandidateDetailView/CandidateDetailView.tsx` (render
  `FlowSection` between the Egress section and the Evidence section)
- `apps/web/src/features/candidates/components/CandidateDetailView/NeighbourCard.tsx` only if the constant or
  the position style needs an export
- `apps/web/src/i18n/fallback/en.json`, `de.json` (`candidates.flow`, `flow_summary`, `flow_empty`,
  `flow_more`)

**Do not edit**

- the API, the list page, the admin features
- `package.json` (no dependency)

## Red tests

Pure function first, table-driven:

| Test | Asserts |
| --- | --- |
| `layoutFlow places one column of three ingress cards` | Happy: 3 ingress, 1 egress: ingress `y` values are `top + i * (cardHeight + rowGap)`, evenly spaced, the centre card's vertical midpoint equals the ingress column's midpoint. |
| `layoutFlow centres the shorter column against the taller one` | Happy: for (2, 5) and (5, 2) the shorter column's midpoint equals the taller column's midpoint; the drawing height is the taller column plus twice the padding. |
| `layoutFlow with no ingress and no egress returns only the centre card` | Negative: 0 and 0 give one `centre` node, no paths, and the minimum height of `cardHeight + 2 * padding`. |
| `layoutFlow with one side empty keeps the width` | Negative: (0, 3) and (3, 0) have the same `width` and `x` columns as (3, 3), so the centre does not move. |
| `layoutFlow produces one path per edge with the right endpoints` | Happy: (n, m) gives `n + m` paths; each ingress path starts at an ingress card's right-edge midpoint and ends at the centre card's left-edge midpoint minus `arrowInset`; each egress path starts at the centre card's right-edge midpoint and ends at an egress card's left-edge midpoint minus `arrowInset`. |
| `layoutFlow path data is a smooth cubic` | Happy: every `d` matches `^M [\d.]+ [\d.]+ C [\d.]+ [\d.]+, [\d.]+ [\d.]+, [\d.]+ [\d.]+$`, the two control points share the x midpoint and the y of their own end, and a straight horizontal edge (equal y) is still a valid cubic. |
| `layoutFlow is deterministic and rounds to one decimal` | Happy: two calls are deep-equal; no number in any `d` has more than one decimal place. |
| `layoutFlow rejects negative or non-integer counts` | Negative: counts of -1 or 1.5 throw a `RangeError` before any computation. |
| `layoutFlow caps the drawn nodes and reports the hidden count` | Negative: 20 ingress and `MAX_FLOW_NODES = 12` draws 12 ingress nodes and reports 8 hidden; paths equal drawn nodes. |

Component tests, using `renderWithProviders` and jsdom (no layout engine, so assertions use the computed
styles and attributes, not measured boxes):

| Test | Asserts |
| --- | --- |
| `flow diagram renders a link and a path per neighbour` | Happy: 2 ingress and 3 egress produce five neighbour links to `/candidates/<id>`, one centre card, and five `<path>` elements with `marker-end`. |
| `flow diagram positions cards from the layout` | Happy: each card's inline `left` and `top` equal its `layoutFlow` node, the SVG `width` and `height` equal the layout size. |
| `flow diagram announces a text alternative` | Happy: the wrapper is a `group` named with the localized counts; the SVG is `aria-hidden`. |
| `flow diagram shows the empty note without dependencies` | Negative: no ingress and no egress renders the empty text and no SVG. |
| `flow diagram is hidden below the md breakpoint` | Negative: the wrapper carries the responsive `display` of `none` on `base` and `block` on `md` (assert the Chakra style), and the Flow heading shares it. |
| `flow diagram shows the overflow note beyond the cap` | Negative: 20 egress items render 12 cards and the text "+8 more", not 20 cards. |
| `item page shows the flow between the lists and the evidence` | Happy: section order is Ingress, Egress, Flow, Evidence. |
| `flow strings exist in en and de` | Happy: the new keys resolve in both bundles. |

Write and run the pure-function tests first; they define the whole geometry before any React exists.

## Green

1. Implement `layoutFlow` (counts validation, column math, node list, path list, cap and hidden count);
   make the pure tests pass.
2. Build `FlowPaths` (the SVG with the marker definition and the path elements) and `FlowCards` (positioned
   neighbour cards and the centre card) from the layout output; build `FlowDiagram` and `FlowSection`
   (heading, empty note, responsive wrapper, text alternative).
3. Insert the section into the detail view; add the strings to both bundles.
4. Run the narrow suite after each step.

## Refactor gate

Audit `layoutFlow` and the `FlowDiagram` folder. Split `layoutFlow` into named helpers (`columnHeight`,
`columnTop`, `nodeY`, `curve`) so no function passes about five lines and the file stays near one hundred
lines; keep geometry in one constant. Verify the component holds no coordinates of its own (every number
comes from the layout), that no function does DOM measurement, and that cards and paths cannot disagree
because both read the same `nodes`. Count the arms of the ingress and egress mapping for the rule of three:
two sides share one `FlowCards` mapping parameterised by role. Report the outcome and rerun the narrow suite.

## Verification

```bash
cd apps/web
npm run test -- src/features/candidates --run
npm run lint
npm run format:check
npm run typecheck
npm run build
cd ../..
./ci.sh
```

Manual look for the release smoke (chapter 10): the diagram in light and dark, with 0, 1 and many neighbours,
and hidden below the `md` width.

## Out of scope

- A graph library, force layouts, drag, zoom, pan or animation
- Multi-hop graphs (only direct ingress and egress)
- Showing edge conditions on the arrows (they are on the cards)
- Server-side rendering or an exported image of the diagram

## Git workflow

```bash
git checkout feat/plans-candidate-view && git pull
git checkout -b feat/candidate-view-flow-diagram
```

Suggested commits:

```text
test(web): define the flow layout geometry
feat(web): add the pure flow layout for candidate dependencies
feat(web): render the candidate flow diagram
```

Open the chapter PR into `feat/plans-candidate-view`.
