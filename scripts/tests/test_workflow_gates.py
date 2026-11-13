"""Tests for the job gates in the CI workflows.

The job `if` expressions are evaluated against recorded event contexts. The
evaluator covers only the operators these gates use, and it reads our own
workflow files, so `eval` never sees untrusted text.
"""

import re
from pathlib import Path

import pytest
import yaml

WORKFLOWS = Path(__file__).resolve().parents[2] / ".github" / "workflows"


def load_workflow(name):
    return yaml.safe_load((WORKFLOWS / name).read_text())


def triggers(workflow):
    # YAML 1.1 reads the bare key `on` as boolean True.
    return workflow.get("on", workflow.get(True))


def gate(expression, *, event, draft=None, output=None):
    """Evaluate one job gate for a recorded event."""
    text = re.sub(r"^\$\{\{\s*(.*?)\s*\}\}$", r"\1", expression.strip())
    text = text.replace("github.event_name", repr(event))
    text = text.replace("github.event.pull_request.draft", repr(draft))
    text = re.sub(r"needs\.[\w-]+\.outputs\.\w+", lambda _: repr(output), text)
    text = text.replace("||", " or ").replace("&&", " and ")
    text = re.sub(r"\btrue\b", "True", text)
    text = re.sub(r"\bfalse\b", "False", text)
    return bool(eval(text, {"__builtins__": {}}, {}))


API_JOBS = ["change-set", "lint-and-test", "migrations"]
WEB_JOBS = ["lint-format-typecheck-build"]


def gated_jobs():
    api = load_workflow("api-lint-test.yml")["jobs"]
    web = load_workflow("web-ci.yml")["jobs"]
    return [(api, job) for job in API_JOBS] + [(web, job) for job in WEB_JOBS]


@pytest.mark.parametrize(("jobs", "job"), gated_jobs())
def test_draft_pull_requests_run_no_api_job(jobs, job):
    assert gate(jobs[job]["if"], event="pull_request", draft=True, output="true") is False


@pytest.mark.parametrize(("jobs", "job"), gated_jobs())
def test_ready_pull_requests_and_pushes_still_run_every_gated_job(jobs, job):
    assert gate(jobs[job]["if"], event="pull_request", draft=False, output="true") is True
    assert gate(jobs[job]["if"], event="push", output="true") is True


@pytest.mark.parametrize("name", ["api-lint-test.yml", "web-ci.yml"])
def test_draft_to_ready_transition_triggers_the_workflow(name):
    pull_request = triggers(load_workflow(name))["pull_request"]
    assert "ready_for_review" in pull_request["types"]


@pytest.mark.parametrize("name", ["api-lint-test.yml", "web-ci.yml"])
def test_superseded_pull_request_runs_are_still_cancelled(name):
    concurrency = load_workflow(name)["concurrency"]
    assert concurrency["cancel-in-progress"] == "${{ github.event_name == 'pull_request' }}"


def uses_steps(steps):
    return [step["uses"] for step in steps if "uses" in step]


def test_api_jobs_share_one_python_setup_composite_action():
    api = load_workflow("api-lint-test.yml")["jobs"]
    for job in ["lint-and-test", "migrations"]:
        assert "./.github/actions/setup-api-python" in uses_steps(api[job]["steps"])


def test_api_python_setup_caches_uv_and_pip_downloads_keyed_on_the_lock_file():
    action = yaml.safe_load((WORKFLOWS.parent / "actions" / "setup-api-python" / "action.yml").read_text())
    cache = next(step for step in action["runs"]["steps"] if step.get("uses", "").startswith("actions/cache@"))
    assert "hashFiles('apps/api/uv.lock')" in cache["with"]["key"]
    assert "~/.cache/uv" in cache["with"]["path"]
    assert "~/.cache/pip" in cache["with"]["path"]


def test_migrations_job_runs_only_when_the_change_set_reports_migrations():
    jobs = load_workflow("api-lint-test.yml")["jobs"]
    needs = jobs["migrations"]["needs"]
    assert "change-set" in (needs if isinstance(needs, list) else [needs])
    assert gate(jobs["migrations"]["if"], event="push", output="true") is True
    assert gate(jobs["migrations"]["if"], event="push", output="false") is False
    assert gate(jobs["migrations"]["if"], event="pull_request", draft=False, output="false") is False


def test_change_set_job_exposes_the_detect_step_output():
    jobs = load_workflow("api-lint-test.yml")["jobs"]
    assert jobs["change-set"]["outputs"]["migrations"] == "${{ steps.detect.outputs.migrations }}"


def test_web_npm_cache_is_keyed_on_the_package_lock():
    steps = load_workflow("web-ci.yml")["jobs"]["lint-format-typecheck-build"]["steps"]
    setup_node = next(step for step in steps if step.get("uses", "").startswith("actions/setup-node@"))
    assert setup_node["with"]["cache"] == "npm"
    assert setup_node["with"]["cache-dependency-path"] == "apps/web/package-lock.json"
