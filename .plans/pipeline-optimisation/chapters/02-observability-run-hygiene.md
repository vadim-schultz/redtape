---
name: "Chapter 2 — Observability and run hygiene"
overview: "Settle failed browser calls once, record a run for every drain with its stage and spend, close stale runs, close runs on SIGTERM, and expose the per-stage queue stats the flow page needs."
todos:
  - id: settle
    content: "Settle a failed browser call at its measured duration, once"
    status: pending
  - id: runs
    content: "Add stage and spend to discovery_run, and record a run for embed, translate and snapshot drains"
    status: pending
  - id: stale-and-signals
    content: "Sweep stale runs on run start and close open runs on SIGTERM"
    status: pending
  - id: stats
    content: "Add oldest pending age and 24 h completed and failed counts to the machine summaries"
    status: pending
isProject: false
---

# Chapter 2 — Observability and run hygiene

**Repo:** `redtape` · **Branch:** `feat/pipeline-optimisation-observability` · **Status:** planned
**Depends on:** none · **Architecture:** [../00-architecture.md](../00-architecture.md) (section 2.4, waste 5 and 10) · **Gaps:** D6 is not needed here

**Loop branch:** `feat/plans-pipeline-optimisation` · **Release branch:** `main`

## Goal

The flow page (chapters 13 and 14) can show a stage only if every drain leaves a run with its stage, its counts, its stop reason and what it spent. Today only `worker drain` writes a run, a failed browser call is booked at its estimate, and a process killed by SIGTERM leaves its run `running`. Fix those, and add the queue numbers the page needs.

## Design

- **Failed browser calls.** `BrowserSpend.call` (`apps/discovery-ingest/discovery_ingest/worker/browser_spend.py:31-40`) settles in a `finally`: the reserved 30 s is adjusted to the measured wall time, including when the call raised. A call that never reached Cloudflare settles to zero.
- **Run kinds and stages.** `discovery_run` gains `stage` (`String(32)`, nullable, default `worker_drain` for old rows) and `spend` (`JSON`, nullable). `RunFinishRequest` gains `spend: dict[str, float] | None`, validated to the known resources. `RunsAPI.start(kind, stage)` in `apps/discovery-ingest/discovery_ingest/client/runs_api.py` stops hard-coding `worker_drain`.
- **Recorded drains.** `recorded_run` (`worker/run.py`) wraps the embed, translate and snapshot drains as well. Each one passes its stage (`embed`, `translate`, `snapshot_translate`).
- **Stale runs.** `RunsRepository` already has `STALE_RUN_AFTER = 1h` (`repository/runs.py:14`). A run start closes any stale run as `failed` with `error_detail = "stale: no finish received"`. A fresh run is never touched.
- **SIGTERM.** `cli/main.py` installs a SIGTERM handler that raises `KeyboardInterrupt`, so the existing `recorded_run` finaliser runs and closes the run as failed. This is the cause of the three runs stuck in `running` since 2026-10-28.
- **Stats.** The existing `TaskSummary` (`repository/queue_metrics.py`) and the embedding, translation and snapshot summaries gain `oldest_pending_age_seconds`, `completed_24h` and `failed_24h`. Both the machine and the admin read use these.

## Files

**Edit**

- `apps/discovery-ingest/discovery_ingest/worker/browser_spend.py`
- `apps/discovery-ingest/discovery_ingest/worker/run.py`
- `apps/discovery-ingest/discovery_ingest/client/runs_api.py`
- `apps/discovery-ingest/discovery_ingest/cli/main.py`
- `apps/api/app/features/discovery/repository/runs.py`
- `apps/api/app/features/discovery/repository/queue_metrics.py`
- `apps/api/app/features/discovery/machine_controller.py` (run start and finish)
- `apps/api/app/schema/discovery/machine.py` (`RunStartRequest`, `RunFinishRequest`, summary schemas)
- `apps/api/app/models/discovery/discovery_run.py`

**Create**

- one Alembic revision: `discovery_run.stage` and `discovery_run.spend`

**Do not edit**

- `apps/web` in this chapter. Chapter 13 adds the admin route.

## Red tests

| Test | Asserts |
| --- | --- |
| `a failed browser call is settled once, at its measured duration` | Negative: a `BrowserRequestError` adjusts the reservation to the measured ms, not to 30 s, and the adjustment happens once. |
| `a call that never reached Cloudflare settles to zero` | Negative: connection error before send settles to 0 s. |
| `a stale run is closed as failed when a run starts` | Happy: a run older than one hour is closed; the new run is recorded. |
| `a fresh run is left alone when another run starts` | Negative: a run younger than one hour stays `running`. |
| `embed, translate and snapshot drains record a run with their stage` | Happy: one run row per drain, with the matching `stage`. |
| `spend round-trips through RunFinishRequest` | Happy: the spend dict is stored and read back. Negative: an unknown resource name is rejected with 422. |
| `SIGTERM closes the open run as failed` | Happy: the signal raises in the drain, and the run row ends `failed` with `stop_reason` set. |
| `the summary reports oldest pending age and 24 h counts` | Happy: the age is the oldest ready row; a row failed 25 h ago is not counted. |

## Green

1. Settle in `finally` in `BrowserSpend.call`; test the failed call first.
2. Add the migration, the model fields and the schema fields. Update the OpenAPI snapshot in `apps/api/tests` in the same commit.
3. Thread `stage` through `RunsAPI.start` and `recorded_run`. Add the three drains.
4. Add the stale sweep to the run-start service method.
5. Add the SIGTERM handler in `cli/main.py`.
6. Extend the summary query with the three new columns, in one grouped statement.

## Refactor gate

`BrowserSpend.call` must stay under about five lines per method after the `finally` is added; move the settle into a helper. `RunsRepository` gets one method per concern, not a branch per kind. The summary query stays one statement.

## Verification

```bash
cd apps/discovery-ingest && .venv/bin/python -m pytest -q && cd ../..
cd apps/api && PYTHONPATH=. .venv/bin/python -m pytest -q tests/test_discovery_runs*.py tests/test_discovery_queue_summary.py && cd ../..
./ci.sh
```

Live gate: after the merge, dispatch `discovery-screenshot.yml` once and confirm its run row exists with `stage` set. Record the run ID in the run ledger.

## Commits

`test(ingest): define browser settle on failure`, `fix(ingest): settle a failed browser call at its measured duration`, `test(api): define stage and spend on discovery runs`, `feat(api): record the stage and spend of each drain run`, `feat(ingest): record a run for the embed, translate and snapshot drains`, `feat(api): close stale runs when a new run starts`, `feat(ingest): close the run on SIGTERM`, `feat(api): report oldest pending age and 24 h counts`.

## Out of scope

Any change to what the drains claim, any change to the flow page, and any change to the budget resources.

## Git workflow

```bash
git checkout feat/plans-pipeline-optimisation && git pull
git checkout -b feat/pipeline-optimisation-observability
```

Open the chapter PR into `feat/plans-pipeline-optimisation`.
