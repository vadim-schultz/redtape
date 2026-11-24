"""An llm_extract drain with concurrency settles every task it claimed, and a stop releases only the unstarted ones (chapter 5, loop B)."""

from __future__ import annotations

import threading

import pytest
from discovery_ingest.extract.llm.errors import LlmQuotaExceeded
from discovery_ingest.schemas import DrainReport
from discovery_ingest.worker.drain import run_worker_drain
from discovery_ingest.worker.policy import DrainPolicy

from drain_deps_for import deps_for
from llm_worker_fakes import SERVICE, LlmApi, ScriptedLlm, llm_task, resources
from render_fakes import robots_fetcher

LEDGER_BUDGET = 5000.0


def _tasks(count: int) -> list[dict[str, object]]:
    return [llm_task(url=f"https://portal.example/service/{number}") for number in range(count)]


def _drain(monkeypatch: pytest.MonkeyPatch, api: LlmApi, llm: ScriptedLlm, policy: DrainPolicy) -> DrainReport:
    return run_worker_drain(deps_for(api.client(monkeypatch), robots_fetcher(), llm=resources(llm)), policy)


def test_an_llm_drain_with_concurrency_3_settles_every_task_it_claimed(monkeypatch: pytest.MonkeyPatch) -> None:
    """llm drain · happy: three tasks of one batch are in the model at the same time (a barrier of three) and all three complete."""
    api = LlmApi(_tasks(3))
    barrier = threading.Barrier(3, timeout=5)
    llm = ScriptedLlm(SERVICE, on_call=lambda _call: barrier.wait())
    policy = DrainPolicy(max_tasks=3, kinds=("llm_extract",), neuron_budget=LEDGER_BUDGET, concurrency=3)

    report = _drain(monkeypatch, api, llm, policy)

    assert (report.claimed, report.completed, report.released, report.failed) == (3, 3, 0, 0)
    assert report.claimed == report.completed + report.failed + report.skipped + report.released
    assert report.llm_calls == 3 and api.named("fail") == []


def test_a_stop_mid_batch_releases_the_unstarted_tasks_and_lets_the_in_flight_call_settle(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """llm drain · negative: concurrency 2 over four tasks; both first calls are in flight together and the second one hits the quota. The call still in flight settles; the quota task and the two unstarted ones are released."""
    tasks = _tasks(4)
    api = LlmApi(tasks)
    barrier = threading.Barrier(2, timeout=5)
    llm = ScriptedLlm(SERVICE, LlmQuotaExceeded("daily neuron quota reached"), on_call=lambda _call: barrier.wait())
    policy = DrainPolicy(max_tasks=4, kinds=("llm_extract",), neuron_budget=LEDGER_BUDGET, concurrency=2)

    report = _drain(monkeypatch, api, llm, policy)

    settled = {str(task_id) for task_id, _body in api.named("complete")}
    released = {str(task_id) for task_id, _body in api.named("release")}
    every_task = {str(task["id"]) for task in tasks}
    assert (report.stop_reason, report.completed, report.released, report.failed) == ("llm_quota", 1, 3, 0)
    assert report.llm_calls == 2 and api.named("fail") == []
    assert settled | released == every_task and not settled & released
    assert len(settled) == 1 and len(released) == 3
