"""render_page with RENDER_FUSED_SCREENSHOT on: one /snapshot call, the HTML first, the screenshot best effort (chapter 8)."""

from __future__ import annotations

import uuid

import pytest
from discovery_ingest.browser.errors import BrowserRequestError, ScreenshotOversize, ScreenshotUnreadable
from discovery_ingest.browser.port import RenderedPage, ScreenshotImage
from discovery_ingest.config import load_browser_settings
from discovery_ingest.schemas import DrainReport
from discovery_ingest.worker.drain import run_worker_drain
from discovery_ingest.worker.policy import DrainPolicy

from drain_deps_for import deps_for
from render_fakes import FakeApi, FakeBrowser, page, robots_fetcher, task_json

URL = "https://portal.example/service/1"
FINAL = "https://portal.example/final"
JPEG = b"\xff\xd8\xff" + b"j" * 64


def shot(html: str | None = "<p>Bürger</p>") -> ScreenshotImage:
    """Return one fused call's image with the DOM of the same session."""
    return ScreenshotImage(JPEG, "image/jpeg", 2000, html, 200, FINAL)


def _tasks(count: int = 1) -> list[dict[str, object]]:
    return [task_json(uuid.uuid4(), URL) for _ in range(count)]


def _drain(
    monkeypatch: pytest.MonkeyPatch,
    api: FakeApi,
    browser: FakeBrowser,
    *,
    fused: bool = True,
    hook_uploads: list[int] | None = None,
) -> DrainReport:
    after = (lambda task, artifact: hook_uploads.append(len(api.uploads))) if hook_uploads is not None else None
    policy = DrainPolicy(max_tasks=5, kinds=("render_page",), browser_budget_seconds=480.0)
    deps = deps_for(
        api.client(monkeypatch),
        robots_fetcher(),
        browser=browser,
        after_snapshot=after,
        fused_screenshot=fused,
    )
    return run_worker_drain(deps, policy)


def _kinds(api: FakeApi) -> list[str]:
    """Return the artifact kind of each upload in upload order; only the HTML form names ``html_snapshot``."""
    return ["html_snapshot" if b"html_snapshot" in request.content else "screenshot" for request in api.uploads]


def test_one_render_task_uploads_the_html_and_the_screenshot_from_one_call(monkeypatch: pytest.MonkeyPatch) -> None:
    """render_page · fused: one /snapshot call and no /content call; two artifacts, the HTML then the screenshot."""
    api, browser = FakeApi([_tasks()]), FakeBrowser(shots=[shot()])

    report = _drain(monkeypatch, api, browser)

    assert browser.shot_calls == [URL] and browser.calls == []
    assert _kinds(api) == ["html_snapshot", "screenshot"]
    assert [body for _, body in api.named("complete")] == [None]
    assert (report.completed, report.failed) == (1, 0)


def test_the_html_is_uploaded_before_the_after_snapshot_hook_runs(monkeypatch: pytest.MonkeyPatch) -> None:
    """render_page · fused: at the hook exactly one upload exists (the HTML); the screenshot follows the hook."""
    api, browser, seen = FakeApi([_tasks()]), FakeBrowser(shots=[shot()]), []

    _drain(monkeypatch, api, browser, hook_uploads=seen)

    assert seen == [1]
    assert _kinds(api) == ["html_snapshot", "screenshot"]


def test_an_oversize_screenshot_keeps_the_html_and_completes_with_a_note(monkeypatch: pytest.MonkeyPatch) -> None:
    """render_page · fused: a screenshot over the cap keeps the DOM of its call; the task completes oversize_screenshot."""
    kept = RenderedPage("<p>kept</p>", 7000, 200, FINAL)
    api, browser = FakeApi([_tasks()]), FakeBrowser(shots=[ScreenshotOversize(9_000_000, 7000, page=kept)])

    report = _drain(monkeypatch, api, browser)

    assert _kinds(api) == ["html_snapshot"]
    assert b"<p>kept</p>" in api.uploads[0].content
    assert [body for _, body in api.named("complete")] == [{"note": "oversize_screenshot"}]
    assert (report.completed, report.failed) == (1, 0)


def test_a_failed_screenshot_upload_does_not_fail_the_task_and_is_logged(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """render_page · fused: the HTML stores, the screenshot upload answers 500; the task completes screenshot_failed."""
    api, browser = FakeApi([_tasks()]), FakeBrowser(shots=[shot()])
    api.upload_script = [201, 500]

    report = _drain(monkeypatch, api, browser)

    assert api.named("fail") == [] and [body for _, body in api.named("complete")] == [{"note": "screenshot_failed"}]
    assert report.completed == 1
    assert "screenshot upload failed" in capsys.readouterr().err


def test_an_unreadable_screenshot_keeps_the_html_and_completes_screenshot_failed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """render_page · fused: no readable image still keeps the DOM; the task completes screenshot_failed, uploads the HTML."""
    kept = RenderedPage("<p>kept</p>", 7000, 200, FINAL)
    broken = ScreenshotUnreadable("Cloudflare returned no readable image", ms_used=7000, page=kept)
    api, browser = FakeApi([_tasks()]), FakeBrowser(shots=[broken])

    _drain(monkeypatch, api, browser)

    assert _kinds(api) == ["html_snapshot"]
    assert [body for _, body in api.named("complete")] == [{"note": "screenshot_failed"}]


def test_the_fused_call_is_made_without_the_accept_script(monkeypatch: pytest.MonkeyPatch) -> None:
    """render_page · fused: the screenshot call asks for consent_click off, so no accept script is sent."""
    api, browser = FakeApi([_tasks()]), FakeBrowser(shots=[shot()])

    _drain(monkeypatch, api, browser)

    assert browser.shot_consent == [False]


def test_with_the_flag_off_the_render_stays_on_content_and_stores_no_screenshot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """render_page · flag off: the classic /content render uploads only the HTML and makes no screenshot call."""
    api, browser = FakeApi([_tasks()]), FakeBrowser(page())

    _drain(monkeypatch, api, browser, fused=False)

    assert browser.calls == [URL] and browser.shot_calls == []
    assert _kinds(api) == ["html_snapshot"]


def test_a_fused_page_without_html_fails_permanently_and_stores_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    """render_page · fused: a snapshot with no DOM cannot be stored, so the task fails permanently with no upload."""
    api, browser = FakeApi([_tasks()]), FakeBrowser(shots=[shot(html=None)])

    _drain(monkeypatch, api, browser)

    ((_, body),) = api.named("fail")
    assert body["retryable"] is False and "no HTML" in str(body["error"])
    assert api.uploads == []


def test_a_fused_call_error_fails_the_task_as_a_render_error_does(monkeypatch: pytest.MonkeyPatch) -> None:
    """render_page · fused: a 5xx from /snapshot is a retryable failure with nothing uploaded, as /content would be."""
    api, browser = FakeApi([_tasks()]), FakeBrowser(shots=[BrowserRequestError("HTTP 502", retryable=True)])

    report = _drain(monkeypatch, api, browser)

    ((_, body),) = api.named("fail")
    assert body["retryable"] is True and api.uploads == [] and report.failed == 1


def test_the_fused_flag_is_off_by_default_and_turns_on_from_the_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """render_page · RENDER_FUSED_SCREENSHOT is off when unset (the shipped default) and on only when set to true."""
    monkeypatch.delenv("RENDER_FUSED_SCREENSHOT", raising=False)
    assert load_browser_settings().render_fused_screenshot is False

    monkeypatch.setenv("RENDER_FUSED_SCREENSHOT", "true")
    assert load_browser_settings().render_fused_screenshot is True
