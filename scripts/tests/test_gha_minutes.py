"""Tests for the billable-minutes report. `gh` is replaced by recorded responses."""

import json

import pytest

import gha_minutes as gm


def timing(*job_durations_ms, runner="UBUNTU"):
    """A run timing payload shaped like `GET .../actions/runs/{id}/timing`."""
    job_runs = [
        {"job_id": index, "duration_ms": duration}
        for index, duration in enumerate(job_durations_ms)
    ]
    return {
        "billable": {
            runner: {
                "total_ms": sum(job_durations_ms),
                "jobs": len(job_durations_ms),
                "job_runs": job_runs,
            }
        },
        "run_duration_ms": sum(job_durations_ms),
    }


def run(run_id, workflow, created_at, status="completed"):
    """A run row shaped like one entry of `gh run list --json`."""
    return {
        "databaseId": run_id,
        "workflowName": workflow,
        "createdAt": created_at,
        "status": status,
    }


RUNS = [
    run(1, "API Lint & Test", "2026-10-03T09:00:00Z"),
    run(2, "API Lint & Test", "2026-10-20T09:00:00Z"),
    run(3, "API Lint & Test", "2026-09-30T23:30:00Z"),
    run(4, "Web CI", "2026-10-05T09:00:00Z"),
]

RECORDED_TIMING = {
    1: timing(61_000, 0),  # 2 minutes: 61 s bills 2, 0 ms bills 0
    2: timing(120_000),  # 2 minutes
    3: timing(600_000),  # 10 minutes, but created before --since
    4: timing(30_000),  # 1 minute
}


def test_gha_minutes_rounds_each_job_up_to_a_whole_minute():
    assert gm.ceil_minutes(61_000) == 2
    assert gm.ceil_minutes(60_000) == 1
    assert gm.run_billable_minutes(timing(61_000)) == 2


def test_gha_minutes_bills_zero_ms_as_zero_minutes():
    assert gm.ceil_minutes(0) == 0
    assert gm.run_billable_minutes(timing(0)) == 0


def test_gha_minutes_rounds_per_job_not_per_run():
    assert gm.run_billable_minutes(timing(30_000, 30_000)) == 2


def test_gha_minutes_counts_windows_jobs_at_double_rate():
    assert gm.run_billable_minutes(timing(60_000, runner="WINDOWS")) == 2


def test_gha_minutes_sums_billable_minutes_per_workflow_over_a_date_range():
    totals = gm.minutes_by_workflow(RUNS, "2026-10-01", fetch=RECORDED_TIMING.__getitem__)
    assert totals == {"API Lint & Test": 4, "Web CI": 1}


def test_gha_minutes_skips_runs_before_since_without_fetching_their_timing():
    requested = []

    def fetch(run_id):
        requested.append(run_id)
        return RECORDED_TIMING[run_id]

    gm.minutes_by_workflow(RUNS, "2026-10-01", fetch=fetch)
    assert 3 not in requested


def test_gha_minutes_ignores_runs_still_in_progress():
    runs = [run(5, "Web CI", "2026-10-06T09:00:00Z", status="in_progress")]
    assert gm.minutes_by_workflow(runs, "2026-10-01", fetch=lambda _: timing(600_000)) == {}


def test_gha_minutes_reads_timing_from_the_run_endpoint(monkeypatch):
    calls = []

    def fake_gh(args):
        calls.append(args)
        return json.dumps(timing(60_000))

    monkeypatch.setattr(gm, "gh", fake_gh)
    assert gm.fetch_timing(43) == timing(60_000)
    assert calls == [["api", "repos/{owner}/{repo}/actions/runs/43/timing"]]


def test_gha_minutes_warns_when_the_listing_may_miss_runs_in_range(capsys):
    truncated = [run(9, "Web CI", "2026-10-06T09:00:00Z")] * 3
    gm.warn_if_truncated(truncated, limit=3, since="2026-10-01")
    assert "may be missing" in capsys.readouterr().err


def test_gha_minutes_does_not_warn_when_the_oldest_run_read_is_before_since(capsys):
    complete = [run(9, "Web CI", "2026-10-06T09:00:00Z"), run(8, "Web CI", "2026-09-20T09:00:00Z")]
    gm.warn_if_truncated(complete, limit=2, since="2026-10-01")
    assert capsys.readouterr().err == ""


def fake_gh_for(runs, timings):
    """Serve recorded `gh run list` and `gh api .../timing` responses."""

    def fake_gh(args):
        if args[0] == "run":
            return json.dumps(runs)
        return json.dumps(timings[int(args[-1].split("/")[-2])])

    return fake_gh


def test_gha_minutes_prints_each_workflow_and_the_total(monkeypatch, capsys):
    monkeypatch.setattr(gm, "gh", fake_gh_for(RUNS, RECORDED_TIMING))
    assert gm.main(["--since", "2026-10-01"]) == 0
    out = capsys.readouterr().out
    assert "API Lint & Test" in out
    assert out.rstrip().splitlines()[-1].split() == ["5", "total"]


def test_gha_minutes_notes_when_timing_reports_no_billable_minutes(monkeypatch, capsys):
    zero_timing = {run_id: timing(0) for run_id in RECORDED_TIMING}
    monkeypatch.setattr(gm, "gh", fake_gh_for(RUNS, zero_timing))
    gm.main(["--since", "2026-10-01"])
    assert "no billable minutes" in capsys.readouterr().err


def test_gha_minutes_stays_quiet_when_minutes_are_billed(monkeypatch, capsys):
    monkeypatch.setattr(gm, "gh", fake_gh_for(RUNS, RECORDED_TIMING))
    gm.main(["--since", "2026-10-01"])
    assert "no billable minutes" not in capsys.readouterr().err


def test_gha_minutes_rejects_a_malformed_since_date():
    with pytest.raises(SystemExit):
        gm.parse_args(["--since", "01/10/2026"])
