---
name: "Chapter E5 — Eval harness and model choice"
overview: "A small hand-labelled gold set and an eval command that measure precision, recall, grounded rate, tag agreement and neurons per page for a model and prompt version, so the model, the prompt and the thresholds are decisions with numbers."
todos:
  - id: gold
    content: "Gold set of about twenty labelled rendered pages"
    status: pending
  - id: harness
    content: "llm eval command and metrics"
    status: pending
  - id: decision
    content: "Run candidate models, record the chosen model, prompt version and thresholds"
    status: pending
isProject: false
---

# Chapter E5 — Eval harness and model choice

**Repo:** `redtape` (`apps/discovery-ingest`) · **Branch:** `feat/extraction-eval` · **Status:** planned

**Depends on:** [E2](02-page-cleaner.md), [E3](03-extraction-schema-and-grounding.md), [E4](04-workers-ai-client-and-probe.md), and crawlers [15](../../crawlers/chapters/15-cloudflare-render-and-snapshot.md)'s live gate (real snapshots) · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/extraction`

## Goal

Nothing after this chapter is built against an unmeasured model (decision X12). The free allowance cannot afford trial and error at scale, so a small labelled set and a repeatable command decide which model, mode and prompt version go to production, and what quality we expect.

## Contract

**Gold set.** `apps/discovery-ingest/tests/fixtures/gold/`: about twenty rendered snapshots (from the crawlers fixture-capture workflow; at least five hosts, including one accordion-style page, one list page, one with no documents, one login wall and one with conditional requirements), each with `<name>.html` and `<name>.gold.json`:

```text
{"page_kind": "service", "documents": [{"name": "Personalausweis", "role": "required"}, ...],
 "dependencies": [{"parent": "...", "requires": "..."}],
 "domain_codes": ["housing"], "situation_codes": ["moving-house"]}
```

Names are labelled by a human reading the page, with the same verbatim, atomic-name rule as the prompt. Personal data is removed and size trimmed. The set is committed; it is small enough to review in one sitting.

**Matching.** Predicted and gold names match by `candidate_key`-equivalent slug (the promotion rule), then role. Precision is correct predicted mentions over predicted; recall is correct predicted over gold; edges are scored the same way on `(parent slug, required slug)`; **grounded rate** is the share of raw model items that survive grounding (a measure of invention); **tag agreement** is the Jaccard overlap of predicted and gold codes averaged over pages (empty versus empty counts as agreement); **neurons per page** is the meter's cost, and tokens in and out are reported alongside.

**Command.** `python -m discovery_ingest llm eval --model <id> [--prompt-version <v>] [--limit N] [--out <file>]` runs the gold set through the cleaner, the client and grounding, reserving from the ledger like a real run (so it cannot overspend the day), and prints a table plus a JSON file with per-page results and every dropped item with its reason. `--limit` and the neuron budget keep one run to a fraction of the day. Results are cached by `(model, prompt version, clean version, page)` in a local directory so a re-run of an unchanged page costs nothing.

**Decision record.** The chapter ends with a decision entry in [../gaps-and-decisions.md](../gaps-and-decisions.md) (X14): the chosen model and endpoint mode (from the probe), `PROMPT_VERSION`, the cleaner version, the measured precision, recall, grounded rate, tag agreement and neurons per page, and the **thresholds** the later live gates use. Starting targets, to be replaced by what the measurements justify: precision at least 0.80, recall at least 0.60, grounded rate at least 0.95, tag agreement at least 0.60 (tags reach the emit payload only if it passes), and an expected pages-per-day figure derived from neurons per page. If no candidate model reaches the targets, record the shortfall and the decision (accept lower recall because everything is human-reviewed, change the cleaner or prompt, or fall back to hand-written extractors for the weak hosts, crawlers chapter 18).

**Cleaner swap check.** If recall misses on pages whose expected names are absent from the cleaned text, that is a cleaner failure, reported separately (`cleaner_recall`); the Trafilatura swap of [E2](02-page-cleaner.md) is decided here, with the same gold set.

## TDD loops

The harness is tested with a fake client and a tiny gold set built in the test.

### Loop A — Metrics

**Red** (`apps/discovery-ingest/tests/test_llm_eval_metrics.py`)

1. `precision and recall count matching slug and role and ignore order`.
2. `edge scoring uses parent and required slugs`.
3. `grounded rate is surviving items over raw items`.
4. `tag agreement is the mean Jaccard and treats empty against empty as agreement`.
5. `a page with no gold documents and no predictions scores as correct, not as a division by zero` — negative edge case.

**Green:** one function per metric. **Refactor:** pure functions on plain data.

### Loop B — Command

**Red** (`test_llm_eval_command.py`)

1. `eval runs every gold page through clean, client and grounding and prints a table`.
2. `eval reserves from the ledger and stops with a clear message when the budget is spent`.
3. `a cached page is not sent again for the same model, prompt and cleaner version`.
4. `the output file lists dropped items with their reasons`.
5. `eval never prints the token`.

**Green:** a command over the existing pieces. **Refactor:** the cache is a small separate class.

## Verification

```bash
cd apps/discovery-ingest && python -m pytest tests/test_llm_eval_metrics.py tests/test_llm_eval_command.py && ruff check . && mypy discovery_ingest
gh pr checks --watch
```

Live gate (spends neurons; plan it over two days):

```bash
python -m discovery_ingest llm eval --model <candidate-1> --neuron-budget 4000 --out /tmp/eval-1.json
python -m discovery_ingest llm eval --model <candidate-2> --neuron-budget 4000 --out /tmp/eval-2.json
```

Paste the tables into the ledger, write decision X14, and set `llm_model` and `PROMPT_VERSION` in a follow-up commit. Record the neurons used per run.

## Out of scope

Fine-tuning, automated prompt search, self-consistency or multi-sample voting, a large benchmark, a human review UI (review is a person reading the output file).
