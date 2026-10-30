---
name: "Candidate view — Gaps and decisions"
overview: "Settled decisions for the public candidate view, the completeness model, screenshot serving and collection, the admin table repairs and the catalogue/coverage split; open seams and risks."
isProject: false
---

# Candidate view — Gaps and decisions

**Architecture:** [00-architecture.md](00-architecture.md) · **Rollout:** [01-rollout.md](01-rollout.md) · **Live runs:** [02-live-runs.md](02-live-runs.md)

## Settled

Decisions D1 to D3, D12, D18 and D19 were made by the owner on 2026-10-30; the rest follow from the request and the exploration. Do not re-open them during implementation.

| # | Decision |
| --- | --- |
| D1 | **Show every candidate, rank by completeness.** The public list is not limited to complete candidates. Each carries five flags (`has_domain`, `has_situation`, `has_edges`, `has_snapshot`, `has_screenshot`) and their count; default order is completeness descending. `filter[complete]=yes` narrows to all-five. Reason: production has no situation code yet, so a strict list would be empty. |
| D2 | **Ingress = what a document requires; egress = what requires it.** Edges are stored `parent requires required`. For a candidate, ingress are the edges where it is the parent (arrows run into it), egress the edges where it is the required end. UI subtitles say "needed first" and "needed by" so nobody has to know the graph terms. |
| D3 | **Screenshots are served by a public proxy route** (`GET /api/v1/candidates/{id}/screenshot`) with immutable `Cache-Control`, `ETag` = sha256 and `If-None-Match`; 404 without one; 503 when the R2 read budget is spent. No presigned URLs on the public surface. The list never includes screenshot bytes or URLs. |
| D4 | **Description = the best mention excerpt.** Staged candidates have no description. Use the excerpt of the first mention ordered by role (`required`, `form`, `issued`), then `created_at`, then `id`; at most 300 characters (quotes are already capped); the card shows "from the source page: {procedure title}". Never invent or translate text. |
| D5 | **Routes are plural and top level:** `/candidates` and `/candidates/:id` (API `/api/v1/candidates...`), like `/documents`. No guard, no login, staged and emitted candidates both listed. |
| D6 | **Completeness lives in one SQL read model, parity-tested.** Tag consensus (and the manual override of D18) is re-expressed in SQL with the settings thresholds and a test pins it to the Python rule. No new column, no migration, no materialised view. Revisit only if the list is slow (open seam). |
| D7 | **Snapshot and screenshot flags are true when any procedure that mentions the candidate has one.** The screenshot shown is the newest among those procedures. |
| D8 | **"Ready" in the UI means the five flags.** The emit preview and its skip reasons remain the authority for emission. The admin gets a Readiness column and a "Ready" quick filter built on the same read model. |
| D9 | **Neighbour cards always link.** Every candidate is visible, so an ingress or egress card always opens `/candidates/:id` of the neighbour. |
| D10 | **The diagram is hand-rolled SVG with fixed-height compact cards.** No graph library. Positions come from the pure `layoutFlow` function so nothing is measured in the DOM. Below `md` the diagram is hidden and the two card lists remain. |
| D11 | **Admin table = shared DataTable contract.** Search and clear live in the table header; every column declares `canSort` and `filter` where the API allowlists them; titles are bounded by a `maxWidth` column option and a Chakra `Tooltip`; the tasks target column gets the same cell. The legacy admin query parameters stay accepted. |
| D12 | **Screenshot collection runs first, as a chief-of-staff live run** after chapter 1 (the requeue tool). The owner's request of 2026-10-30 is the go for this bounded spend: Cloudflare browser seconds up to the 570 a day cap, R2 writes of about 60 to 300 KB a page, staged data only. A different scope (more than one day's cap, a different kind) needs a new go. |
| D13 | **Catalogue and coverage are made distinct, not unified.** Coverage keeps the 8-card summary and the budgets. Catalogue drops `CoverageSummary` and shows its own already-typed summary chips as clickable filters, plus a Title column. Both layouts stay as they are. |
| D14 | **A machine read route is added for the requeue tool** because no route links catalogue rows to candidate mentions. It is read-only and uses the machine key like its neighbours. The live run therefore waits for the API deploy (blocker, see [02-live-runs.md](02-live-runs.md)). |
| D15 | **No new dependency** in `apps/web` or `apps/api`. Tooltip is Chakra v3's own (`Tooltip` parts), the diagram is SVG. |
| D16 | **Every public page carries a "staged, unreviewed" notice.** The candidates are model output; the notice is a plain text banner from i18n keys, not a feature flag. |
| D18 | **Manual tags override the consensus.** A mention with `extractor = 'manual'` and non-empty codes is authoritative for its axis (domain, situation) and replaces, not merges with, the extracted consensus; one procedure suffices. Implemented in Python (`curated_codes`) and SQL, parity-tested (chapter 2). The extracted consensus rule and its thresholds are not changed; the emit path sees manual codes as accepted codes, and the OP15 tag review still applies before any emit. |
| D19 | **Showcase candidates are curated in production, marked `manual`.** After the completeness model is deployed and screenshots exist, the chief of staff completes five (at most eight) of the highest-ranking real candidates by hand through `candidates curate` (chapter 11) in the live run LR2: manual tags, grounded manual edges, targeted screenshot capture. Only the existing machine routes are used; nothing is deleted or edited; nothing is emitted. The owner's request of 2026-10-30 is the go for this bounded write. A different scope (more candidates, editing extracted rows, emit) needs a new go. |
| D17 | **Gates are local.** GitHub Actions minutes are exhausted until about 2026-11-01. Each chapter passes the local gate in [01-rollout.md](01-rollout.md) and merges into the loop branch on that; remote CI is run on the release PR when minutes are back. |

