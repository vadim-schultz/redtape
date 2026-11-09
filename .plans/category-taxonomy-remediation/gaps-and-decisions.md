# Category taxonomy remediation — Gaps and decisions

**Architecture:** [00-architecture.md](00-architecture.md) · **Rollout:** [01-rollout.md](01-rollout.md) · **Ledger:** [run-ledger.md](run-ledger.md)
**Reviewed suite:** [../category-taxonomy-migration/gaps-and-decisions.md](../category-taxonomy-migration/gaps-and-decisions.md)

This file records decisions that chapters must consume. A chapter may add a decision only when it records the reason, the affected contracts, the migration consequence, and the rollback consequence.

## Decisions carried in (D-R1 to D-R10)

| ID | Decision | Status | Consequence for chapters |
| --- | --- | --- | --- |
| D-R1 | **Recovery source.** The free tier has no backups. The archive schema `legacy_taxonomy_archive` in the same database is the only recovery source for retired rows. Integrity is proven by count and checksum (chapter 03), not by `pg_dump`. | Accepted by user | C3 verifies in-transaction. C13 forbids `pg_dump` and writes. Supersedes the earlier `pg_dump` rehearsal. |
| D-R2 | **Single source under `apps/api`.** The contract lives in the API source tree. Ingest reads no file. It fetches the PVOG leaf crosswalk from the machine taxonomy endpoint once per harvest. | Accepted by user | C1 moves the artifact. C4 adds the fetch and deletes the `.plans` copy. |
| D-R3 | **Worker-suggested categories.** Codes suggested by worker models are accepted automatically when their LLM-only score is at or above `MIN_SUGGESTED_SCORE` (0.05). Accepted codes carry confidence. No gate, parity check, or backfill needs a human. Calibration is deferred to a later suite. | Accepted by user | Amends the earlier architecture section 5 for the automatic floor only. The floor stays as an automatic inclusion rule. |
| D-R4 | **Completeness denominator.** Five completeness flags became four (`has_category` replaces `has_domain` and `has_situation`). | **Accepted by user 2026-11-06: four flags** | Unblocks C5. C5 records the rule in this file. |
| D-R5 | **Artifact freeze scope.** The inventory and the legacy crosswalk are frozen. Migrations read only those. PVOG leaf states may be amended in place, with a reason and date. | Accepted in this suite | C1 and C9. The C9 edit must not change the frozen-section hash. |
| D-R6 | **Loop branch.** Stay on `feat/plans-category-taxonomy-migration`. Chapters integrate there. PR 370 is the release PR into `main`. | Accepted by user; **deliberate deviation** from the chief-of-staff default, which expects a suite-specific loop branch | Every chapter integrates on the shared branch. |
| D-R7 | **Plan-only session.** This session writes suite documents only. Implementers are launched in a later session. | Accepted | No chapter code runs in this session. |
| D-R8 | **Old bookmarked URLs.** Old `domain`, `situation`, and `group` links show an unfiltered list. No compatibility code is added. | Accepted | The run ledger records this as known behaviour. |
| D-R9 | **Review-state PVOG leaves.** Keep publishing them. Each leaf gets a recorded reason and date. A test pins the behaviour. | Accepted by user | C9. |
| D-R10 | **Template gap.** The chief-of-staff skill names `.plans/PLAN_TEMPLATE.md`, which does not exist in this repository. | Accepted in this suite | This suite follows the shape of `category-taxonomy-migration`. Creating the template is out of scope. |
| D-R11 | **C4 scope (2026-11-06, user).** The touch set is widened to the crosswalk consumers. The legacy crosswalk is served from the machine response until C7 removes it. | Accepted by user | C4 is integrated. C7 must also remove the legacy crosswalk from the machine response, which is a new API touch for C7. |
| D-R12 | **`accepted_on` (2026-11-06, user).** The 32 leaves that were already `mapped` get `accepted_on` `2026-11-06`. | Accepted by user | C9 is integrated. The date is not persisted (DD4), and it is observed only. |
| D-R13 | **Leaves `1040100` and `1060700` (2026-11-06, user).** Keep the current targets (`education-and-training`, `death-and-estate`). They are exempt from the harvest-evidence assertion by name. | Accepted by user | C9 is integrated. A later harvest path for either leaf needs its own decision. |
| D-R14 | **Canonical schema drift (2026-11-09).** Production contains the exact empty canonical taxonomy tables and indexes while `alembic_version` remains at `20261104_document_normalized_url`. | Accepted for the release candidate | The expand migration adopts only that exact empty schema and rejects partial, column-drifted, or non-empty pre-existing tables. |

**D-R14 detail:** The drift affects the expand migration and the production startup path. The release candidate now adopts the exact empty objects so the backfill and retirement revisions can continue; any unexpected shape or existing data aborts before mutation. The existing downgrade remains the rollback boundary for the additive schema and drops the adopted tables, which are empty at this gate.

## Open decisions

### D-R4 — Completeness denominator (decided 2026-11-06: four flags)

- **Options:** four flags (`has_category`, `has_edges`, `has_snapshot`, `has_screenshot`) or five flags (restore `has_domain` and `has_situation` as separate checks).
- **Decision:** four flags, confirmed by the user on 2026-11-06. C5 records the rule as accepted, with a before-and-after ordering report for the fixture set.
- **Affects:** the completeness repository, public order, `filter[complete]`, the parity fixture, and `docs/operations/candidate-view.md`.
- **Reason it is open:** the earlier suite left the choice to product. The review found that the change was made without a recorded decision.

### Archive owner and drop date

