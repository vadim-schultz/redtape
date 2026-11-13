---
name: "Chapter 5 — LLM readiness"
overview: "Make neuron spend thread-safe, run the LLM stage with concurrency so it is no longer clock-bound, and requeue the extractions made under a stale prompt version."
todos:
  - id: meter-lock
    content: "Serialise reserve and settle in NeuronMeter"
    status: pending
  - id: concurrency
    content: "Honour a concurrency option for llm_extract batches, default 3"
    status: pending
  - id: stale-requeue
    content: "Requeue llm_extract tasks whose prompt version is not the current one"
    status: pending
isProject: false
---

# Chapter 5 — LLM readiness

**Repo:** `redtape` · **Branch:** `feat/pipeline-optimisation-llm-readiness` · **Status:** planned
**Depends on:** [2](02-observability-run-hygiene.md) (run stages) · **Architecture:** [../00-architecture.md](../00-architecture.md) (section 2.4, waste 9) · **Decisions:** D2

**Loop branch:** `feat/plans-pipeline-optimisation` · **Release branch:** `main`

## Goal

The last real LLM run completed 32 of 32 tasks and then stopped on the queue, but a busy run stops on the clock at about 45 tasks in 600 s, because the batch settle is sequential. Make the LLM stage concurrent and safe, and requeue the extractions made under prompt `ext-5`, which the taxonomy cutover made stale. The schedule itself is re-enabled by operator step S2, not by this chapter.

## Design

- **Thread-safe meter.** `NeuronMeter` (`apps/discovery-ingest/discovery_ingest/extract/llm/meter.py`, reserve at about line 102 and settle at about line 116) serialises reserve and settle with one lock per meter. Only the in-process reservation is locked; the API stays the source of truth, and the lock is held only around the local budget read and the API call.
- **Concurrency option.** `DrainOptions` (`worker/...` and `operations/drain.py`) gains `concurrency: int = 1`. `DrainPolicy.concurrency` already exists and is honoured only by translate (`translate_batch.py:37`), so the batch runner (`worker/batch.py:53-60`) takes a pool of that size for LLM kinds. CLI flag `--concurrency` on `worker drain`. The `discovery-llm.yml` default becomes 3.
- **Ordering.** A concurrent batch still releases unstarted tasks on a stop, and `StopDrain` still ends the drain after the in-flight calls finish.
- **Stale requeue.** `llm requeue` (`operations/requeue.py:51-63`) gains `--stale-only`: it selects completed `llm_extract` tasks whose `input_key` carries a prompt version other than the current `PROMPT_VERSION` (`extract/llm/prompt.py`), and re-pends them.
- **Schedule.** Not touched here. Operator step S2 turns it on after the verification query.

## Files

**Edit**

- `apps/discovery-ingest/discovery_ingest/extract/llm/meter.py`
- `apps/discovery-ingest/discovery_ingest/worker/batch.py`
- `apps/discovery-ingest/discovery_ingest/operations/drain.py`
- `apps/discovery-ingest/discovery_ingest/operations/requeue.py`
- `apps/discovery-ingest/discovery_ingest/cli/worker/commands.py` (the `--concurrency` flag)
- `apps/discovery-ingest/discovery_ingest/cli/llm/commands.py` (the `--stale-only` flag)
- `.github/workflows/discovery-llm.yml` (the default concurrency input)

**Do not edit**

- `DISCOVERY_LLM_SCHEDULE`. Operator-only.

## Red tests

| Test | Asserts |
| --- | --- |
| `concurrent reservations never exceed the cap` | Negative: 20 threads reserve against a cap of 100 with 10 each; the total reserved is at most 100. |
| `an llm drain with concurrency 3 settles every task it claimed` | Happy: all completed; the report counts add up. |
| `a stop mid-batch releases the unstarted tasks and no others` | Negative: unstarted tasks are released, in-flight tasks settle. |
| `stale-only requeue selects only old prompt versions` | Happy: `ext-5` rows are selected; `ext-6` rows are not. |
| `the concurrency option is rejected below 1 and above 8` | Negative: 0 and 9 fail at settings load. |

## Green

1. Write the meter contention test first, then add the lock.
2. Add `concurrency` to `DrainOptions` and the policy, then the batch pool, then the CLI flag.
3. Add `--stale-only` and its selection query.
4. Change the workflow default to 3.

## Refactor gate

`batch.py` keeps one function per concern: claim, run, settle. The pool is one helper. The lock is a single attribute on the meter, not a second class.

## Verification

```bash
cd apps/discovery-ingest && .venv/bin/python -m pytest -q tests/ -k "meter or batch or llm" && cd ../..
./ci.sh
```

Live gate: after the merge, dispatch `discovery-llm.yml` once with `max_batches=1` and `concurrency=3`, then record the report in the run ledger. The gate fails if any claimed task is neither completed nor released.

## Commits

`test(ingest): define concurrent neuron reservations`, `fix(ingest): serialise neuron reservations within a drain`, `feat(ingest): run llm batches with a concurrency option`, `feat(ingest): requeue llm extractions made under a stale prompt`.

## Out of scope

Turning the schedule on (S2), the rolling neuron ledger (chapter 3 decides), and the translation tail (chapter 7).

## Git workflow

```bash
git checkout feat/plans-pipeline-optimisation && git pull
git checkout -b feat/pipeline-optimisation-llm-readiness
```

Open the chapter PR into `feat/plans-pipeline-optimisation`.
