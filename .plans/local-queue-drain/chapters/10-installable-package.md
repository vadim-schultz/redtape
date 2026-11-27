# C10 — Installable package

**Depends on:** C6, C8 · **Batch:** 6 · **Branch:** `feat/local-queue-drain-package`

## Goal

Make `discovery-ingest` an installed command, so the workers and the dashboard run from an installed copy and not from the repository venv. The fleet, the monitor and the dashboard ship inside the existing `redtape-discovery-ingest` distribution (D23).

## Why one distribution

- The fleet starts `discovery-ingest daemon run`, which is the drain code of C1–C5. A second distribution would depend on the first, and the two would drift apart.
- The launcher needs a path to an installed command. A console script provides that path, and C6 finds it with `shutil.which`.

## Scope

1. `pyproject.toml`: add `[project.scripts] discovery-ingest = "discovery_ingest.cli.main:app"`. The Typer app defined in `cli/main.py` is the callable. Confirm the attribute name before writing the line.
2. Extras, each added when its chapter's gate passes:
   - `dashboard = ["textual>=8,<9", "psutil>=7,<8"]` (C8).
   - `local-browser` for Playwright (C2), `local-embed` for the embedding runtime (C1) and `local-translate` for the translation runtime (C3). Their packages are chosen by those chapters' measurements, so this plan does not pin them now.
   - The LLM provider (C4) needs only `httpx`, which the base install already has.
3. The base install adds no UI package and no ML package. The dashboard and the local providers are extras (D21).
4. Install with `uv tool install`, which puts the command on PATH. The exact command, with the extras, is confirmed in the first step of this chapter. Use an editable install while the code is changing, so the installed command runs the repository's code.
5. `requires-python` stays `>=3.11`, as it is now.

## Slices (red → green → refactor each)

### Slice 10a — entry point

- **Happy:** `importlib.metadata.entry_points(group="console_scripts")` contains `discovery-ingest`, and it resolves to the Typer app.
- **Negative:** the entry point does not resolve when its module is missing. The test fails, so a broken install cannot pass.

### Slice 10b — wheel contents

- **Happy:** `uv build --wheel` into a temporary directory produces a wheel whose file list includes `discovery_ingest/fleet/`, `discovery_ingest/monitor/`, `discovery_ingest/tui/` and `discovery_ingest/worker_types.py`.
- **Negative:** the wheel's `Requires-Dist` lines for `textual` and `psutil` carry the marker `extra == "dashboard"`, so a base install does not pull them in (D21).

### Slice 10c — the dashboard without its extra

- **Happy:** with the extra installed, `discovery-ingest dashboard --help` exits 0.
- **Negative:** without the extra, `discovery-ingest dashboard` prints a message that names the extra to install and exits 1. It does not show a traceback.

## Green

- Add the script entry and the extras to `pyproject.toml`.
- Make the `dashboard` command import Textual lazily, so the base command runs without the extra. C8 owns the command; this chapter guards only the import.

## Refactor

- Keep the extras in one block of `pyproject.toml`, sorted by name.
- Check that the fence of C7 still passes, since packaging must not move a UI import into a facade.

## Verification

```bash
cd apps/discovery-ingest && .venv/bin/python -m pytest tests -k "package or entry" -q
cd apps/discovery-ingest && .venv/bin/python -m ruff check discovery_ingest && .venv/bin/python -m mypy discovery_ingest
```

Then by hand: install with `uv tool install` (the command confirmed in step 4), open a new shell, and run `discovery-ingest --help` and `discovery-ingest workers status`.

## Exit

- `discovery-ingest` runs from any directory on this machine.
- `workers up` finds the installed command, and the workers run from it.
