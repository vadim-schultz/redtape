"""capture_screenshot handler: evidence upload, guards, limits that release instead of fail (chapter 19, Loop B)."""

from __future__ import annotations

import uuid

import pytest
from discovery_ingest.browser.errors import (
    BrowserAuthError,
    BrowserError,
    BrowserQuotaExceeded,
    BrowserRequestError,
    ScreenshotOversize,
)
from discovery_ingest.browser.port import ScreenshotImage

from capture_fakes import FakeCamera, drain_captures, shot
from render_fakes import FakeApi, task_json

URL = "https://portal.example/service/1"


def _tasks(count: int, url: str = URL) -> list[dict[str, object]]:
    return [task_json(uuid.uuid4(), url, "capture_screenshot") for _ in range(count)]


def _completions(api: FakeApi) -> list[object]:
    return [body for _, body in api.named("complete")]


def test_capture_uploads_a_jpeg_screenshot_artifact_and_completes(monkeypatch: pytest.MonkeyPatch) -> None:
    """capture · uploads the image as a screenshot artifact with source and final url, books the time, completes."""
    api = FakeApi([_tasks(1)])

    done = drain_captures(monkeypatch, api, FakeCamera(shot(ms=2500)))

    upload = api.uploads[0].content.decode("latin-1")
    for part in ('name="kind"', "screenshot", "image/jpeg", URL, "https://portal.example/final", "fetched_at"):
        assert part in upload
    assert _completions(api) == [None] and api.named("fail") == []
    assert (done.tally.completed, done.tally.failed, done.spend.used_seconds) == (1, 0, 2.5)


@pytest.mark.parametrize("login_url", ["https://sso.example/realms/x/openid-connect/auth", "https://p.example/Login"])
def test_capture_completes_with_login_wall_for_a_login_url_without_calling_the_browser(
    monkeypatch: pytest.MonkeyPatch, login_url: str
) -> None:
    """capture · a login url costs no browser time; a similar-looking normal url is captured."""
    api, camera = FakeApi([_tasks(1, login_url)]), FakeCamera()

    drain_captures(monkeypatch, api, camera)

    assert camera.calls == [] and _completions(api) == [{"note": "login_wall"}] and api.uploads == []

    normal = FakeApi([_tasks(1, "https://portal.example/author/profile")])
    captured = FakeCamera(shot())
    drain_captures(monkeypatch, normal, captured)
    assert captured.calls == ["https://portal.example/author/profile"] and len(normal.uploads) == 1


@pytest.mark.parametrize(
    "login_shot",
    [
        shot('<form><input type="password" name="p"></form>'),
        shot('<form><INPUT TYPE="Password"></form>'),
        shot("<p>sign in</p>", final_url="https://idp.example/signin?x=1"),
    ],
    ids=["password", "password-upper-case", "final-url"],
)
def test_capture_completes_with_login_wall_and_uploads_nothing_when_the_captured_page_is_a_login_wall(
    monkeypatch: pytest.MonkeyPatch, login_shot: ScreenshotImage
) -> None:
    """capture · a password field in the captured DOM, or a login final url, completes with login_wall."""
    api = FakeApi([_tasks(1)])

    done = drain_captures(monkeypatch, api, FakeCamera(login_shot))

    assert _completions(api) == [{"note": "login_wall"}] and api.uploads == [] and done.tally.completed == 1


