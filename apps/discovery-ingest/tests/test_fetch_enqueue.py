"""fetch_url enqueues a render_page task after a successful HTML fetch (chapter 15, Loop C)."""

from __future__ import annotations

import hashlib
import uuid

import httpx
import pytest
from discovery_ingest.schemas import DrainReport
from discovery_ingest.worker.drain import run_worker_drain
from discovery_ingest.worker.fetcher import PoliteUrlFetcher
from discovery_ingest.worker.policy import DrainPolicy

from drain_deps_for import deps_for
from render_fakes import CATALOGUE_ID, FakeApi, task_json

PAGE = "https://portal.example/service/1"
HTML = {"content-type": "text/html; charset=utf-8"}


def _fetch(monkeypatch: pytest.MonkeyPatch, api: FakeApi) -> DrainReport:
    api.batches = [[task_json(uuid.uuid4(), PAGE, kind="fetch_url")]]
    client = api.client(monkeypatch)
    return run_worker_drain(deps_for(client, PoliteUrlFetcher(min_interval_per_host_s=0)), DrainPolicy(max_tasks=1))


def test_fetch_url_enqueues_render_page_with_the_final_url_after_a_200_html_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """fetch_url · a redirect then 200 text/html enqueues render_page for the final url at default priority."""
    api = FakeApi([])
    api.pages = {
        PAGE: httpx.Response(301, headers={"location": "https://portal.example/final"}),
        "https://portal.example/final": httpx.Response(200, headers=HTML, content=b"<html>x</html>"),
    }

    report = _fetch(monkeypatch, api)

    ((_, _, body),) = [call for call in api.calls if call[0] == "enqueue"]
    assert body == {
        "catalogue_service_id": str(CATALOGUE_ID),
        "kind": "render_page",
        "target_url": "https://portal.example/final",
        "priority": 100,
    }
    assert (report.completed, report.render_enqueue_failed) == (1, 0)


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(404, headers=HTML, content=b"gone"),
        httpx.Response(503, headers=HTML, content=b"down"),
        httpx.Response(200, headers={"content-type": "application/pdf"}, content=b"%PDF"),
        httpx.Response(200, headers={"content-type": "application/json"}, content=b"{}"),
        httpx.Response(301, headers={"location": PAGE}),
    ],
    ids=["404", "503", "pdf", "json", "redirect loop"],
)
def test_fetch_url_does_not_enqueue_for_a_failed_fetch_or_a_non_html_body(
    monkeypatch: pytest.MonkeyPatch, response: httpx.Response
) -> None:
    """fetch_url · no render_page for a failed fetch, a non-html 200 or a redirect that never lands."""
    api = FakeApi([])
    api.pages = {PAGE: response}

    _fetch(monkeypatch, api)

    assert [call for call in api.calls if call[0] == "enqueue"] == []


def test_fetch_url_does_not_enqueue_for_a_login_wall_url_but_still_completes(monkeypatch: pytest.MonkeyPatch) -> None:
    """fetch_url · a final url that looks like login completes the fetch and enqueues nothing."""
    api = FakeApi([])
    api.pages = {
        PAGE: httpx.Response(302, headers={"location": "https://sso.example/Account/Login?next=1"}),
        "https://sso.example/Account/Login?next=1": httpx.Response(200, headers=HTML, content=b"<form>"),
    }

    report = _fetch(monkeypatch, api)

    assert [call for call in api.calls if call[0] == "enqueue"] == [] and report.completed == 1


@pytest.mark.parametrize("status", [500, 507])
def test_an_enqueue_error_is_counted_and_does_not_fail_the_fetch(monkeypatch: pytest.MonkeyPatch, status: int) -> None:
    """fetch_url · a refused enqueue still completes the fetch and is counted as render_enqueue_failed."""
    api = FakeApi([])
    api.pages = {PAGE: httpx.Response(200, headers=HTML, content=b"<html>x</html>")}
    api.enqueue_status = status

    report = _fetch(monkeypatch, api)

    assert (report.completed, report.failed, report.render_enqueue_failed) == (1, 0, 1)
    assert [call for call in api.calls if call[0] == "complete"]


def test_an_unchanged_body_enqueues_no_render_and_the_fetch_still_completes(monkeypatch: pytest.MonkeyPatch) -> None:
    """fetch_url · negative: the API says the body is unchanged and was rendered recently, so no render_page is enqueued."""
    api = FakeApi([])
    api.pages = {PAGE: httpx.Response(200, headers=HTML, content=b"<html>x</html>")}
    api.fetch_answer = {"render_due": False, "render_input_key": None}

    report = _fetch(monkeypatch, api)

    assert [call for call in api.calls if call[0] == "enqueue"] == []
    assert report.completed == 1


def test_a_changed_body_enqueues_a_render_and_logs_the_sha256_of_the_body(monkeypatch: pytest.MonkeyPatch) -> None:
    """fetch_url · happy: a body the API marks due is enqueued, and the fetch log carries the sha256 of the bytes read."""
    body = b"<html>x</html>"
    api = FakeApi([])
    api.pages = {PAGE: httpx.Response(200, headers=HTML, content=body)}
    api.fetch_answer = {"render_due": True, "render_input_key": None}

    _fetch(monkeypatch, api)

    ((_, log),) = api.named("fetches")
    assert log["body_sha256"] == hashlib.sha256(body).hexdigest()
    assert log["final_url"] == PAGE
    assert [call[2] for call in api.calls if call[0] == "enqueue"] == [
        {"catalogue_service_id": str(CATALOGUE_ID), "kind": "render_page", "target_url": PAGE, "priority": 100}
    ]


def test_a_refresh_verdict_enqueues_the_render_under_its_input_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """fetch_url · happy: a refresh the API keys by week is enqueued under that key, so it does not collide with the first render."""
    api = FakeApi([])
    api.pages = {PAGE: httpx.Response(200, headers=HTML, content=b"<html>x</html>")}
    api.fetch_answer = {"render_due": True, "render_input_key": "rr:2026-W47"}

    _fetch(monkeypatch, api)

    assert [call[2] for call in api.calls if call[0] == "enqueue"] == [
        {
            "catalogue_service_id": str(CATALOGUE_ID),
            "kind": "render_page",
            "target_url": PAGE,
            "priority": 100,
            "input_key": "rr:2026-W47",
        }
    ]
