# C8 — Textual dashboard (terminal app)

**Depends on:** C6, C7 · **Batch:** 5 · **Branch:** `feat/local-queue-drain-dashboard`

## Goal

`discovery-ingest dashboard` runs a Textual application in the terminal the operator chooses. It shows the `DashboardSnapshot`: queues with rates and ETAs for the local kinds, the local workers, budgets, the host, and a log tail for the selected worker. It is read-only. It never starts or stops a process (I13) and it makes no write request (I11). Where that terminal sits is not part of this plan (D19).

## Packaging

- Textual and psutil form the `dashboard` extra of the distribution (C10, D21). The worker processes install neither, so no worker imports Textual.

## Layout

One screen, with one module per panel under `tui/panels/`:

- **Queues:** kind, pending, claimed, failed, completed per minute, ETA. Only the kinds that local worker types drain.
- **Workers:** type, state, pid, claimed, completed, failed, heartbeat age, and the last error.
- **Budgets:** remaining against cap for each resource.
- **Host:** CPU summary, memory, GPU (or "no driver"), llama-server health.
- **Log:** the tail of the selected worker's log.
- **Footer:** source errors, and the time of the last refresh of each source.

Refresh intervals (D26): queues 15 s, budgets 60 s, host and workers 5 s. The log refreshes when the selection changes or on `r`. Each source runs on a worker thread with its own timeout, so a slow source cannot freeze the screen.

Keys: `q` quits, `r` refreshes now, `p` pauses the refresh, and the number keys select a worker for the log panel. No key writes anything.

## Slices (red → green → refactor each)

Tests use Textual's pilot (`app.run_test()`), with a fake `Monitor` that returns fixed snapshots.

### Slice 8a — render

- **Happy:** after mount, the Queues panel row for `render_page` shows the values of the fixture snapshot.
- **Negative:** the fake's log source returns `SourceError`. The Log panel shows the error text, and the Queues panel still shows its rows.

### Slice 8b — refresh

- **Happy:** the second snapshot changes `pending` for `render_page` from 10 to 7. After the 15 s queue tick, or after `r`, the table shows 7.
- **Negative:** a source that sleeps for 5 s does not delay the Host panel. The Queues panel keeps its last values, with their age.

### Slice 8c — keys and the read-only rule

- **Happy:** `q` ends the application with return code 0. A number key selects that worker's log.
- **Negative:** no key calls `WorkerFleet.up`, `down` or `restart`. The test replaces the fleet with a recording fake and asserts zero calls (I13). The test also asserts that the machine client records no write request (I11).

### Slice 8d — command

- **Happy:** the `dashboard` command builds `DashboardApp` with a `Monitor` made from the settings. A fake factory is injected.
- **Negative:** without a TTY, `dashboard` prints "run the dashboard in a terminal" and exits 1.

## Green

- `tui/app.py`: the App, its bindings and its timers.
- `tui/panels/`, one module per panel: `queues.py`, `workers.py`, `budgets.py`, `host.py`, `log.py`, `footer.py`.
- `tui/format.py`: ages, percentages, rates and ETAs as pure functions, tested without Textual.
- `cli/dashboard.py`: the `dashboard` command, one facade call (`Monitor`) and the app. It is registered in `cli/main.py`.

## Refactor

- The panels share a base class, `Panel`, which owns the table or bar update and the source-error line.
- Each panel module stays under about 100 lines.
- In `app.py`, one function per refresh interval, not one branch per source.

## Verification

```bash
cd apps/discovery-ingest && .venv/bin/python -m pytest tests -k "dashboard" -q   # with the dashboard extra installed
cd apps/discovery-ingest && .venv/bin/python -m ruff check discovery_ingest && .venv/bin/python -m mypy discovery_ingest
```

Then by hand, in a terminal of 200×50: each panel against `workers status` and the API.

## Exit

- A 30-minute session shows queues and workers updating without a freeze. A source error appears only on its own panel.
- The workers keep running after the dashboard is closed. `workers status` shows it.
