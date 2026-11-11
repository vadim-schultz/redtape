---
name: "Chapter 19 — Claude Code translation engine (tr and uk)"
overview: "Translate the German card unit into tr and uk with the Claude Code CLI on the user's Claude Code allowance, through the existing engine port, validators, machine API and R2 path, instead of Cloudflare neurons."
id: C19
depends_on:
  - C13
  - C14
  - C15
touches:
  - apps/discovery-ingest/discovery_ingest/translation/
  - apps/discovery-ingest/discovery_ingest/ (CLI wiring for the engine option)
  - apps/discovery-ingest/tests/
  - apps/api/app/features/translation/ (only if the complete route checks engine names)
  - docs/operations/ (translation engine notes, where they exist)
  - .plans/search-first/
execution: chapter-implementer
---

# Chapter 19 — Claude Code translation engine (tr and uk)

**Repo:** `redtape` (`apps/discovery-ingest`; `apps/api` only if the engine name is checked there)
**Depends on:** [Chapter 13](13-translation-schema-and-core.md), [Chapter 14](14-translation-queue-and-machine-api.md), [Chapter 15](15-translation-drain-worker.md) · **Decisions:** [../gaps-and-decisions.md](../gaps-and-decisions.md) (D13, D15, D16) · **Rules:** [../../../CLAUDE.md](../../../CLAUDE.md) (package registries)

## Goal

Translate the German card unit (title and description) into `tr` and `uk` with the Claude Code CLI, paid for from the user's Claude Code allowance, not from Cloudflare neurons. The Cloudflare daily allowance is exhausted. The product owner decided on 2026-11-11 to start with these two locales on Claude Code. Everything else in the translation track (queue, validators, R2 objects, index rows, read path) stays as built.

## Scope

- Locales: `tr` and `uk` only. `en`, `ru`, `pl` and `ro` are not claimed in this run.
- Unit: `card` (title and description), as in chapter 13.
- Output: stored through the machine API `complete` route as today, with `source = mt`, `engine = claude-code` and `model` = the model id.
- Out of scope: enabling locales, native review, human translations, changes to the Cloudflare adapter, scheduling on GitHub Actions, full-document translation.

## Design

1. **Adapter.** A new engine `claude-code` in the translation engine registry, next to `llm`. `TRANSLATION_ENGINE=claude-code` selects it. It implements the existing port. It reuses `llm`'s prompt, glossary, answer schema and validators; only the transport differs.
2. **Transport.** One CLI call per batch: `claude --print --output-format json --json-schema <answer schema> --model <model> --tools "" --no-session-persistence`, with the prompt on stdin. `--tools ""` disables every tool, so the German source text is data and cannot make the model act. The model defaults to `claude-sonnet-5-5` and is set by `CLAUDE_TRANSLATE_MODEL`.
3. **Auth.** Remove `ANTHROPIC_API_KEY` from the subprocess environment, so the CLI uses the Claude Code login and not API billing. The drain report records which auth mode ran.
4. **Usage and metering.** The engine declares a new usage unit (`subscription`), counted in calls and tokens from the CLI's JSON output. It is not neuron-metered: the query-embedding floor (D15) does not apply and the neuron ledger is not written. The drain report shows calls, tokens and rejections.
5. **Batching and concurrency.** Up to 20 units per call. Bounded concurrency: default 2, at most 4 CLI calls at once. Each batch is its own lease from the queue, so the existing claim semantics hold. The drain stops on its existing time budget, batch limit and quota stop.
6. **Errors.** Usage-limit or rate-limit output maps to a quota stop, releasing the batch without consuming attempts, as the Cloudflare quota stop does. A timeout or non-zero exit is transient. "Not logged in" is unauthorised. Invalid JSON or failed validators get one repair call, then are rejected, as today.
7. **API.** If the machine `complete` route whitelists engine names, add `claude-code` and regenerate the machine contract fixture, as chapter 14 did. Otherwise there is no API change.
8. **Process isolation.** The subprocess runner sits behind a small callable port, so tests inject a fake runner and never spawn `claude`.

## Red tests (write first; confirm each fails for the intended reason)

Happy path:
- `claude-code` passes the shared engine conformance suite (`translation_engine_contract.py`) with an injected fake runner.
- The command built has `--tools ""`, the answer JSON schema, the configured model, and no `ANTHROPIC_API_KEY` in the environment.
- A drain with `TRANSLATION_ENGINE=claude-code` and locales `tr uk` claims only those locales and reports zero neurons and no ledger writes.

Negative path:
- Rate-limit output maps to a quota stop; the batch is released with `attempt_count` unchanged.
- A timeout maps to transient. A non-zero exit with "not logged in" maps to unauthorised.
- Invalid JSON is repaired once. A second invalid answer is rejected, not stored.

## Green

The smallest change for each red test. Reuse the `llm` prompt, glossary, schema and validators.

## Refactor gate

House rules: about 5 lines per function, about 100 lines per file, at most 3 parameters, no boolean flags, no `Any`, docstrings in discovery-ingest. The subprocess code and its error mapping live in separate modules.

## Verification

```bash
cd apps/discovery-ingest
uv run pytest tests/ -k claude_code     # or the new test paths
uv run ruff format --check . && uv run ruff check . && uv run mypy discovery_ingest
```

Run local CI as the repo rules say (see [CLAUDE.md](../../../CLAUDE.md) for the registry fallback). If the API changes, also run its contract tests against a scratch database.

**Live smoke (manual, recorded):** one batch of two real German units through the real CLI. Print the output and record the tokens. Write nothing. This is the only live model call the chapter may make.

## Operator steps after merge (chief of staff)

1. Set `TRANSLATION_TARGET_LOCALES=tr uk` on Render (the machine API scopes claims by it).
2. After backfill A has finished: run `scripts.backfill_translations` with `TRANSLATION_TARGET_LOCALES="tr uk"`. It enqueues about 9,400 units.
3. Run the local drain with `TRANSLATION_ENGINE=claude-code` and the machine API URL and key from the local config, in batches, until the queue is empty or the subscription quota stops it.
4. Record the drain reports, the validator repair rate and translated / total per locale in the run ledger.

## Git workflow

```bash
# 0. sync the loop branch with main (13 commits behind on 2026-11-11)
git checkout feat/plans-search-first && git pull
git checkout -b chore/sync-loop-with-main && git merge --no-ff origin/main
git push -u origin HEAD          # PR into feat/plans-search-first; merge commit, not squash
# 1. the chapter
git checkout feat/plans-search-first && git pull
git checkout -b feat/translation-claude-code
```

Commit messages: `test(ingest): ...`, `feat(ingest): add claude-code translation engine`, `docs(ingest): ...`. End commit messages and the PR body with the attribution lines the session gives.
