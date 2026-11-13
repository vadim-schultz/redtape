---
name: "Chapter 3 — Neuron reconciliation spike"
overview: "Decide whether the 2026-11-11 neuron refusal (code 4006 at 7.3k of 9.5k in the ledger) comes from a rolling window, unledgered spend or estimate error, before any rolling ledger is built."
todos:
  - id: daily
    content: "Compare the ledger with Cloudflare's usage for each UTC day from 2026-10-30 to today"
    status: pending
  - id: unledgered
    content: "List every neuron-spending path that bypasses the ledger (probes, operator CLIs)"
    status: pending
  - id: decision
    content: "Record the decision: calibrate the estimate, or build a rolling window"
    status: pending
isProject: false
---

# Chapter 3 — Neuron reconciliation spike

**Repo:** `redtape` · **Branch:** `feat/pipeline-optimisation-neuron-spike` · **Status:** planned
**Depends on:** none · **Decisions:** D7 · **Architecture:** [../00-architecture.md](../00-architecture.md) (section 2.4, waste 7)

**Loop branch:** `feat/plans-pipeline-optimisation` · **Release branch:** `main`

## Goal

On 2026-11-11 Cloudflare refused an embedding call with code 4006 (the daily allowance used up) while the ledger read 7,302.57 of 9,500. The working explanation in `.plans/search-first/run-ledger.md` is a rolling 24-hour window, which is not confirmed. Find the cause with data, so that the planner in chapter 12 is built on the right model.

## Design

- **Read-only comparison.** `scripts/neuron_reconcile.py` (standard library only) reads Cloudflare's account usage for Workers AI neurons per hour, and `python -m discovery_ingest budget show --resource neurons` for the ledger per UTC day. It prints one row per day: ledger used, Cloudflare used, the difference.
- **Unledgered spend.** Make a list of every path that spends neurons without the ledger: `llm probe`, `embed probe`, the `llm eval` path if it skips reservation, and any laptop run that hits the API with a different key. Record the probe spend from the probe reports the operator kept.
- **Estimate error.** For the last 20 `llm_extract` tasks, compare the reserved estimate with the neurons the model reported. `NeuronMeter.settle` keeps the estimate when `actual_neurons` is `None` (`apps/discovery-ingest/discovery_ingest/extract/llm/meter.py`), so count how often that happens in the run reports.
- **Rolling test.** If Cloudflare's usage shows that the 4006 refusal came while the trailing 24 hours was above 10,000 but the UTC day was below 9,500, record that the window is the cause. This is the only result that makes a rolling ledger necessary.
- **Operator input.** The Cloudflare read needs an account analytics token. Operator step S5 creates it; the token is never committed.

## Files

**Create**

- `scripts/neuron_reconcile.py`
- `.plans/pipeline-optimisation/run-ledger.md` (the decision, with numbers; created when the loop starts)

**Do not edit**

- Any application code. This chapter produces a decision, not a change.

## Red tests

There are no code tests for a spike. The gate is a recorded decision with the figures behind it.

| Check | Asserts |
| --- | --- |
| `the reconciliation table has one row per UTC day from 2026-10-30` | Happy: no day is missing. |
| `every neuron path is listed as ledgered or unledgered` | Negative check: a path with no answer blocks the decision. |

## Green

1. Write the script and run it against the ledger for the period.
2. Write the decision in the run ledger: one of "calibrate the estimate", "build a rolling window", or "both", with the figures that decide it.
3. If the decision is "build a rolling window", the work moves to a follow-up chapter. This chapter does not build it.

## Refactor gate

The script stays under one screen and has one function per data source. No dependency beyond the standard library.

## Verification

```bash
python3 scripts/neuron_reconcile.py --from 2026-10-30 --to 2026-11-13
```

Gate: the run ledger holds the decision, the table, and the list of unledgered paths. Chapter 12 reads the decision before it sets the neuron caps.

## Commits

`chore(scripts): compare the neuron ledger with Cloudflare usage` and `docs(plans): record the neuron reconciliation decision`.

## Out of scope

Building the rolling ledger, lowering `BUDGET_NEURONS_DAILY`, and changing any drain. The earlier suggestion to lower the cap to about 6,500 was withdrawn in `search-first` because the ledger was accurate to about 0.4%.

## Git workflow

```bash
git checkout feat/plans-pipeline-optimisation && git pull
git checkout -b feat/pipeline-optimisation-neuron-spike
```

Open the chapter PR into `feat/plans-pipeline-optimisation`.
