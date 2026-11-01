---
name: Discovery throughput — Gaps and decisions
overview: "Settled decisions for the budget split, same-day scheduling, optional situation codes, and completeness-first queue ordering."
isProject: false
---

# Discovery throughput — Gaps and decisions

**Architecture:** [00-architecture.md](00-architecture.md) · **Rollout:** [01-rollout.md](01-rollout.md)

## Settled

| # | Decision |
| --- | --- |
| D1 | **The 2000/1000/1000 split is a new convention, not a reconciliation, and is unverified.** Every current doc and test (`apps/api/tests/test_budget_caps_ratio.py::test_the_actions_minutes_budget_stays_a_repository_share_of_the_account_pool`, `docs/operations/scheduled-jobs.md`, `docs/operations/deployment-checklist.md`, [gha-budget/00-architecture.md](../gha-budget/00-architecture.md)) states this repository's confirmed share as 1,000 minutes/month out of a 2,000-minute GitHub Free-plan pool *shared across every repository on the account* (other repos reportedly used roughly 1,040 min/month per the gha-budget notes). The user's new numbers assume this repository's share has since grown to 2,000, or other repos' usage has dropped. **This is flagged for the user to confirm before chapter 1 ships** — not silently reconciled — since over-claiming the shared pool risks the same account-wide lockout `docs/operations/gha-budget.md` already recorded once. |
| D2 | **The split is implemented via `BUDGET_ACTIONS_MINUTES_MONTHLY=2000`, `ACTIONS_CI_RESERVE_MINUTES=1000`.** The usable drain cap is derived live as `BUDGET_ACTIONS_MINUTES_MONTHLY − ACTIONS_CI_RESERVE_MINUTES` (confirmed formula: `apps/api/app/features/discovery/budget_resources.py:39-40`, `_actions_minutes_cap`), giving a derived scheduled-drain cap of 1000 — matching "1000 to scheduled tasks, 1000 to CI" exactly, with no other code change needed. |
| D3 | **Both the Python defaults and the Render-dashboard override move to the new numbers.** `apps/api/app/config.py:75-80` defaults change so any environment without an explicit Render override also reflects the new convention; the Render dashboard is still set explicitly as the authoritative production value (defense in depth, matching existing practice). |
| D4 | **Only `situation_codes` becomes optional**, via `default_factory=list` on `PageExtraction.situation_codes` (`apps/discovery-ingest/discovery_ingest/extract/llm/schema.py:71`). `domain_codes` (line 70) keeps its required `Field(max_length=...)` with no default — this is the exact scope of the user's literal ask, not extended by inference. |
| D5 | **This suite supersedes [discovery-operations](../discovery-operations/gaps-and-decisions.md) decision D7's ordering clause.** D7 says "priority/created ordering" is a preserved guarantee; this suite replaces created-time tie-breaking within a priority tier with page-completeness-desc, for the throughput goal `candidate-view` explicitly left open rather than ruled out ([01-capture-requeue.md](../candidate-view/chapters/01-capture-requeue.md) and [00-architecture.md](../candidate-view/00-architecture.md) both say "not this chapter" for completeness-based task choice, not "never"). D7's other clauses — 1–50 claim limit, 15-minute lease, reclaim-on-claim, idempotent catalogue upsert, fingerprint dedup — are unaffected and stay in force. |
| D6 | **Page-level completeness is a new, simpler parallel computation, not a reuse of `candidate_completeness_flags.py`.** Confirmed against the real schema: `DiscoveryCandidateMention`, `DiscoveryCandidateEdge`, and `DiscoveryArtifact` all carry `catalogue_service_id` directly (confirmed via their `UniqueConstraint`s and FK columns in `apps/api/app/models/discovery/discovery_candidate_mention.py` and `discovery_candidate_edge.py`). So the page-level flags are plain `EXISTS`/non-empty checks against `catalogue_service_id` — no join through `DiscoveryDocumentCandidate` and no consensus-threshold `axis_acceptance` logic needed. This is explicitly a queue-ordering heuristic, not a redefinition of "complete" for candidate lists; the canonical per-candidate `completeness_subquery`/`completeness_order` is untouched. |
| D7 | **Workflow restructuring is pure YAML and docs, no application code.** `--kinds` is already a free-form comma-separated list on every drain workflow, so splitting `extract_page` and `capture_screenshot` into their own scheduled files needs no CLI or worker code change. |
| D8 | **Activating the LLM fan-out needs one more variable than "enabled."** Confirmed at `apps/discovery-ingest/discovery_ingest/worker/llm_setup.py:86-100` (`prepare_llm_enqueue`): the hook only wires up when `settings.llm_enqueue` is true **and** `"render_page" in policy.kinds`; if `llm_enqueue` is true but `llm_model` is unset, it raises `LlmSetupError` rather than silently skipping. Chapter 2 must set **both** `LLM_ENQUEUE: "true"` and `LLM_MODEL: ${{ vars.DISCOVERY_LLM_MODEL }}` in `discovery-render.yml`'s job env, or the render workflow will hard-fail once the flag is on. |
| D9 | **The concurrency group is renamed `discovery-drain` → `discovery-pipeline`** across all five workflow files plus `platform-maintenance.yml`'s `discovery` job, now that it spans five scheduled files instead of two. Purely cosmetic; documented so the rename doesn't read as a behavior change. |

## Open seams

| Seam | Forcing condition |
| --- | --- |
| Account-wide GHA pool headroom | D1 is unverified; if the account pool hasn't grown, the new cap will fail the same way a prior overrun already did |
| Render-dashboard env change execution | No Render API access is available from a chapter-implementer session; `BUDGET_ACTIONS_MINUTES_MONTHLY`/`ACTIONS_CI_RESERVE_MINUTES` on Render must be set by a human, same as every existing `docs/operations/*-checklist.md` step |
| Page-level completeness query performance | No new index is proposed; if claim latency grows under load, a materialized/indexed page-completeness column is the deferred fix, same shape as `candidate-view`'s already-deferred persisted-completeness column |
| `domain_codes` leniency | Not in scope now; if the LLM later struggles with domain classification too, it needs its own decision, not a silent extension of D4 |
| Backlog overflow across stage boundaries | The same-day design assumes each stage's batch/time bound covers that day's volume; a sustained backlog still slips by whole days, just fewer of them than today |

## Deferred

- A persisted/materialized page-level or candidate-level completeness column (currently always computed on the fly).
- Extending optional-code leniency to `domain_codes`.
- Any fourth queue-ordering factor beyond priority, completeness, and created_at.
- Any `apps/crawler` or evidence-storage work (out of this suite per discovery-operations' existing boundary).
