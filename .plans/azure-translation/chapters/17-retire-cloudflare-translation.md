---
name: "Chapter 17 — Retire the Cloudflare translation adapter (deferred)"
overview: "Remove the Cloudflare Workers AI translation adapter and the translation-only neuron wiring, after about a month of Azure operation with no rollback. Extraction, embedding and query embedding keep their Cloudflare code. Not in the execution order: it starts only on an operator go-ahead."
id: AZ17
depends_on:
  - AZ16
touches:
  - apps/discovery-ingest/discovery_ingest/translation/adapters/cloudflare_llm.py
  - apps/discovery-ingest/discovery_ingest/translation/adapters/cloudflare_prompt.py
  - apps/discovery-ingest/discovery_ingest/translation/adapters/cloudflare_answer.py
  - apps/discovery-ingest/discovery_ingest/translation/adapters/__init__.py
  - apps/discovery-ingest/discovery_ingest/translation/settings.py
  - apps/discovery-ingest/discovery_ingest/translation/meter.py
  - apps/discovery-ingest/tests/translation_harnesses.py
  - .github/workflows/discovery-translate.yml
  - docs/operations/translation-engines.md
execution: operator go-ahead, then chapter-implementer
---

# Chapter 17 — Retire the Cloudflare translation adapter (deferred)

**Repo:** `redtape` (`apps/discovery-ingest`, `.github/workflows`, docs) · **Depends on:** [Chapter 16](16-cutover-runbook.md) and about one month of Azure operation · **Decisions:** [D9](../gaps-and-decisions.md#d9--independent-of-the-claude-engine-the-cloudflare-translation-role-is-retired-later) · **Rules:** [../../../CLAUDE.md](../../../CLAUDE.md) (package registries) · **Status:** deferred

## Goal

Remove the translation-only Cloudflare code once Azure has run for about a month with no rollback, so only one translation engine is left to maintain. This is a deletion chapter, and it changes nothing that extraction, embedding or query embedding use.

## Scope

- In: the `llm` translation adapter and its prompt and answer modules, its harness entry, its settings, its workflow secrets, and the neuron wiring used only by translation.
- Out: the Cloudflare extraction and embedding clients, `QUERY_EMBED_RESERVE`, the neuron ledger for query embedding, `LLM_MODEL` if extraction still reads it.

## Precondition

The operator records all three in the run ledger before this chapter starts:

- No rollback to `TRANSLATION_ENGINE=llm` has been needed for about 30 days.
- The coverage page shows the card and snapshot backlog is on track.
- The operator gives a go-ahead for this chapter.

## Design

1. **Confirm before deleting.** Grep the ingest package and the tests for each name to be removed, and remove only what has no other user. `cloudflare_prompt` and `cloudflare_answer` are imported by `cloudflare_llm` alone, as checked on `main`. The translation-only neuron wiring in `translation/meter.py` is removed only if nothing else calls it.
2. **Delete.** The `llm` translation adapter, its prompt and answer modules, its registration in `adapters/__init__.py`, its harness entry, and the translation settings (`TRANSLATION_MODEL`, the `llm` default).
3. **Keep.** The Cloudflare extraction and embedding clients, `QUERY_EMBED_RESERVE` and the query-embedding floor, and `LLM_MODEL` while extraction reads it.
4. **Engine name.** `TRANSLATION_ENGINE=llm` now fails at load with a message that names the supported engine.
5. **Workflow.** The Cloudflare translation secrets are removed from the translate workflow. The embed and extraction workflows are not touched.
6. **Docs.** `translation-engines.md` removes the rollback path and records the removal date.

## Files

| Path | Change |
| --- | --- |
| `translation/adapters/cloudflare_llm.py`, `cloudflare_prompt.py`, `cloudflare_answer.py` | deleted |
| `translation/adapters/__init__.py` | import removed |
| `translation/settings.py` | translation model and `llm` default removed |
| `translation/meter.py` | translation-only neuron wiring removed, if unused |
| `tests/translation_harnesses.py` | `llm` entry removed |
| `.github/workflows/discovery-translate.yml` | Cloudflare translation secrets removed |
| `docs/operations/translation-engines.md` | rollback section replaced |

## Red tests

For a deletion chapter the tests pin the removal and the things that must stay.

**Happy path**
- `Registry · the azure-translator engine is the only translation engine registered`
- `Workflow · the translate workflow references no Cloudflare translation secret`
- `Contract · the shared conformance suite runs for azure-translator only`

**Negative path**
- `Settings · TRANSLATION_ENGINE=llm fails at load with a message that names the supported engine`
- `Regression · the extraction and embedding Cloudflare clients still pass their existing tests unchanged`
- `Regression · query embedding and its neuron floor still pass their existing tests unchanged`

## Green

Delete the modules, then fix the imports and the settings until the regression tests pass without edits to them.

## Refactor gate

- No commented-out code, no dead settings, no unused fixtures.
- Any helper that is left with one caller after the deletion is inlined.
- House rules apply to the modules that remain.

## Verification

```bash
cd apps/discovery-ingest
grep -rn "cloudflare_llm\|cloudflare_prompt\|cloudflare_answer\|TRANSLATION_MODEL" discovery_ingest tests || echo "no references"
.venv/bin/python -m pytest -q tests/test_translation_registry.py tests/test_translate_workflow.py tests/test_embed_*.py tests/test_llm_*.py
.venv/bin/ruff format --check . && .venv/bin/ruff check . && .venv/bin/mypy discovery_ingest
cd ../.. && ./ci.sh
```

## Out of scope

Extraction and embedding changes, Render or GitHub settings (the operator removes unused variables), the rollback procedure's history.

## Operator steps after merge

Remove the now-unused Cloudflare translation secrets from the GitHub environment, after confirming extraction and embedding still use their own credentials.

## Git workflow

```bash
git checkout feat/plans-azure-translation && git pull
git checkout -b feat/azure-17-retire-cloudflare-translation
# refactor(ingest): ... (deletion, one commit per removed module), docs(ops): runbook
git push -u origin HEAD
# PR into feat/plans-azure-translation, only after the operator go-ahead
```
