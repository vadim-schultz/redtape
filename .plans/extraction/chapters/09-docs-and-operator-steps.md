---
name: "Chapter E9 — Docs sync and operator steps"
overview: "Synchronise the operations docs, loop document, READMEs and neighbouring plans with what the extraction suite shipped, add documentation contract tests, and publish the operator checklist (Workers AI token, plan check, probe, labelling, eval, schedule)."
todos:
  - id: runbooks
    content: "Update discovery-layer, discovery-online, scheduled-jobs, deployment-checklist and the ingest README"
    status: pending
  - id: loop-doc
    content: "Create docs/operations/loops/extraction.md"
    status: pending
  - id: neighbours
    content: "Mark discovery-layer chapter 21 superseded; point crawlers docs at this suite"
    status: pending
  - id: tests
    content: "Documentation contract tests and a link check"
    status: pending
  - id: operator
    content: "Operator checklist X1-X10 with commands"
    status: pending
isProject: false
---

# Chapter E9 — Docs sync and operator steps

**Repo:** `redtape` (`docs/operations`, `.plans`, `apps/discovery-ingest/README.md`, `apps/api/tests`) · **Branch:** `docs/extraction-docs-sync` · **Status:** planned

**Depends on:** [E1](01-staging-groundwork.md)–[E8](08-admin-display.md) · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/extraction`

## Goal

Leave the repository describing what exists, and collect every manual action in the order it is needed. This chapter changes documentation and documentation tests only; code found to be wrong goes to the ledger and its own chapter. It also completes what the crawlers revision deliberately left for later: the operator docs that still say "Supabase bucket" or "about 960 minutes" are corrected by crawlers chapter 21; this chapter covers the extraction side.

## Documentation targets

| Document | Update |
| --- | --- |
| `docs/operations/discovery-layer.md` | The `llm_extract` kind and its budgeted nature, the `issued` role, mention conditions and tag columns, candidate edges, the taxonomy route, the tag consensus rule |
| `docs/operations/discovery-online.md` | The LLM drain: neuron budget, the ledger, the stop reasons `llm_budget`, `llm_quota`, `db_limit`, release-not-fail, the result notes, triage by note |
| `docs/operations/scheduled-jobs.md` | `discovery-llm.yml`, `discovery-llm-probe.yml`, the variable `DISCOVERY_LLM_SCHEDULE`, the Workers AI secret used only by them, the shared concurrency group |
| `docs/operations/deployment-checklist.md` | `BUDGET_NEURONS_DAILY` (an API variable) and that the Workers AI token is deliberately **not** a Render variable |
| `docs/operations/loops/extraction.md` (new) | Chief-of-staff instructions in the format of `loops/crawlers.md`: plan folder `.plans/extraction/`, loop branch `feat/extraction`, chapter order, rules for implementers (the invariants), operator dependencies, what the suite delivers, known gaps |
| `apps/discovery-ingest/README.md` | `llm probe`, `llm eval`, `llm requeue`, `budget show`, the settings, and the local drain command |
| `.plans/README.md` | Extraction entry status |
| [discovery-layer chapter 21](../../discovery-layer/chapters/README.md) | Mark the deferred LLM-extract flag **superseded by this suite** |
| [crawlers gaps](../../crawlers/gaps-and-decisions.md) | The "LLM extraction" seam row points to the shipped state |

## TDD and documentation gate

**Red** (`apps/api/tests/test_extraction_docs.py`, same style as `test_discovery_operations_runbook.py`)

1. `extraction docs mention the llm_extract kind, the neuron budget, the ledger and release-on-limit`.
2. `extraction docs state that nothing is emitted automatically and that edges are staged, not emitted`.
3. `extraction docs state that the Workers AI token is not a Render variable and that the account stays on the Workers Free plan`.
4. `extraction docs describe the grounding rule and the tag consensus threshold`.
5. `docs do not claim translation, per-document tags, edge emit or automatic emit as shipped` — negative scope contract.
6. `every relative link in the extraction plan folder and the changed runbooks resolves`.
7. `plans README lists eleven extraction chapters`.

**Green:** update the documents until the checks pass. **Refactor:** docs only; report "no code refactor needed".

## Operator steps

Copied into `docs/operations/` as `extraction-operator-checklist.md`; each step is ticked with a date and, where relevant, a run ID or a local command. Merging a chapter never waits for a step; steps unlock **live gates**. The crawlers steps S15–S21 (Cloudflare token, plan, billing notifications, ledger caps) come first.

| Step | Needed before |
| --- | --- |
| X1, X2, X3 | the E4 probe |
| X4 | the first model run (optional: defaults are safe) |
| X5 | E4 live gate |
| X6 | the E5 eval |
| X7 | E5 decision, then E7 |
| X8, X9 | E7 live gate, then ongoing |
| X10 | after E7, before any emit that carries tags |

**X1 — Create the Workers AI token.** Cloudflare dashboard → My Profile → API Tokens → Create Custom Token. Permission: the narrowest Workers AI permission the probe proves sufficient (start with **Account · Workers AI · Read**; add Edit only if the probe is refused), limited to this account, no client IP filter. Copy it once. It is **not** a Render variable, not the Browser Run token, and never committed.

**X2 — Store the secrets.** `gh secret set CLOUDFLARE_AI_API_TOKEN` (and confirm `CLOUDFLARE_ACCOUNT_ID` exists from crawlers S16). Only `discovery-llm.yml` and `discovery-llm-probe.yml` use them. Export both for local runs.

**X3 — Confirm the free plan.** Dashboard → Workers AI usage and Workers plans: the account is on **Workers Free**; the daily neuron meter is visible (10,000 neurons). Do not upgrade to Workers Paid: Workers AI would then bill past the free allowance. Record the date and the plan name (crawlers S19 holds the billing notifications).

**X4 — Optional: set `BUDGET_NEURONS_DAILY` in Render** (default 9,500, 95 percent of the allowance, set by [E11](11-free-tier-caps-95.md)). Tighten it if other Cloudflare workloads also use Workers AI, because only 500 neurons a day are left unreserved. Check with `GET /machine/budgets`.

**X5 — Run the probe (chapter E4 Step 0).** Locally with the two variables exported. Note the dashboard's neuron counter before and after. Record the table and the observed neurons.

**X6 — Label the gold set (about an hour).** Pick twenty rendered snapshots (`discovery-fixture-capture.yml`, at least five hosts), write a `.gold.json` for each as specified in chapter E5, commit them.

**X7 — Run the eval and choose.** The chapter E5 commands over two days; write decision X14; set `llm_model` and `PROMPT_VERSION`; turn `llm_enqueue` on for the render worker.

**X8 — Backfill and drain.** `python -m discovery_ingest llm requeue --limit 50`, then drain locally (command in chapter E7) once a day. Watch `neurons_used` and the stop reason; the ledger caps stop overspend, the dashboard confirms it.

**X9 — Enable the schedule (optional).** Set `DISCOVERY_LLM_SCHEDULE=enabled` only after the E7 live gate and only if the monthly Actions allowance has room (crawlers S20). To pause, delete the variable; manual dispatch keeps working.

**X10 — Review before emitting tags.** Read ten candidates' suggested tags against their procedures in the admin; compare with the eval's tag agreement; if they disagree, leave tags out of emit (the thresholds are settings) and record the finding. Candidate emit itself stays the crawlers routine S10.

**Rotation and rollback.** Rotate: create a new token (X1), replace the secret, run the probe, delete the old token. Roll back: delete `DISCOVERY_LLM_SCHEDULE` and the Cloudflare AI secret, or switch `llm_enqueue` off; pending `llm_extract` tasks wait harmlessly and the render and fetch drains are unaffected.

## Verification

```bash
cd apps/api && python -m pytest tests/test_extraction_docs.py tests/test_crawlers_docs.py tests/test_discovery_operations_runbook.py
gh pr checks --watch
```

The operator ticks each step in the checklist and the ledger. The suite's release checklist in [../run-ledger.md](../run-ledger.md) is complete only when X1–X8 and X10 are recorded with dates and run IDs (X9 is optional).

## Out of scope

Rewriting source-canon documents, editing other suites' statuses beyond the two pointers above, automating console steps, alerting integrations, new features.