- **Required:** a named owner for `legacy_taxonomy_archive` and a date after which the archive schema may be dropped.
- **Who decides:** the user. Chapter 12 records both values. Chapter 13 confirms them against the release candidate.
- **Decision (2026-11-09):** owner `punasika`; drop date `2026-11-16`. The archive is kept until that date.

### PR 369 merge (pre-flight)

- Merge [PR 369](https://github.com/vadim-schultz/redtape/pull/369) with a merge commit before C0 starts. A human performs the merge. Record the commit in the ledger.

## Carried decisions from the earlier suite (O2, O4 to O7)

| ID | Question | Status | Decision and evidence |
| --- | --- | --- | --- |
| O2 | Score combination for old links that map to one category | **Decided** | Maximum confidence. `score_combination = "max"` in `category_backfill.py`. Replay keeps this rule (C2): the stored value and the projection are merged with `max`. |
| O4 | Compatibility duration for `domain`, `group`, and `situation` parameters | **Boundary date decided 2026-11-06: release day** (the day PR 370 merges to `main`). The window for cached web bundles is still open until C8's production payload check is recorded. | Stop accepting the parameters from the boundary, and answer with a 422 that names the parameter. The user chose the release day as the boundary. C8 records the window for cached bundles. |
| O5 | Whether list cards remain whole-card links | **Confirmed by C12** (`DocumentCard.tsx`: title link plus sibling chip links, no nested anchors) | Default: linked title region plus independent category chip links. No nested anchors. C12 checks the shipped markup and records the result. |
| O6 | Accordion URL state | **Confirmed by C12** (`CandidateDetailContent.tsx`: `Accordion.Root multiple defaultValue`, no URL state) | Default: local state with stable defaults. Add URL state only if deep-linking to evidence or sources is a demonstrated need. C12 checks the shipped behaviour. |
| O7 | Empty source behaviour | **Reopened by C12 (2026-11-06).** The shipped sources accordion has no empty state. `CandidateSources.tsx` has none, and no `sources_empty` copy exists in `en.json` or `de.json`. The default in the earlier suite was: keep the accordion with a localized empty state. **Decision needed from the user:** implement the empty state, or accept no empty state and record that. | The shipped copy differs from the default, so the item stays open. |

O2 and O4 are decided in substance. O5 to O7 are marked decided in C12, which must cite the shipped code or copy as evidence. If the shipped behaviour differs from the default, C12 reopens the item here and does not change the default silently.

## Review findings — decisions and deviations

| Finding | Decision | Note |
| --- | --- | --- |
| H1 | Archive, count and checksum, and a read-only preflight replace the `pg_dump` rehearsal. | The earlier todo listed `pg_dump` restore rehearsal. D-R1 supersedes it. |
| M1 | The replay merge rule is confidence `max`, and a non-legacy row keeps its source and provenance. | Matches O2. |
| M2 | The artifact moves into `apps/api`. Ingest fetches the crosswalk. | D-R2. |
| M3 | Four flags are the default. | D-R4 open. |
| M4 | Confidence opacity is removed from chips. | Confidence stays in data and tests. |
| M5 | Whole-file exemptions are replaced by reasoned line allowances. | Allowlist entries must name real files. |
| M6 | Legacy translators and legacy PVOG modules are removed after C8. | C7 depends on C8. |
| M7 | The compatibility boundary is recorded before removal. | C8 is chief-of-staff work. |
| M8 | Review-state leaves stay published with reasons and dates. | D-R9. |
| L1, L2 | Stale C9 and C10 statuses are corrected. Stale worktree copies under `.worktrees/` are removed or ignored only with user approval. | C12. |
| L3, L4 | Docs and empty-state copy are corrected. | C12 and C6. |
| L5, L6, L7 | `SourceCard` stays inline until a second variant appears. Duplicate traversal is removed. The `candidates_api` docstring is fixed. | C11. |
| L8 | Archive owner and drop date are recorded. | Open until the user supplies them. |
| Chip size wording | The code uses `size="sm"`. The docs are corrected to match. | C12. |

## Migration risks

| Risk | Required mitigation |
| --- | --- |
| Replay overwrites a promotion-written row | C2 tests the case and keeps source and provenance. C13 checks promotions after C2. |
| Archive copy is incomplete or differs from the source | C3 compares count and checksum inside the migration transaction and aborts on mismatch. |
| Unmapped, ambiguous, or conflict rows are dropped silently | C3 aborts on any non-zero count and logs the full report. C13 blocks C14 until the user decides. |
| Old workers still send domain or situation codes | C8 checks worker runs before C7 removes the translators. |
| Cached web bundles call removed parameters | C8 records the 404 and 422 window in the ledger. |
| Completeness public order changes without a decision | C5 is blocked until D-R4 is confirmed. |
| Database loss (no backups) | Out of scope. Needs a separate infrastructure decision. Recorded in the architecture. |
| Deploy from `main` runs the retirement migration on Render startup | `render.yaml` and `apps/api/scripts/start.sh` run `alembic upgrade head` on every start. C14 must not merge until the user approves a deploy plan that includes C13 evidence. Open item for the user. |

## Rejected alternatives

- **`pg_dump` as the only recovery path.** The free tier has no backups, so this is not available (D-R1).
- **Reading the artifact from `.plans/` at runtime.** It couples production to a documentation folder (D-R2).
- **A human acceptance gate for worker codes.** D-R3 accepts worker codes automatically.
- **Confidence opacity on chips.** It encodes an internal score in the UI and is removed (C6).
- **Permanent compatibility code for old URLs.** D-R8 accepts unfiltered lists for old bookmarks.
- **Unpublishing review-state leaves.** D-R9 keeps them published with reasons.
- **Creating `.plans/PLAN_TEMPLATE.md` in this suite.** Out of scope (D-R10).
