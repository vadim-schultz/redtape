---
name: "Chapter E19 — Neuron overshoot"
overview: "Let the neuron meter spend up to the daily cap by granting a reservation while the day or the run is below its limit, even when the estimate crosses it, so a day no longer stops 140 to 900 neurons early; overshoot is at most one call and the cap, the ledger API and Cloudflare's own 429 stay as they are."
todos:
  - id: run-budget
    content: "Run budget denies only at or above the limit, not when used plus the estimate would pass it"
    status: pending
  - id: ledger-clamp
    content: "A ledger denial with neurons left retries once with the remaining amount; the settlement corrects upward"
    status: pending
  - id: messages-docs
    content: "Help text, stop messages, architecture section 9 and the drain runbook say the last call may pass the budget by its own cost"
    status: pending
isProject: false
---

# Chapter E19 — Neuron overshoot

**Repo:** `redtape` (`apps/discovery-ingest`, docs) · **Branch:** `feat/extraction-neuron-overshoot` · **Status:** planned

**Depends on:** [E4](04-workers-ai-client-and-probe.md) (meter), [E6](06-llm-extract-handler.md) (handler), [E11](11-free-tier-caps-95.md) (cap 9,500), [E14](14-raise-the-input-cap.md) (page-sized reservation) · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/extraction`

**Order:** executes after [E9](09-docs-and-operator-steps.md), first of the chapters added on 2026-10-30. Owner decision 2026-10-30 (decision X18 in [gaps-and-decisions.md](../gaps-and-decisions.md)): the day should reach the 9,500 cap, and an overshoot is acceptable because it is small with the models in use.

## Goal

On 2026-10-29 the ledger stopped well below the cap. Two rules cause a day to end early:

1. `NeuronMeter.reserve` ([meter.py](../../../apps/discovery-ingest/discovery_ingest/extract/llm/meter.py)) denies a call when `used + estimate > run_limit`.
2. The ledger grants a reservation only when `used + amount <= cap` (`reserve_ledger` in `apps/api/app/features/discovery/repository/budgets.py`).

The estimate is an upper bound: a 30,000-character page reserves about 140 neurons on Qwen and about 900 on the 70B, and the real answer usually costs less. Near the cap the next page is refused although the day still has neurons, so a day ends 140 to 900 neurons short and the same shortfall hits every per-run `--neuron-budget` (the drain, the eval).

After this chapter a call is allowed while the run and the day are still **below** their limits. The call may take the total past the limit by its own cost (at most one call per run). Cloudflare's own 429 (code 4006) remains the hard stop.

## Contract

1. **Run budget.** `reserve` denies with `Denied("run_budget")` only when `self._used >= self._limit`. `open_neuron_meter` still caps the run limit at what the ledger has left today, so a run opened on a nearly spent day still overshoots by one call at most.
2. **Ledger clamp.** When the guard denies the estimate and its answer reports `remaining` above 0, `reserve` asks once more for exactly `remaining` (a grant is then certain unless another worker spent it in between). The `Reservation` carries the clamped amount; `settle` corrects it to the reported cost through `adjust`, which the ledger never refuses, so the ledger records the true cost. A second denial, or `remaining` of 0 or less, is `Denied("ledger")`. An exhausted day is denied by the ledger in both attempts (negative case).
3. **Neurons only.** R2 operations keep the strict rule because they bill past the free tier. No API change, no migration, no Render deploy; `reserve_ledger` is untouched.
4. **Messages.** The `--neuron-budget` help text of `llm eval` and `worker drain` says the run stops once the budget is reached and the last call may pass it by its own cost; the eval and drain stop messages (`refusal_stop`, `_budget_stop`, the `llm_budget` note) no longer claim "would pass".
5. **Docs.** One sentence in [00-architecture.md](../00-architecture.md) section 9 (Reserve, then adjust) and in `docs/operations/discovery-online.md` (the LLM drain): overshoot is at most one call; the `ext-5` docs tests stay green.
6. **No change** to the price table, `reserved_output_tokens`, the cap (9,500), the stop reasons, the fail-open ledger read or the release-not-fail rule.

## TDD loops

### Loop A — Run budget

**Red** (`apps/discovery-ingest/tests/test_neuron_meter.py`, the fake guard that already exists there)

1. `a reservation that would pass the run limit is granted while used is below the limit`.
2. `a reservation is denied with run_budget once used has reached the limit`.
3. `after an overshooting call settles, the next reservation is denied` (the run stops after one call).
4. `without a ledger the run budget alone overshoots by one call and then stops` (use_ledger false).
5. `open_neuron_meter still caps the run limit at what the ledger has left` and `returns None on an exhausted day` (regression).

**Green:** change the comparison in `reserve`. **Refactor:** keep `reserve` at five lines or fewer by moving the decision to a small named helper.

### Loop B — Ledger clamp

**Red** (same file; extend the fake guard so `reserve` can deny and report `remaining`)

1. `a ledger denial with neurons left retries with the remaining amount and grants it`.
2. `the clamped reservation settles to the reported cost through one adjust call` (the ledger ends at the true cost, above the cap by the overshoot).
3. `a ledger denial with no neurons left is Denied("ledger")` and `an exhausted day is denied on both attempts` (negative).
4. `a ledger outage on either attempt returns LedgerUnavailable` (regression of E6).
5. `refund of a clamped reservation gives back only what was reserved`.

**Green:** in `_ledger_refusal`, on a denial with `answer.remaining > 0` call `self._guard.reserve(RESOURCE, answer.remaining)` once and return the clamped amount to `reserve`. **Refactor:** `Reservation.neurons` is the only place the granted amount lives; `NeuronMeter` stays at about a hundred lines (it is already over the guideline: do not grow it, extract the retry into a helper or a small `LedgerReserver` if needed).

### Loop C — Messages and docs

**Red** (`tests/test_llm_eval_command.py`, the drain CLI parser test, the docs tests in `apps/api/tests`)

1. `the --neuron-budget help of llm eval and worker drain says the last call may pass the budget`.
2. `the eval stops with a budget message that does not say would pass` and `the drain note for llm_budget matches`.
3. `architecture section 9 and the drain runbook state that overshoot is at most one call` (substring checks in `test_extraction_docs.py`).

**Green:** edit the strings and the two docs. **Refactor:** none expected.

## Verification

```bash
cd apps/discovery-ingest && ruff format --check . && ruff check . && mypy discovery_ingest && python -m pytest -q
cd apps/api && python -m pytest tests/test_extraction_docs.py tests/test_extraction_docs_structure.py -q
```

No live call. The effect is checked in the live runbook ([../02-live-runs.md](../02-live-runs.md)): `GET /machine/budgets` at the end of the day should read at or slightly above 9,500, not 8,600.

## Out of scope

Server-side `reserve_ledger`, any other resource, raising the cap above 9,500, the difference between Cloudflare's count and the ledger (checkpoint in the live runbook), changing prices or the reservation formula.
