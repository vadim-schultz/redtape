# C5 — Local daemon and observability

**Depends on:** C1, C2, C3, C4 · **Batch:** 3 · **Branch:** `feat/local-queue-drain-daemon`

## Goal

Run the local drains unattended on this machine: a bounded loop that claims in short runs, backs off when the queue is empty, stops on credential or setup errors, and shows its work in the flow page.

## Preconditions

- C1–C4 each passed their gates. The daemon runs only the providers whose gates passed; a provider that failed stays off.
- The local machine key exists (D15). Its name is recorded; its value is in the user's environment, never in the repo.

## Slices (red → green → refactor each)

### Slice 5a — loop

- **Happy:** the daemon runs a bounded drain with the configured kinds, and when the report says `queue_empty` it sleeps for the configured backoff before the next drain. The test uses a fake clock and a fake drain that reports `queue_empty` twice, then work.
- **Negative:** a drain that returns an `error` stop does not end the daemon. It records the error, backs off, and runs again. A setup error (`LlmSetupError` or `BrowserSetupError` with exit code 2, for example missing credentials) ends the daemon with a non-zero exit, so the service manager does not restart it in a loop.

### Slice 5b — run bounds

- **Happy:** a daemon configured with a time budget of 1,800 seconds per run is accepted, and each run's `time_budget_seconds` is at most 1,800.
- **Negative:** a configured time budget at or above 3,600 seconds is refused at startup, with a message naming the stale-run window (I4).

### Slice 5c — observability

- **Happy:** each local run posts its report through `RunsAPI.start` and `finish`, with `stage` set to the stage the run drained. The flow page's last-run figure for the stage moves after the run.
- **Negative:** a run that cannot reach the API before it starts does not claim tasks. It logs the failure and backs off, and no task is left leased (the claim never happened).

### Slice 5d — heartbeats

- **Happy:** after one batch that completes three tasks, the heartbeat file for the type holds `state="idle"`, `completed=3`, and a current `updated_at`.
- **Negative:** the heartbeat directory is read-only. The write fails, the failure is logged, and the drain continues. The drain's report is unchanged.

## Green

- Add `apps/discovery-ingest/discovery_ingest/daemon.py` with the loop, reusing `drain_until_stop` semantics for the bounds. Keep it small: one function per concern (`_next_action`, `_run_once`, `_backoff`).
- Write a heartbeat after every batch and every state change. `WorkerStateStore` writes `<state dir>/redtape-workers/<type>.json` atomically: a temporary file, then a rename. Fields: `worker_type`, `provider`, `host`, `pid`, `state` (`running`, `idle`, `backoff`, `error` or `stopped`), `run_id`, `claimed`, `completed`, `failed`, `last_report`, `last_error`, `started_at`, `updated_at` and `heartbeat_interval_seconds`. C7 reads these files. The store and `process_matches(pid, worker_type)` live in `worker_state.py`. `process_matches` reads `/proc/<pid>/cmdline`, so a reused pid is never taken for a worker. C6 and C7 import both.
- Add `worker_types.py`: one table that lists each worker type with its kinds, its provider and its resource limits. The provider switches of C1–C4 map onto it. C6 and C7 import it, and they do not repeat it.
- Expose it as `discovery_ingest daemon run --type <worker type>`. The type selects the kinds, the provider and the limits from `worker_types.py`.
- Each claim takes one task (`limit=1`, D11), and the daemon sets `screenshot_sweep_limit=None` (D10).
- The daemon writes its log to stderr. The fleet redirects that stream into the type's log file (C6).

## Refactor

- The provider switches of C1–C4 map onto worker types in one table, `worker_types.py`. The daemon reads only that table, and it does not repeat the switches.
- `daemon.py` must stay small. If it passes about 100 lines, split the backoff policy into its own module.
- Check the operator docs written in C0 for the new daemon. Describe the local runs next to the GHA runs, so the two are not confused in the flow.

## Verification

```bash
cd apps/discovery-ingest && .venv/bin/python -m pytest tests -k "daemon" -q
cd apps/discovery-ingest && .venv/bin/python -m ruff check discovery_ingest && .venv/bin/python -m mypy discovery_ingest
cd apps/api && ./ci.sh
```

Then the eight-hour unattended run, recorded in the ledger: the run count, the longest run, every stop reason, and the flow page state before and after.

## Exit

- The eight-hour run passes: no run older than the stale window, no unhandled error, backoff while the queue is empty.
- The flow page shows the local runs. The Cloudflare and Azure figures do not move because of local work.
- The daemon's start, stop and check steps are in the runbook (C9).