def test_capture_completes_with_oversize_and_uploads_nothing_for_an_image_over_8_mb(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """capture · an image over 8 MB completes with oversize, uploads nothing and still books its browser time."""
    api = FakeApi([_tasks(1)])

    done = drain_captures(monkeypatch, api, FakeCamera(ScreenshotOversize(9_000_000, 7000)))

    assert _completions(api) == [{"note": "oversize"}] and api.uploads == []
    assert (done.tally.completed, done.spend.used_seconds) == (1, 7.0)


def test_capture_fails_permanently_when_robots_txt_disallows(monkeypatch: pytest.MonkeyPatch) -> None:
    """capture · a robots.txt disallow is a permanent failure before any browser time is spent."""
    api, camera = FakeApi([_tasks(1)]), FakeCamera()

    done = drain_captures(monkeypatch, api, camera, robots="User-agent: *\nDisallow: /")

    ((_, body),) = api.named("fail")
    assert body["retryable"] is False and "robots" in str(body["error"])
    assert camera.calls == [] and (done.tally.failed, done.tally.completed) == (1, 0)


@pytest.mark.parametrize(
    ("outcome", "reason", "released"),
    [
        (BrowserQuotaExceeded("limit", 3600.0), "browser_quota", 3),
        (shot(ms=6000), "browser_budget", 2),
    ],
    ids=["quota", "budget"],
)
def test_capture_releases_the_task_and_stops_the_run_on_quota_or_a_spent_budget(
    monkeypatch: pytest.MonkeyPatch, outcome: ScreenshotImage | BrowserError, reason: str, released: int
) -> None:
    """capture · quota 429 or a spent run budget release this and every unstarted task; none fails."""
    tasks = _tasks(3)
    api = FakeApi([tasks])

    done = drain_captures(monkeypatch, api, FakeCamera(outcome), budget_seconds=5.0)

    assert done.batch.stop is not None and done.batch.stop.reason == reason
    assert [task for task, _ in api.named("release")] == [str(task["id"]) for task in tasks][-released:]
    assert api.named("fail") == [] and done.tally.released == released


@pytest.mark.parametrize(
    ("status", "detail", "reason"),
    [
        (503, "object store is not configured", "storage_unavailable"),
        (507, "object store byte cap reached", "storage_unavailable"),
        (507, '{"detail": "database_soft_limit"}', "db_limit"),
    ],
)
def test_capture_releases_the_batch_and_stops_when_storage_or_the_database_refuses_the_upload(
    monkeypatch: pytest.MonkeyPatch, status: int, detail: str, reason: str
) -> None:
    """capture · upload 503, 507 and 507 database_soft_limit release both tasks, no attempt is failed."""
    api = FakeApi([_tasks(2)])
    api.upload_status, api.upload_detail = status, detail

    done = drain_captures(monkeypatch, api, FakeCamera(shot()))

    assert done.batch.stop is not None and done.batch.stop.reason == reason
    assert len(api.named("release")) == 2 and api.named("fail") == [] and api.named("complete") == []


def test_capture_stops_the_run_with_an_error_when_the_browser_token_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """capture · a rejected Cloudflare token is infrastructure: release the batch and stop with error."""
    api = FakeApi([_tasks(2)])

    done = drain_captures(monkeypatch, api, FakeCamera(BrowserAuthError("HTTP 403")))

    assert done.batch.stop is not None and done.batch.stop.reason == "error"
    assert len(api.named("release")) == 2 and api.named("fail") == []


@pytest.mark.parametrize("retryable", [True, False])
def test_capture_fails_retryably_on_a_5xx_and_permanently_on_a_4xx_from_the_browser(
    monkeypatch: pytest.MonkeyPatch, retryable: bool
) -> None:
    """capture · the browser client's request error carries retryability into the task failure; nothing uploaded."""
    api = FakeApi([_tasks(1)])
    error: BrowserError = BrowserRequestError("Cloudflare HTTP 5xx or 4xx", retryable=retryable)

    done = drain_captures(monkeypatch, api, FakeCamera(error))

    ((_, body),) = api.named("fail")
    assert body["retryable"] is retryable and api.uploads == [] and done.tally.failed == 1


@pytest.mark.parametrize(("status", "retryable"), [(503, True), (404, False)])
def test_capture_fails_on_a_page_that_answered_with_an_error_status_and_uploads_nothing(
    monkeypatch: pytest.MonkeyPatch, status: int, retryable: bool
) -> None:
    """capture · meta.status 400 or higher is no evidence: 5xx retryable, 4xx permanent."""
    api = FakeApi([_tasks(1)])

    drain_captures(monkeypatch, api, FakeCamera(shot(status=status)))

    ((_, body),) = api.named("fail")
    assert body["retryable"] is retryable and str(status) in str(body["error"]) and api.uploads == []


def test_capture_still_works_when_the_client_returns_no_dom_or_final_url(monkeypatch: pytest.MonkeyPatch) -> None:
    """capture · without a DOM the url rule is the only guard: the image is uploaded with the task url as final url."""
    api = FakeApi([_tasks(1)])

    done = drain_captures(monkeypatch, api, FakeCamera(shot(html=None, status=None, final_url=None)))

    assert len(api.uploads) == 1 and _completions(api) == [None] and done.tally.completed == 1
