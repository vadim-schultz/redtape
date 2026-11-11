---
name: "Chapter 03 — Character meter and floor"
overview: "Let the Azure engine spend the monthly character ledger safely: reserve exact characters before each call, settle to the billed figure, stop on denial without consuming attempts, and generalise the floor so that a document share can later sit above a protected card band."
id: AZ03
depends_on:
  - AZ02
touches:
  - apps/discovery-ingest/discovery_ingest/translation/character_meter.py
  - apps/discovery-ingest/discovery_ingest/translation/meter.py
  - apps/discovery-ingest/discovery_ingest/translation/metered.py
  - apps/discovery-ingest/discovery_ingest/worker/floored_meter.py
  - apps/discovery-ingest/discovery_ingest/worker/translate_meter.py
  - apps/discovery-ingest/discovery_ingest/worker/translate_drain.py
  - apps/discovery-ingest/discovery_ingest/budget.py
  - apps/discovery-ingest/discovery_ingest/operations/translate_drain.py
  - apps/discovery-ingest/discovery_ingest/operations/translate_ui.py
  - apps/discovery-ingest/tests/
execution: chapter-implementer
---

# Chapter 03 — Character meter and floor

**Repo:** `redtape` (`apps/discovery-ingest`) · **Depends on:** [Chapter 02](02-azure-engine-adapter.md) · **Decisions:** [D2](../gaps-and-decisions.md#d2--azure-ai-translator-f0-first-a-19-million-character-monthly-cap) · **Rules:** [../../../CLAUDE.md](../../../CLAUDE.md) (package registries) · **Status:** planned

## Goal

Make the Azure engine spend `azure_translator_chars` correctly. Each call reserves its exact characters, settles to what Azure bills, and stops cleanly on a denial or a quota error. The floor used for query embedding is generalised so chapter 11 can keep a card band for cards and interface strings.

## Scope

- In: `CharacterMeter`, the generalised `FlooredMeter`, the cap on the budget snapshot, per-resource ledger checks, `characters_used` in the drain report, and own-meter wiring in the drain and interface-string commands.
- Out: the document share as used by snapshots (chapter 11), the admin display (chapter 06), the workflow (chapter 05).

## Design

1. **`CharacterMeter`** (`translation/character_meter.py`) implements the existing `UsageMeter` protocol for `characters`:
   - `reserve`: all or nothing through `BudgetGuard.reserve("azure_translator_chars", amount)`. A refused reservation is a denial. There is no partial grant, because a partly-granted call would still bill in full.
   - `settle`: adjusts the reservation by the difference between the billed and reserved characters. `BudgetGuard.adjust` accepts a signed amount.
   - `refund`: gives back a reservation for a call that billed nothing.
   - `exhaust`: calls `BudgetGuard.exhaust` for the resource.
   - Its in-process state is protected by a lock, as `SubscriptionMeter` is, because the window runs calls concurrently.
2. **`Floor`** replaces the float in `FlooredMeter`: `Floor(resource: str, amount: float)`. The neuron floor becomes `Floor(RESOURCE, floor)`. The class no longer imports the neuron constant. The denial reason stays `"floor"`.
3. **`Remaining.cap`** (`budget.py`) gains `cap: float | None = None`, filled from the ledger row, so a floor can be computed from the cap.
4. **`DENIAL_TEXT["floor"]`** (`metered.py`) becomes generic: "the usage kept for other work would be used".
5. **Own-meter wiring.** `run_translate` builds `{"characters": CharacterMeter(guard)}` when the engine's unit is `characters`, and `run_translate_ui` does the same. Today `run_translate_ui` passes `{}`, so a characters engine exits 2. The neuron path is unchanged.
6. **Ledger check.** `check_neuron_ledger` becomes `check_ledger(engine)`. It checks the resource that matches the engine's unit: `neurons` for neurons, `azure_translator_chars` for characters. Other units are skipped. The mapping is one dictionary in `translation/meter.py`.
7. **Report.** The drain report and the CLI summary gain `characters_used` beside the existing counters. It is reported as an integer character count.

## Files

| Path | Change |
| --- | --- |
| `translation/character_meter.py` (new) | `CharacterMeter` |
| `translation/meter.py` | resource mapping per unit |
| `translation/metered.py` | generic floor denial text |
| `worker/floored_meter.py` | `Floor` value object, generic resource |
| `worker/translate_meter.py` | neuron floor passed as `Floor` |
| `worker/translate_drain.py`, `schemas.py`, `tally.py` | `characters_used` in tally and report |
| `budget.py` | `Remaining.cap` |
| `operations/translate_drain.py` | own-meter wiring; `check_ledger` |
| `operations/translate_ui.py` | own-meter wiring |
| `tests/` | new meter, floor and wiring tests; neuron regression tests unchanged |

## Red tests

**Happy path**
- `Character meter · reserve grants the exact characters when the ledger has room`
- `Character meter · settle to the billed figure adjusts the ledger by the difference`
- `Character meter · refund returns the reservation of a call that billed nothing`
- `Drain · an azure-translator run writes azure_translator_chars and reports characters_used, and never touches the neuron ledger`
- `Floor · a reservation that would leave remaining below the floor is denied for a monthly resource`
- `Floor · the neuron floor behaves exactly as before (parity test)`
- `Ledger · the check reads the resource matching the engine's unit`
- `Translate-ui · an azure-translator run is accepted with a character meter (no exit 2)`

**Negative path**
- `Character meter · a 10,000-character request with 4,000 remaining is denied and reserves nothing`
- `Character meter · an unreadable ledger is a denial, and no HTTP request is sent`
- `Drain · a 403001 calls exhaust once, releases the batch and leaves attempt_count unchanged`
- `Character meter · concurrent reserves from two threads never exceed the remaining amount`
- `Ledger · an unknown unit has no resource and is skipped, not an error`

## Green

The smallest change for each red test. Keep `NeuronUsageMeter` and the neuron floor behaviour intact; the parity test is the guard.

## Refactor gate

- `CharacterMeter` and `NeuronUsageMeter` both do reserve, settle, refund and exhaust. When the third repetition of a settle or refund body appears, extract a shared helper. Do not extract it earlier.
- `FlooredMeter` stays under about 60 lines and has no resource constant.
- The own-meter wiring is a single function that maps a unit to its meter. Do not add an if-chain per unit.
- House rules: about 5 lines per function, no boolean flags, at most 3 parameters.

## Verification

```bash
cd apps/discovery-ingest
.venv/bin/python -m pytest -q tests/test_translate_drain.py tests/test_translation_registry.py tests/test_budget_guard.py tests/test_neuron_meter.py tests/test_cli_budget.py tests/test_translate_cli.py tests/test_azure_*.py
.venv/bin/ruff format --check . && .venv/bin/ruff check . && .venv/bin/mypy discovery_ingest
cd ../.. && ./ci.sh
```

Update `tests/ledger_fakes.py` so `FakeLedger` handles `azure_translator_chars` as well as `neurons`.

## Out of scope

Snapshot drain and document share in use (11), the admin display (06), the workflow precheck (05), the glossary mode (05).

## Operator steps after merge

None.

## Git workflow

```bash
git checkout feat/plans-azure-translation && git pull
git checkout -b feat/azure-03-character-meter
# test(ingest): ... (red), feat(ingest): ... (green), refactor(ingest): ... (gate)
git push -u origin HEAD
# PR into feat/plans-azure-translation
```
