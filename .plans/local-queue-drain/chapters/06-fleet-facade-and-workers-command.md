# C6 — Process fleet facade and workers command

**Depends on:** C5 · **Batch:** 4 · **Branch:** `feat/local-queue-drain-fleet`

## Goal

Start, stop and inspect the local worker processes through one facade, `WorkerFleet`, and expose it through a `workers` typer group. Each worker type runs as a detached process, started the way `nohup` starts a job: a new session, no terminal, output appended to a log file, no root and no systemd (D18). The facade returns data and never prints. The typer handlers make one facade call each and print the result (D17).

## Scope

1. `fleet/launcher.py`: `Launcher` starts `discovery-ingest daemon run --type <type>` with `subprocess.Popen(..., start_new_session=True, stdin=DEVNULL, stdout=log, stderr=STDOUT, env=...)`. The log is `<state dir>/redtape-workers/logs/<type>.log`, opened in append mode. `start_new_session=True` gives the effect of `setsid`, so no terminal is attached and closing a terminal does not reach the worker. This is the only module in `fleet/` that calls `Popen`.
2. `fleet/pidfile.py`: `PidFile` reads, writes and removes `<state dir>/redtape-workers/<type>.pid`.
3. `fleet/envfile.py`: loads the environment for the workers from `~/.config/redtape/worker.env`, one `KEY=VALUE` per line. A file whose mode is not `0600` is refused with `FleetError`, which names the path and the mode. Values are never printed.
4. `fleet/facade.py`: `WorkerFleet(launcher, pidfiles, types)` with `status()`, `up()`, `down()` and `restart(types)`. Each returns Pydantic models. `up()` starts every type in `worker_types.py` that is not running (D24). `down()` stops every running type. `restart(types)` restarts the named types.
5. `process_matches(pid, worker_type)` from `worker_state.py` (C5) decides whether a pid is one of ours before any signal is sent. It reads `/proc/<pid>/cmdline`.
6. `cli/workers.py`: a typer group `workers` with `status`, `up`, `down` and `restart [TYPE]`. Each handler makes one facade call, prints the result, and exits 1 on `FleetError`. An unknown type name exits 2, as a usage error.

## Slices (red → green → refactor each)

### Slice 6a — status

- **Happy:** a pidfile holds a pid whose process matches its worker type. `status()` reports that type as `running`, with that pid. A type without a pidfile reports `stopped`.
- **Negative:** a pidfile holds a pid that is no longer alive. `status()` reports `stale` and leaves the pidfile in place. Only `up` removes stale pidfiles, so a status check changes nothing.

### Slice 6b — up

- **Happy:** with a fake launcher and no workers running, `up()` starts each type in the table once, in table order. Each start passes `start_new_session=True` and the log path of that type.
- **Negative:** `discovery-ingest` is not on PATH. `up()` raises `FleetError` that names the command, and the launcher is not called.

### Slice 6c — no duplicates, no pid reuse

- **Happy:** `up()` run twice starts each type once. The second call reports `running` for every type.
- **Negative:** a pidfile holds a live pid that `process_matches` rejects, because the pid was reused. `up()` sends no signal to that pid, reports the type as `stale`, and starts a fresh process.

### Slice 6d — down

- **Happy:** `down()` sends SIGTERM to each running worker's pid. A process still alive after 10 s gets SIGKILL. The test uses a fake signal sender and a fake clock.
- **Negative:** a pidfile holds a pid that `process_matches` rejects. `down()` sends no signal to it, and it reports the type as `stale`.

### Slice 6e — environment file

- **Happy:** a `0600` file of `KEY=VALUE` lines is loaded into the environment passed to the launcher.
- **Negative:** a `0644` file is refused. The `FleetError` names the path and the mode. A sentinel value in the file appears in no message and in no log.

### Slice 6f — CLI

- **Happy:** with `WorkerFleet` replaced by a fake, `workers status` exits 0 and prints one line per type in the table.
- **Negative:** `workers restart bogus` exits 2 and names the known types. `workers up` with a fleet that raises `FleetError` exits 1.

## Green

- Implement the launcher, the pidfile, the environment file loader and `WorkerFleet`, each in its own module. Add the `workers` group to `cli/main.py`.
- Keep the mapping from each command to its action in one table, not in branches.

## Refactor

- `down` and `restart` share one `_signal_all(types, signal)` helper. Check the branch count of `facade.py` after the change.
- `facade.py` stays under about 100 lines. Each CLI handler makes one facade call.
- Add `fleet/` to the import fence of C7.

## Verification

```bash
cd apps/discovery-ingest && .venv/bin/python -m pytest tests -k "fleet or workers" -q
cd apps/discovery-ingest && .venv/bin/python -m ruff check discovery_ingest && .venv/bin/python -m mypy discovery_ingest
```

Then, by hand, once the package is installed (C10): `discovery-ingest workers up`, `discovery-ingest workers status`, `discovery-ingest workers down`.

## Exit

- `workers status` lists every type in `worker_types.py`, with its state and pid.
- `workers up` starts every type in the table. `workers down` stops them all.