## Open seams

- **Curation gate.** Unreviewed output is public. A vote, a moderator hide, or a `candidates_public_enabled` switch is not built. If the false-positive rate bothers the owner after seeing the pages, add a hide list first (smallest) before any voting.
- **Sparse tags.** Domain codes cover 6 of 58 candidates and situation codes none (2026-10-30). The list will rank almost every candidate as incomplete until more procedures are drained. This suite does not change extraction; see the extraction suite's possible E21 and the daily drain.
- **Completeness performance.** The read model is computed per request. With a few thousand candidates this is fine; a persisted column or materialised view is the later fix.
- **Screenshot coverage.** One drain a day captures about 55 to 65 pages. A full backlog takes several days; the live run records the remaining count.
- **Thumbnails.** The list shows no image. A resized thumbnail needs server-side image work and is deferred.
- **Staged titles are German only.** The UI localizes chrome and tags, not candidate titles.
- **Edge quality is unjudged.** The 2026-10-30 drain judged nodes, not edges; the diagram may show wrong edges. The edge excerpt is shown on the neighbour card as the evidence.
- **Admin sharing of the read model.** The admin list reuses the flags but not the public DTO; unifying the DTOs is deferred until a third consumer exists (rule of three).

## Risks

| Risk | Mitigation |
| --- | --- |
| False positives (`Bescheid`, `Kontaktformular`, annex names) appear publicly | Banner (D16); completeness ranking pushes sparse ones down; hide list is the first follow-up |
| Public screenshot route spends R2 reads | Immutable cache, ETag/304, budget guard answers 503, list never loads images |
| SQL consensus diverges from the Python rule | Parity test over shared fixtures (chapter 2) |
| Machine route needs an API deploy before the live run | Recorded as the chapter 1 / LR blocker; the owner deploys; a `--host` fallback is documented in [02-live-runs.md](02-live-runs.md) |
| Manual rows are production data with no delete route | The `manual` marker makes them selectable; reversal SQL in the operator doc and the command's help; the curation file is committed and reviewed first; the set is capped at eight |
| Manual rows inflate `mention_count` and the roles of a candidate | Stated in the PR and operator doc; the admin Mentions table shows the `manual` extractor; ranking prefers completeness first so the effect on order is small |
| A curator's tag or edge is wrong | Edges need a verbatim, grounded excerpt; codes are validated against the closed taxonomy; `tag_note` records the reason; the owner reviews the file |
| Cloudflare browser quota or login walls leave pages without a screenshot | Handler releases on quota, completes login-wall pages with a note; flags show the gap; re-drain the next UTC day |
| Tooltip is the first in the app and may misbehave in jsdom | Chapter 8 tests the cell by its accessible description and the open state through the user event, with a documented fallback to `aria-label` text |

## Out of scope

Emit and voting UI, moderation, editing or deleting extracted rows, a curation web editor, translation of titles, search over mention text, authentication on the public pages, graph libraries, image resizing, changes to extraction or its guards, GitHub Actions workflow changes.
