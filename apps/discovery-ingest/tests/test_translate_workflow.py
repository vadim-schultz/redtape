"""The discovery-translate workflow: gated schedule, ledger and queue prechecks, bounded drain, minutes report (search-first C15)."""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml

PATH = Path(__file__).resolve().parents[3] / ".github" / "workflows" / "discovery-translate.yml"
BUDGET_CHECK = "python -m discovery_ingest budget show"
SUMMARY_CHECK = "python -m discovery_ingest translate summary --require-pending"
DRAIN = "python -m discovery_ingest translate drain"
REPORT = "python -m discovery_ingest budget report-minutes"
SECRETS = {"DISCOVERY_API_URL", "DISCOVERY_API_KEY", "CLOUDFLARE_ACCOUNT_ID", "CLOUDFLARE_AI_API_TOKEN"}
AZURE_SECRETS = {"AZURE_TRANSLATOR_KEY", "AZURE_TRANSLATOR_REGION", "AZURE_TRANSLATOR_ENDPOINT"}
AZURE_GATE = "vars.TRANSLATION_ENGINE == 'azure-translator'"


@pytest.fixture(scope="module")
def document() -> dict[Any, Any]:
    loaded = yaml.safe_load(PATH.read_text())
    assert isinstance(loaded, dict)
    return loaded


@pytest.fixture(scope="module")
def job(document: dict[Any, Any]) -> dict[str, Any]:
    drain = document["jobs"]["drain"]
    assert isinstance(drain, dict)
    return drain


def _index(steps: list[dict[str, Any]], needle: str) -> int:
    matches = [i for i, step in enumerate(steps) if needle in str(step.get("run", ""))]
    assert len(matches) == 1, f"expected one step running {needle!r}"
    return matches[0]


def test_the_schedule_is_gated_by_the_translate_variable_and_dispatch_always_works(
    document: dict[Any, Any], job: dict[str, Any]
) -> None:
    """workflow · schedule plus workflow_dispatch; the job runs on dispatch or when DISCOVERY_TRANSLATE_SCHEDULE is enabled."""
    triggers = document[True]
    assert triggers["schedule"] and "workflow_dispatch" in triggers
    assert job["if"] == "github.event_name == 'workflow_dispatch' || vars.DISCOVERY_TRANSLATE_SCHEDULE == 'enabled'"


def test_it_shares_the_pipeline_concurrency_group_and_never_cancels_a_running_drain(document: dict[Any, Any]) -> None:
    """workflow · group discovery-pipeline, cancel-in-progress false, read-only permissions."""
    assert document["concurrency"] == {"group": "discovery-pipeline", "cancel-in-progress": False}
    assert document["permissions"] == {"contents": "read"}


def test_the_job_has_a_timeout_and_requires_that_many_minutes_and_the_llm_neurons_above_the_floor(
    job: dict[str, Any],
) -> None:
    """workflow · the ledger precheck requires the job's timeout in minutes; llm also needs neurons above the query-embedding floor."""
    check = job["steps"][_index(job["steps"], BUDGET_CHECK)]["run"]

    minutes = re.search(r"--require-remaining\s+actions_minutes=(\d+)", check)
    assert minutes is not None and int(minutes.group(1)) == job["timeout-minutes"]
    assert re.search(r'neurons=\$\(\( QUERY_EMBED_RESERVE \+ \d+ \)\)"', check)


def test_the_documented_skip_when_nothing_is_pending_precedes_the_drain_and_gates_every_later_step(
    job: dict[str, Any],
) -> None:
    """workflow · documents the skip when pending_ready is 0: the summary precheck sits before the drain and sets skip."""
    steps = job["steps"]
    summary, drain = _index(steps, SUMMARY_CHECK), _index(steps, DRAIN)

    assert _index(steps, BUDGET_CHECK) < summary < drain
    assert "skip=true" in steps[summary]["run"] and "nothing to translate" in steps[summary]["run"]
    for step in steps[summary + 1 :]:
        if REPORT not in step.get("run", ""):
            assert "steps.budget.outputs.skip" in step["if"], step["name"]


def test_the_drain_writes_a_report_and_the_job_fails_only_when_it_did_not_succeed(job: dict[str, Any]) -> None:
    """workflow · tee drain-report.json, summary in the job page, failure only when succeeded is false."""
    steps = job["steps"]

    assert "tee drain-report.json" in steps[_index(steps, DRAIN)]["run"]
    assert "GITHUB_STEP_SUMMARY" in steps[_index(steps, 'echo "### Translation drain report"')]["run"]
    assert "get('succeeded')" in steps[_index(steps, "json.load(open('drain-report.json'))")]["run"]


