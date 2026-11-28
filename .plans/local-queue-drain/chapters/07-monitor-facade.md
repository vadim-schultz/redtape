# C7 — Monitor facade (read-only data, no UI)

**Depends on:** C5 · **Batch:** 4 · **Branch:** `feat/local-queue-drain-monitor`

## Goal

`Monitor.snapshot()` returns one `DashboardSnapshot`, built from independent, read-only sources. Each source returns its model or an error value, so a failing source never makes `snapshot()` raise (D22, I12). The module prints nothing and imports no UI library (I10). It is the least intrusive reader we can build: one machine request per queue refresh, no writes, and no request more often than its interval (D26, I14).

## Sources

| Source | Reads | Refresh | Model |
| --- | --- | --- | --- |
| `QueueSource` | one machine `GET /tasks/summary` for the kinds that the local worker types drain (from `worker_types.py`) | 15 s | `QueueRow` per kind |
| `RateTracker` | two successive queue samples | with the queues | completed per minute, and an ETA |
| `HostSource` | psutil (`cpu_percent(percpu=True)`, `virtual_memory`); `nvidia-smi --query-gpu=...` when it is on PATH; llama-server `GET http://127.0.0.1:<port>/health` with a 1 s timeout | 5 s | `HostState` |
| `WorkerStateSource` | the heartbeat files of C5, read through `worker_state.py`, with `process_matches` for each pid; the threads and VRAM of the types whose pid matches (D27) | 5 s | `WorkerRow` per type and `FleetCap` |
| `LogSource` | the last 64 KiB of one selected type's log file | on demand | `LogTail` |

An absent GPU is `gpu=None`, not an error. A heartbeat older than three heartbeat intervals shows state `stale`. The log source reads only the end of the file, never the whole file.

## Slices (red → green → refactor each)

### Slice 7a — queues

- **Happy:** a fake machine client returns `TaskSummary(pending_ready=10, pending_delayed=0, claimed=2, claimed_stale=0, completed=100, failed=1)` for `render_page`. The result is `QueueRow(kind="render_page", pending=10, claimed=2, completed=100, failed=1)`. The client receives one request that names every local kind.
- **Negative:** the client raises `DiscoveryMachineApiError` with HTTP 500. The queue source returns `SourceError(source="queue", detail="HTTP 500 from /tasks/summary")`. The other sources still return their data.

### Slice 7b — rates

- **Happy:** completed is 100 at t = 0 s and 160 at t = 60 s, with 40 pending. The rate is 60 per minute, and the ETA is 40 seconds.
- **Negative:** the completed count drops, after a requeue or a reset. The rate is `None`, never negative.

### Slice 7c — fleet caps

- **Happy:** two running types, `browser` (2 threads) and `llm` (6 threads, 2048 MiB), give `FleetCap(threads=8, threads_cap=16, vram_mib=2048, vram_cap=3584)`. The caps come from `worker_types.py`, not from the heartbeats.
- **Negative:** a type whose heartbeat says `running` but whose pid fails `process_matches` counts for zero threads and zero VRAM.

### Slice 7d — host

- **Happy:** with psutil replaced by a fake, the result has one CPU percentage per logical CPU and the memory percentage used.
- **Negative:** `nvidia-smi` is not on PATH, so `gpu is None` and there is no error. llama-server refuses the connection, so `llama` is `down`, with no exception.

### Slice 7e — worker heartbeats

- **Happy:** a heartbeat with `state="running"`, updated 2 s ago, whose pid passes `process_matches`, gives a `WorkerRow` in state `running`.
- **Negative:** a heartbeat updated 10 minutes ago gives state `stale`. A heartbeat whose pid fails `process_matches` gives state `dead`. A corrupt file gives a row with an `error` and no crash.

### Slice 7f — log tail

- **Happy:** a log of 10 lines gives its last three lines when three are asked for.
- **Negative:** a missing log gives an empty tail with no error. A sparse 1 GiB file is read only at its last 64 KiB. The test asserts the number of bytes read.

### Slice 7g — least intrusive, read-only, and fence

- **Happy:** a recording machine client sees only `GET` calls across a full `snapshot()` (I11). With a fake clock, a 60-second run of the queue source makes no more than four queue requests, because the interval is 15 s (I14).
- **Negative:** an AST test finds no module under `fleet/` or `monitor/` that imports `typer` or `textual` (I10). It follows the fence test that chief uses for its CLI.

## Green

- Define one `Source` protocol with `name` and `read() -> SourceResult`. Each source is a class in its own module.
- `Monitor` holds the sources, runs each one with its own timeout, and collects the results into `DashboardSnapshot`.
- `RateTracker` is its own class, and it keeps the previous sample.

## Refactor

- Adding a source adds a class to the list. It must not add a branch to `Monitor.snapshot()`. Count the branches in `snapshot()` after the change.
- Each source module stays under about 100 lines. The psutil and `nvidia-smi` parsing moves to `monitor/host_parse.py`, as pure functions tested without a subprocess.

## Verification

```bash
cd apps/discovery-ingest && .venv/bin/python -m pytest tests -k "monitor" -q
cd apps/discovery-ingest && .venv/bin/python -m ruff check discovery_ingest && .venv/bin/python -m mypy discovery_ingest
```

Then one live, read-only snapshot against the API, recorded in the ledger: the queue rows and each source's status.

## Exit

- The live snapshot shows the queue rows from the API. Each other source shows data or a named error.
- The fence and read-only tests pass.
