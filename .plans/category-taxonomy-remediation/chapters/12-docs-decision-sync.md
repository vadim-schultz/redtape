---
id: C12
depends_on:
  - C3
  - C5
  - C6
  - C7
  - C9
  - C10
  - C11
touches:
  - docs/planning/STATUS.md
  - docs/operations/discovery-online.md
  - apps/discovery-ingest/README.md
  - .plans/category-taxonomy-migration/gaps-and-decisions.md
  - .plans/category-taxonomy-migration/01-rollout.md
  - .plans/category-taxonomy-migration/run-ledger.md
  - .plans/category-taxonomy-migration/00-architecture.md
  - .plans/category-taxonomy-migration/chapters/09-legacy-retirement.md
  - .plans/category-taxonomy-migration/chapters/10-docs-sync-and-live-validation.md
execution: chapter-implementer
todos:
  - ch12-docs-decision-sync
---

# Chapter 12 — Docs and decision sync (L1, L2, L3, L8)

**Suite:** [README](README.md) · **Architecture:** [../00-architecture.md](../00-architecture.md) · **Rollout:** [../01-rollout.md](../01-rollout.md) · **Ledger:** [../run-ledger.md](../run-ledger.md)
**Reviewed suite:** [../../category-taxonomy-migration/00-architecture.md](../../category-taxonomy-migration/00-architecture.md)

**Batch:** B5 · **Execution:** chapter-implementer · **Status:** planned

## Goal

Bring the docs and the earlier suite's status records in line with the code and with this suite. Each stale claim is paired with a grep that finds it. The grep must fail before the change and pass after it.

## Boundaries

- `depends_on`: C3, C5, C6, C7, C9, C10, C11.
- `touches`: the nine files listed. Other docs are out of scope.
- Do not edit the ledger of this suite. The chief of staff records the evidence.
- Do not remove or ignore the untracked copies under `.worktrees/`. That needs user approval (see below).

## Stale claims (evidence pairs)

Each row is one stale claim. Write the grep, confirm it matches before the change (red), then fix the claim and confirm no match (green).

| Claim | File | Fix |
| --- | --- | --- |
| Five completeness flags (`has_domain`, `has_situation`) | `docs/planning/STATUS.md` | Four flags, matching the C5 decision |
| `domain_codes` in the public discovery description | `docs/operations/discovery-online.md` | Category codes only |
| Curation fields that the ingest no longer accepts | `apps/discovery-ingest/README.md` | Category fields only |
| Stale C9 and C10 statuses in the earlier suite | `.plans/category-taxonomy-migration/01-rollout.md`, `run-ledger.md`, chapter files | Reset to the status shown by the ledger |
| Chip size wording that differs from code | `docs/operations/candidate-view.md` or the ingest README, wherever it appears | `sm` |

## Decisions to record

- **O2:** decided, maximum confidence. Cite `score_combination = "max"` in `category_backfill.py`.
- **O4:** decided, 422 after the boundary. Cite the C8 ledger entry for the date.
- **O5, O6, O7:** decided from the shipped code or copy. Cite the file and the test that shows the behaviour. If the shipped behaviour differs from the default in [../gaps-and-decisions.md](../gaps-and-decisions.md), reopen the item there and do not change the default silently.
- **Archive owner and drop date (L8):** record both values if the user supplied them. If not, leave them open and say so.
- **Statuses:** set each affected status to `partial` wherever a live check is still pending (C13, C14).

## Red

- **Happy path (after the change):** every stale-claim grep returns no matches, and every relative link in the changed files resolves.
- **Negative path (before the change):** each stale-claim grep matches the stale text. A grep that does not match before the change proves nothing and must be rewritten.

## Green

- Apply the fixes in the table above.
- Record each O-item decision with its evidence.

## Refactor

- None expected. The docs have no code to refactor. State that in the ledger row.

## Gate

- Docs: run the grep for each row and the link check on the changed files. Record each pair (before and after) in the ledger row.
- Then `./ci.sh`, because `docs/` and READMEs may be read by tests.
- Corporate build block: [corporate-build-env.md](../../../.cursor/skills/chief-of-staff/corporate-build-env.md).

## Stale worktree copies

- Untracked `.plans/` copies under `.worktrees/chief-c9-legacy-retirement/` are stale (L2).
- Remove or ignore them only with user approval. This chapter reports them and waits for the decision. It does not delete them.