def test_an_always_step_reports_the_minutes_last(job: dict[str, Any]) -> None:
    """workflow · the minutes report runs even after a failure, last, with the runner-setup minute added."""
    steps = job["steps"]
    report = steps[_index(steps, REPORT)]

    assert report["if"] == "always()" and report["name"] == steps[-1]["name"] and "+ 1" in report["run"]
    assert "date +%s" in steps[0]["run"] and "GITHUB_ENV" in steps[0]["run"]


def test_the_four_secrets_reach_the_job_and_none_is_echoed(job: dict[str, Any]) -> None:
    """workflow · API URL and key plus the Workers AI account and token as secrets; no step prints them."""
    env = job["env"]
    assert {name for name, value in env.items() if "secrets." in str(value)} == SECRETS | AZURE_SECRETS
    for step in job["steps"]:
        run = str(step.get("run", ""))
        assert not re.search(r"echo[^\n]*\$\{?(CLOUDFLARE_AI_API_TOKEN|DISCOVERY_API_KEY|AZURE_TRANSLATOR_KEY)", run)


def test_azure_secrets_are_passed_only_when_the_engine_is_azure_translator(job: dict[str, Any]) -> None:
    """workflow · the three Azure secrets are read only when TRANSLATION_ENGINE is azure-translator, else the value is empty or the default."""
    env = job["env"]

    assert env["AZURE_TRANSLATOR_KEY"] == f"${{{{ {AZURE_GATE} && secrets.AZURE_TRANSLATOR_KEY || '' }}}}"
    assert env["AZURE_TRANSLATOR_REGION"] == f"${{{{ {AZURE_GATE} && secrets.AZURE_TRANSLATOR_REGION || '' }}}}"
    assert env["AZURE_TRANSLATOR_ENDPOINT"] == (
        f"${{{{ {AZURE_GATE} && secrets.AZURE_TRANSLATOR_ENDPOINT || 'https://api.cognitive.microsofttranslator.com' }}}}"
    )
    assert job["environment"] == "discovery-translate"


