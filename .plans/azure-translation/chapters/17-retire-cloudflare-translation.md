---
name: "Chapter 17 — Retire the Cloudflare translation adapter and the claude-code engine (deferred)"
overview: "Remove the Cloudflare Workers AI translation adapter, the claude-code engine and the translation-only neuron wiring, after about a month of Azure operation with no rollback. Extraction, embedding, query embedding and the port's limits stay. Not in the execution order: it starts only on an operator go-ahead."
id: AZ17
depends_on:
  - AZ16
touches:
  - apps/discovery-ingest/discovery_ingest/translation/adapters/cloudflare_llm.py
  - apps/discovery-ingest/discovery_ingest/translation/adapters/cloudflare_prompt.py
  - apps/discovery-ingest/discovery_ingest/translation/adapters/cloudflare_answer.py
  - apps/discovery-ingest/discovery_ingest/translation/adapters/claude_code.py
  - apps/discovery-ingest/discovery_ingest/translation/adapters/claude_code_cli.py
  - apps/discovery-ingest/discovery_ingest/translation/adapters/claude_code_errors.py
  - apps/discovery-ingest/discovery_ingest/translation/adapters/claude_code_output.py
  - apps/discovery-ingest/discovery_ingest/translation/claude_code_settings.py
  - apps/discovery-ingest/discovery_ingest/translation/subscription_meter.py
  - apps/discovery-ingest/discovery_ingest/translation/adapters/__init__.py
  - apps/discovery-ingest/discovery_ingest/translation/settings.py
  - apps/discovery-ingest/discovery_ingest/translation/units.py
  - apps/discovery-ingest/discovery_ingest/translation/meter.py
  - apps/discovery-ingest/discovery_ingest/operations/translate_drain.py
  - apps/discovery-ingest/tests/translation_harnesses.py
  - apps/discovery-ingest/tests/claude_code_fakes.py
  - .github/workflows/discovery-translate.yml
  - docs/operations/translation-engines.md
execution: operator go-ahead, then chapter-implementer
---

# Chapter 17 — Retire the Cloudflare translation adapter and the claude-code engine (deferred)

