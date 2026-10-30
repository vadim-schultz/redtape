# Candidate view (chief of staff)

A public, read-only candidate list and item view (ingress and egress dependency cards and a flow diagram) on top of the staged candidates of the extraction suite, one completeness read model shared with the admin, the screenshot collection that makes the pages worth opening, a handful of hand-completed showcase candidates to check the pages against, a repaired admin documents table, and distinct admin catalogue and coverage pages.

Plan suite: [`.plans/candidate-view/`](../../../.plans/candidate-view/) on `main`.

**Loop branch:** `feat/plans-candidate-view`  
**Release branch:** `main`

**Prerequisites:** the [extraction](../../../.plans/extraction/01-rollout.md) suite is on `main` (PR #260). GitHub Actions minutes are exhausted until about 2026-11-01, so every gate is local.

## How to run

1. Merge the plan suite on `main` (docs PR) so the chief of staff's preflight passes.
2. Bootstrap the loop branch per the chief-of-staff `git-model.md` skill.
3. Launch **chief of staff** with plan folder `.plans/candidate-view/`.
4. One **chapter-implementer** per chapter, in the execution order of [01-rollout.md](../../../.plans/candidate-view/01-rollout.md); each PR targets the loop branch only.
5. After chapter 1, the chief runs **LR1, the screenshot collection**, of [02-live-runs.md](../../../.plans/candidate-view/02-live-runs.md). It needs the owner to deploy the API (the machine sources route). Without the deploy the run records a blocker and the chapters that need no screenshots continue.
6. After chapters 2, 3 and 11 and LR1, and a second owner API deploy (override and public list), the chief runs **LR2, the showcase curation**: it picks the highest-ranking candidates, reads their pages, writes a reviewed curation file, applies it with `candidates curate` (everything marked `manual`), and captures their screenshots. Both live runs happen before chapter 10.
7. When the ledger is complete, open the release PR **loop branch to `main`**. The owner then deploys the API first, then the web, and a human performs the smoke checks in `docs/operations/candidate-view.md`, section Release smoke checks (written by chapter 10).

## Status

Planned: eleven chapters (chapter 11 executes after chapter 2) and two live runs. No chapter started.

## Exit criteria

- `/candidates` and `/candidates/:id` are public, show every candidate ranked by completeness, and the item page shows ingress and egress cards and the diagram.
- Five (at most eight) showcase candidates are complete in the public list, all marked `manual`, with the curation file reviewed and committed.
- At least some candidates have a screenshot, collected within the browser-seconds cap, and the public route serves it with cache headers.
- `/admin/discovery/documents` has its toolbar in the table header, every column sorts and filters where the API allows it, and long titles are clipped with a tooltip.
- Catalogue and coverage show different top blocks.
- `./ci.sh` is green on the loop branch.
