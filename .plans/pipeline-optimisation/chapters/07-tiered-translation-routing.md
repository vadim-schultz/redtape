---
name: "Chapter 7 — Tiered translation routing"
overview: "Route the lower-priority card translations to Workers AI, validated per locale, and let an Azure translation later supersede a tail row, without ever overwriting a human translation."
todos:
  - id: priority-range
    content: "Claim translation tasks within a priority range, and let each drain choose its engine"
    status: pending
  - id: upgrade
    content: "Enqueue an upgrade for each tail row once Azure capacity frees up"
    status: pending
  - id: locale-gate
    content: "Enable a tail locale only after its probe passes, with an empty default"
    status: pending
isProject: false
---

# Chapter 7 — Tiered translation routing

**Repo:** `redtape` · **Branch:** `feat/pipeline-optimisation-tiered-translation` · **Status:** planned
**Depends on:** [3](03-neuron-reconciliation-spike.md), [6](06-azure-economy.md) · **Architecture:** [../00-architecture.md](../00-architecture.md) (section 3, item 4) · **Decisions:** D3, D14

**Loop branch:** `feat/plans-pipeline-optimisation` · **Release branch:** `main`

## Goal

Azure's free tier covers about 317 card-locales a month, and the backlog is about 25,000. Workers AI covers the rest, at about 10 to 13 neurons a card-locale, from neurons that are otherwise idle. Route only the lower-priority tier to Workers AI, and only into locales that pass a probe. The higher-priority tier stays on Azure, and a tail row can be superseded later.

## Design

- **Priority tiers.** `priority.py` gives first translations a priority of `1000 − round(confidence × 1000)`, so 0 to 1000, and re-translations 10,000 and above. A tier boundary is a setting, `TRANSLATION_TAIL_PRIORITY_MIN`, defaulting to 600.
- **Claim by range.** The claim (`queue.py`) accepts `priority_min` and `priority_max`. `translate drain` gains `--engine`, `--priority-min` and `--priority-max`. A drain claims only the rows its engine is allowed to take.
- **Tail locales.** `TRANSLATION_TAIL_LOCALES` is empty by default (D14). A tail locale is one that has passed the existing `translate probe` with at least 90% valid units. Nothing is routed to Workers AI until the operator sets the variable.
- **Upgrade.** When the Azure band has spare capacity, the upgrade enqueue creates a task for each tail row (`engine = llm`) at a higher base priority (`UPGRADE_BASE`, about 20,000), so the Azure drain takes it. `CandidateTranslation` already records `engine` and `model` (`models/translation.py`), so the row is found by its engine.
- **Protected rows.** The completion check never overwrites a row whose origin is human (`_human` in the store), and a tail row is replaced only when the Azure translation has a newer source hash.
- **Pages stay on Azure.** Snapshot translation (`snapshot_drain.py`) never uses the tail engine.

## Files

**Edit**

- `apps/api/app/features/translation/priority.py`
- `apps/api/app/features/translation/queue.py`
- `apps/api/app/features/translation/enqueue.py`
- `apps/api/app/features/translation/store.py`
- `apps/api/app/schema/translation/machine.py` (the claim body)
- `apps/discovery-ingest/discovery_ingest/cli/translate/commands.py`
- `apps/discovery-ingest/discovery_ingest/operations/translate_drain.py`
- `apps/api/app/config.py` (`TRANSLATION_TAIL_LOCALES`, `TRANSLATION_TAIL_PRIORITY_MIN`)

**Do not edit**

- The character ledger or the glossary modes.

## Red tests

| Test | Asserts |
| --- | --- |
| `a claim within a priority range returns only tasks inside it` | Happy and negative: a task outside the range is not returned. |
| `an llm drain claims only tail-locale rows` | Negative: a row for a locale not in `TRANSLATION_TAIL_LOCALES` is never claimed by `llm`. |
| `with an empty tail list no row is routed to llm` | Negative: the default config routes nothing to Workers AI. |
| `an azure upgrade supersedes an llm row with the same source hash` | Happy: the row's engine becomes `azure-translator`. |
| `an azure upgrade never overwrites a human row` | Negative: a row with a human origin is unchanged. |
| `tier boundaries: 599 is Azure, 600 is the tail` | Boundary: both sides of the default. |

## Green

1. Write the claim-range test first, then add the range to the query.
2. Add the drain flags, then the empty-default tail config.
3. Write the human-row negative test before the upgrade.

## Refactor gate

The claim takes one range object, not two loose integers. The upgrade enqueue is one function with one query. The engine choice is a lookup table, not a branch per engine.

## Verification

```bash
cd apps/api && PYTHONPATH=. .venv/bin/python -m pytest -q tests/ -k "translation" && cd ../..
cd apps/discovery-ingest && .venv/bin/python -m pytest -q tests/ -k "translate" && cd ../..
./ci.sh
```

Live gate: for each candidate tail locale, run `translate probe --engine llm` on the reviewed sample and record the valid share in the run ledger. Set `TRANSLATION_TAIL_LOCALES` only for locales at 90% or more.

## Commits

`test(api): define priority-range claims for translation tasks`, `feat(api): claim translation tasks by priority range`, `feat(ingest): route the translation tail to a chosen engine`, `feat(api): enqueue Azure upgrades for tail translations`, `test(api): protect human translations from upgrades`.

## Out of scope

Page translation on Workers AI, changes to the glossary, and enabling the translate schedule (operator step S4).

## Git workflow

```bash
git checkout feat/plans-pipeline-optimisation && git pull
git checkout -b feat/pipeline-optimisation-tiered-translation
```

Open the chapter PR into `feat/plans-pipeline-optimisation`.
