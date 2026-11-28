# C9 — Operator runbook and logout check

**Depends on:** C6, C8 · **Batch:** 6 · **Branch:** `feat/local-queue-drain-runbook`

## Goal

The workers keep running after the operator logs out (D25). An operator runbook says how to start, stop, check, read the logs and recover the fleet. The runbook is tested against the CLI, so it cannot name a command that does not exist.

## Process model

- `workers up` starts each type as a detached process: a new session, no terminal attached, stdin from `/dev/null`, and stdout and stderr appended to the type's log file (C6).
- No systemd unit and no root are involved (D18).
- Logind does not kill user processes on this machine. `/etc/systemd/logind.conf` has `#KillUserProcesses=no`, which is the default, so the processes should survive the session ending. The manual check below confirms it with a real logout.
- Processes do not survive a reboot. Starting the fleet again is `workers up` (O10).

## Slices (red → green → refactor each)

### Slice 9a — runbook commands exist

- **Happy:** a test reads `docs/operations/local-worker-fleet.md` and finds that every command it names is one the CLI defines: `workers status`, `workers up`, `workers down`, `workers restart`, `dashboard`, `daemon run`.
- **Negative:** a runbook command that the CLI does not define fails the test.

### Slice 9b — log paths match

- **Happy:** the runbook's log section names the log path of each type, and a test checks that each path matches the path the launcher writes (C6).
- **Negative:** a log path in the runbook that the launcher does not write fails the test.

## Green

- `docs/operations/local-worker-fleet.md` covers: what the fleet is; the install command (C10); the environment file and its required mode; `workers up`, `down`, `status` and `restart`; the caps of each type in `worker_types.py` (slots, threads, VRAM) and the nice level (D27); the dashboard command; where the logs are; and recovery. Recovery covers a worker in `error` after a setup error: fix the environment file, then `discovery-ingest workers restart <type>`. Recovery after a reboot is `discovery-ingest workers up`.

## Refactor

- The runbook test and the CLI both read one list of command names, so they cannot drift apart.

## Verification

```bash
cd apps/discovery-ingest && .venv/bin/python -m pytest tests -k "runbook" -q
```

Then by hand, on this machine, as the operator:

1. Run `discovery-ingest workers up`, then `discovery-ingest workers status`. Every type shows `running` with a pid.
2. Log out of the Plasma session completely. Log in again, or reach the machine over SSH.
3. Run `discovery-ingest workers status`. Every pid is still alive, and the heartbeats are still updating.

Record the result, with the date and the time of the logout, in the run ledger.

## Exit

- The logout check is recorded, and the workers were running after the logout.
- The runbook test passes.