def _run_step(job: dict[str, Any], needle: str, env: dict[str, str], bin_dir: Path) -> subprocess.CompletedProcess[str]:
    """Run one step's shell script as the runner does, with ``python`` replaced by a fake that logs its arguments."""
    script = job["steps"][_index(job["steps"], needle)]["run"]
    return subprocess.run(
        ["bash", "--noprofile", "--norc", "-eo", "pipefail", "-c", script],
        env={**os.environ, **env, "PATH": f"{bin_dir}:{os.environ['PATH']}"},
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.fixture
def runner(tmp_path: Path) -> dict[str, Any]:
    """A fake ``python`` that appends its arguments to a log and exits with FAKE_EXIT, and the step's output files."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    fake = bin_dir / "python"
    fake.write_text('#!/bin/sh\necho "$@" >> "$FAKE_LOG"\nexit "${FAKE_EXIT:-0}"\n', encoding="utf-8")
    fake.chmod(0o755)
    base = {
        "FAKE_LOG": str(tmp_path / "calls.log"),
        "GITHUB_OUTPUT": str(tmp_path / "output"),
        "GITHUB_STEP_SUMMARY": str(tmp_path / "summary"),
        "QUERY_EMBED_RESERVE": "1000",
        "AZURE_TRANSLATOR_MIN_REMAINING_CHARS": "20000",
        "MAX_TASKS": "10",
    }
    return {"bin": bin_dir, "base": base, "tmp": tmp_path}


def test_the_character_precheck_exits_3_when_remaining_is_below_the_minimum(
    job: dict[str, Any], runner: dict[str, Any]
) -> None:
    """workflow · for azure-translator the budget check asks for azure_translator_chars at the minimum; exit 3 skips the job without failing it."""
    env = {**runner["base"], "TRANSLATION_ENGINE": "azure-translator", "FAKE_EXIT": "3"}

    result = _run_step(job, BUDGET_CHECK, env, runner["bin"])

    assert result.returncode == 0, result.stderr
    assert "skip=true" in (runner["tmp"] / "output").read_text()
    calls = (runner["tmp"] / "calls.log").read_text()
    assert "--require-remaining azure_translator_chars=20000" in calls and "--resource azure_translator_chars" in calls
    assert "neurons" not in calls


def test_the_neuron_precheck_runs_only_for_the_llm_engine(job: dict[str, Any], runner: dict[str, Any]) -> None:
    """workflow · the llm engine checks neurons above the query-embedding floor; azure-translator never does."""
    _run_step(job, BUDGET_CHECK, {**runner["base"], "TRANSLATION_ENGINE": "llm"}, runner["bin"])
    llm_calls = (runner["tmp"] / "calls.log").read_text()
    (runner["tmp"] / "calls.log").unlink()
    _run_step(job, BUDGET_CHECK, {**runner["base"], "TRANSLATION_ENGINE": "azure-translator"}, runner["bin"])
    azure_calls = (runner["tmp"] / "calls.log").read_text()

    assert "--require-remaining neurons=1100" in llm_calls and "azure_translator_chars" not in llm_calls
    assert "neurons" not in azure_calls and "azure_translator_chars=20000" in azure_calls


def test_engine_azure_translator_with_no_secret_fails_at_the_precheck_with_a_message(
    job: dict[str, Any], runner: dict[str, Any]
) -> None:
    """workflow · azure-translator with an empty key or region fails the job at its precheck and names the secret, never a silent skip."""
    steps = job["steps"]
    check = _index(steps, "::error::")
    assert steps[check]["if"] == "env.TRANSLATION_ENGINE == 'azure-translator'"
    assert check < _index(steps, BUDGET_CHECK)

    env = {
        **runner["base"],
        "TRANSLATION_ENGINE": "azure-translator",
        "AZURE_TRANSLATOR_KEY": "",
        "AZURE_TRANSLATOR_REGION": "westeurope",
    }
    result = _run_step(job, "::error::", env, runner["bin"])

    assert result.returncode != 0
    assert "AZURE_TRANSLATOR_KEY" in result.stdout and "westeurope" not in result.stdout
    assert _run_step(job, "::error::", {**env, "AZURE_TRANSLATOR_KEY": "k"}, runner["bin"]).returncode == 0


def test_the_dispatch_inputs_default_to_a_bounded_drain(document: dict[Any, Any], job: dict[str, Any]) -> None:
    """workflow · every bound is an input with a default, passed to the drain command."""
    inputs = document[True]["workflow_dispatch"]["inputs"]

    assert set(inputs) == {"max_tasks", "max_batches", "time_budget_seconds", "neuron_budget"}
    assert (inputs["max_tasks"]["default"], inputs["neuron_budget"]["default"]) == ("10", "2500")
    run = job["steps"][_index(job["steps"], DRAIN)]["run"]
    for flag in ("--max-tasks", "--max-batches", "--time-budget-seconds", "--neuron-budget"):
        assert flag in run


def test_it_runs_after_the_morning_embed_drain_and_just_before_the_evening_one(document: dict[Any, Any]) -> None:
    """workflow · one run a day at 17:10 UTC: after the 06:10 embed drain, an hour before the 18:10 one that embeds it."""
    (schedule,) = document[True]["schedule"]
    minute, hour, *_ = schedule["cron"].split()
    embed = yaml.safe_load((PATH.parent / "discovery-embed.yml").read_text())[True]["schedule"][0]["cron"]
    embed_hours = [int(part) for part in embed.split()[1].split(",")]

    assert (int(minute), int(hour)) == (10, 17) and min(embed_hours) < int(hour) < max(embed_hours)


def test_the_floor_and_the_engine_are_variables_with_safe_defaults(job: dict[str, Any]) -> None:
    """workflow · QUERY_EMBED_RESERVE (default 1000) and TRANSLATION_ENGINE (default llm) come from variables, never secrets."""
    env = job["env"]

    assert env["QUERY_EMBED_RESERVE"] == "${{ vars.QUERY_EMBED_RESERVE || '1000' }}"
    assert env["TRANSLATION_ENGINE"] == "${{ vars.TRANSLATION_ENGINE || 'llm' }}"


def test_the_glossary_mode_and_the_character_minimum_are_variables_with_safe_defaults(job: dict[str, Any]) -> None:
    """workflow · TRANSLATION_GLOSSARY_MODE (default strict) and AZURE_TRANSLATOR_MIN_REMAINING_CHARS (default 20000) are variables."""
    env = job["env"]

    assert env["TRANSLATION_GLOSSARY_MODE"] == "${{ vars.TRANSLATION_GLOSSARY_MODE || 'strict' }}"
    assert env["AZURE_TRANSLATOR_MIN_REMAINING_CHARS"] == "${{ vars.AZURE_TRANSLATOR_MIN_REMAINING_CHARS || '20000' }}"
