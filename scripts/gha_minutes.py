#!/usr/bin/env python3
"""Report billable GitHub Actions minutes per workflow. Read-only.

Uses the operator's `gh` session: `gh run list` for the runs, and
`gh api repos/{owner}/{repo}/actions/runs/{id}/timing` for each run's per-job
durations. GitHub bills each job rounded up to a whole minute, so this report
does the same.

    python scripts/gha_minutes.py --since 2026-10-01
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import defaultdict
from collections.abc import Callable, Iterable
from datetime import date

MS_PER_MINUTE = 60_000
RUN_FIELDS = "databaseId,workflowName,createdAt,status"
# GitHub bills Windows jobs at 2x and macOS jobs at 10x the Linux rate.
RUNNER_MULTIPLIER = {"UBUNTU": 1, "WINDOWS": 2, "MACOS": 10}

Fetch = Callable[[int], dict]


def gh(args: list[str]) -> str:
    """Run `gh` and return its stdout. The only function that reaches GitHub."""
    result = subprocess.run(["gh", *args], check=True, capture_output=True, text=True)
    return result.stdout


def ceil_minutes(duration_ms: int) -> int:
    """Round one job's duration up to a whole minute, as GitHub bills it."""
    return (duration_ms + MS_PER_MINUTE - 1) // MS_PER_MINUTE


def run_billable_minutes(timing: dict) -> int:
    """Billable minutes of one run: each job rounded up, weighted by runner OS."""
    total = 0
    for runner, entry in (timing.get("billable") or {}).items():
        job_minutes = sum(ceil_minutes(job["duration_ms"]) for job in entry.get("job_runs", []))
        total += RUNNER_MULTIPLIER.get(runner, 1) * job_minutes
    return total


def fetch_timing(run_id: int) -> dict:
    """The per-job timing of one run, as GitHub returns it."""
    return json.loads(gh(["api", f"repos/{{owner}}/{{repo}}/actions/runs/{run_id}/timing"]))


def list_runs(limit: int) -> list[dict]:
    """The most recent runs of the current repository, newest first."""
    return json.loads(gh(["run", "list", "--limit", str(limit), "--json", RUN_FIELDS]))


def counts_toward(run: dict, since: str) -> bool:
    """A run counts once it has finished and was created on or after `since`."""
    return run["status"] == "completed" and run["createdAt"][:10] >= since


def minutes_by_workflow(
    runs: Iterable[dict], since: str, fetch: Fetch = fetch_timing
) -> dict[str, int]:
    """Billable minutes per workflow name, for the runs that count toward `since`."""
    totals: dict[str, int] = defaultdict(int)
    for run in runs:
        if counts_toward(run, since):
            totals[run["workflowName"]] += run_billable_minutes(fetch(run["databaseId"]))
    return dict(totals)


def render(totals: dict[str, int]) -> str:
    """A table of workflows, largest first, with the total on the last line."""
    by_size = sorted(totals.items(), key=lambda item: -item[1])
    lines = [f"{minutes:>6}  {name}" for name, minutes in by_size]
    lines.append(f"{sum(totals.values()):>6}  total")
    return "\n".join(lines)


def warn_if_truncated(runs: list[dict], limit: int, since: str) -> None:
    """Warn on stderr when the listing hit the limit before reaching back to `since`."""
    hit_limit = len(runs) >= limit
    if hit_limit and runs[-1]["createdAt"][:10] >= since:
        print(f"warning: only the {limit} most recent runs were read; older runs may be missing",
              file=sys.stderr)


UNBILLED_NOTE = (
    "note: GitHub's run timing reports no billable minutes for these runs, so the total is zero. "
    "Read the billed figure from the usage report (Settings, Billing and licensing, Usage)."
)


def note_if_unbilled(totals: dict[str, int]) -> None:
    """Say so when no minutes came back, so a zero is not read as a bill."""
    if sum(totals.values()) == 0:
        print(UNBILLED_NOTE, file=sys.stderr)


def iso_date(text: str) -> str:
    """Accept only a YYYY-MM-DD calendar date."""
    return date.fromisoformat(text).isoformat()


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Billable Actions minutes per workflow (read-only).")
    parser.add_argument("--since", required=True, type=iso_date, metavar="YYYY-MM-DD",
                        help="count runs created on or after this UTC date")
    parser.add_argument("--limit", type=int, default=1000, help="read at most this many recent runs")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    runs = list_runs(args.limit)
    warn_if_truncated(runs, args.limit, args.since)
    totals = minutes_by_workflow(runs, args.since)
    note_if_unbilled(totals)
    print(render(totals))
    return 0


if __name__ == "__main__":
    sys.exit(main())