**Repo:** `redtape` (`apps/discovery-ingest`, `.github/workflows`, docs) · **Depends on:** [Chapter 16](16-cutover-runbook.md) and about one month of Azure operation · **Decisions:** [D9](../gaps-and-decisions.md#d9--the-claude-engine-is-on-main-cloudflare-translation-is-retired-later) · **Rules:** [../../../CLAUDE.md](../../../CLAUDE.md) (package registries) · **Status:** deferred

## Goal

Remove the two translation engines that Azure replaces, once Azure has run for about a month with no rollback, so that one translation engine is left to maintain. Extraction, embedding and query embedding are not touched.

## Scope

- In: the `llm` translation adapter with its prompt and answer modules; the `claude-code` engine with its CLI, errors, output, settings and fakes; the `subscription` usage unit and its own-meter entry; the harness entries; the Cloudflare translation secrets in the translate workflow; translation-only neuron wiring.
- Out: `CallLimits`, `TranslationEngine.limits`, `TranslationOutcome.auth` and the concurrency window, because Azure uses them or the drain keeps them; the Cloudflare extraction and embedding clients; `QUERY_EMBED_RESERVE` and the query-embedding floor; `LLM_MODEL` while extraction reads it.

## Precondition

The operator records all three in the run ledger before this chapter starts:

- No rollback to `TRANSLATION_ENGINE=llm` has been needed for about 30 days.
- The coverage page shows the card and snapshot backlog is on track.
- The operator gives a go-ahead for this chapter.

## Design

1. **Confirm before deleting.** Grep the ingest package and the tests for each name, and remove only what has no other user. `cloudflare_prompt` and `cloudflare_answer` are imported by `cloudflare_llm` alone, as checked on `main`. The neuron wiring in `translation/meter.py` goes only if nothing else calls it.
2. **Delete the Cloudflare translation adapter.** `cloudflare_llm.py`, its prompt and answer modules, its registration in `adapters/__init__.py`, its harness entry, and the translation model setting.
3. **Delete the claude-code engine.** `adapters/claude_code.py`, `claude_code_cli.py`, `claude_code_errors.py`, `claude_code_output.py`, `translation/claude_code_settings.py`, `translation/subscription_meter.py`; their registration; the `"subscription"` literal in `UsageUnit`; the `own_meters={"subscription": …}` entry in `operations/translate_drain.py`; and the fakes and tests that exercise them.
4. **Keep the port.** `limits` and `CallLimits` stay on the protocol, because Azure implements them. `TranslationOutcome.auth` and the concurrency window with `--concurrency` stay as well, because the drain uses them.
5. **Keep the rest.** The Cloudflare extraction and embedding clients, `QUERY_EMBED_RESERVE` and the query-embedding floor, and `LLM_MODEL` while extraction reads it.
6. **Engine names.** `TRANSLATION_ENGINE=llm` and `TRANSLATION_ENGINE=claude-code` now fail at load, with a message that names the supported engine.
7. **Workflow.** The Cloudflare translation secrets leave the translate workflow. The claude-code engine was never in it, so nothing else changes there.
8. **Docs.** `translation-engines.md` removes the rollback path and records the removal date.

## Files

| Path | Change |
| --- | --- |
| `translation/adapters/cloudflare_llm.py`, `cloudflare_prompt.py`, `cloudflare_answer.py` | deleted |
| `translation/adapters/claude_code.py`, `claude_code_cli.py`, `claude_code_errors.py`, `claude_code_output.py` | deleted |
| `translation/claude_code_settings.py`, `translation/subscription_meter.py` | deleted |
| `translation/adapters/__init__.py` | both registrations removed |
| `translation/settings.py` | translation model setting removed |
| `translation/units.py` | `subscription` removed from `UsageUnit` |
| `translation/meter.py` | translation-only neuron wiring removed, if unused |
| `operations/translate_drain.py` | `own_meters` subscription entry removed |
| `tests/translation_harnesses.py`, `tests/claude_code_fakes.py`, `tests/test_translate_claude_code*.py`, `tests/test_translation_subscription_meter.py` | removed or updated |
| `.github/workflows/discovery-translate.yml` | Cloudflare translation secrets removed |
| `docs/operations/translation-engines.md` | rollback section replaced |

## Red tests

For a deletion chapter, the tests pin the removal and the things that must stay.

**Happy path**
- `Registry · azure-translator is the only translation engine registered`
- `Units · UsageUnit has no subscription literal; characters and neurons remain`
- `Workflow · the translate workflow references no Cloudflare translation secret`
- `Contract · the shared conformance suite runs for azure-translator only`

**Negative path**
- `Settings · TRANSLATION_ENGINE=llm and TRANSLATION_ENGINE=claude-code fail at load, naming the supported engine`
- `Regression · the extraction and embedding Cloudflare clients still pass their existing tests unchanged`
- `Regression · query embedding and its neuron floor still pass their existing tests unchanged`
- `Regression · the port's limits and the concurrency window still drive the Azure drain`

## Green

Delete the modules, then fix the imports and the settings until the regression tests pass without edits to them.

## Refactor gate

- No commented-out code, no dead settings, no unused fixtures.
- Any helper left with one caller after the deletion is inlined.
- House rules apply to the modules that remain.

## Verification

```bash
cd apps/discovery-ingest
grep -rn "cloudflare_llm\|cloudflare_prompt\|cloudflare_answer\|claude_code\|subscription_meter\|TRANSLATION_MODEL\|\"subscription\"" discovery_ingest tests || echo "no references"
.venv/bin/python -m pytest -q tests/test_translation_registry.py tests/test_translate_workflow.py tests/test_azure_*.py tests/test_embed_*.py tests/test_llm_*.py
.venv/bin/ruff format --check . && .venv/bin/ruff check . && .venv/bin/mypy discovery_ingest
cd ../.. && ./ci.sh
```

## Out of scope

Extraction and embedding changes, removing `limits` or the concurrency window, Render or GitHub settings (the operator removes unused variables), the rollback procedure's history.

## Operator steps after merge

Remove the now-unused Cloudflare translation secrets from the GitHub environment, after confirming extraction and embedding still use their own credentials. Confirm that no host still needs the `claude` CLI or a Claude Code login for translation.

## Git workflow

```bash
git checkout feat/plans-azure-translation && git pull
git checkout -b feat/azure-17-retire-translation-engines
# refactor(ingest): ... (one commit per removed module), docs(ops): runbook
git push -u origin HEAD
# PR into feat/plans-azure-translation, only after the operator go-ahead
```
