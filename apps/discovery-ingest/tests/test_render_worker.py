"""render_page handler: snapshot upload, login walls, limits that release instead of fail (chapter 15, Loop B)."""

from __future__ import annotations

import uuid

import pytest
from discovery_ingest.artifacts import ArtifactRead
from discovery_ingest.browser.errors import BrowserAuthError, BrowserError, BrowserQuotaExceeded, BrowserRequestError
from discovery_ingest.schemas import ClaimedTask, DrainReport
from discovery_ingest.worker.drain import run_worker_drain
from discovery_ingest.worker.policy import DrainPolicy

from render_fakes import FakeApi, FakeBrowser, page, robots_fetcher, task_json

URL = "https://portal.example/service/1"
MAX_SNAPSHOT_BYTES = 4 * 1024 * 1024


def _tasks(count: int, url: str = URL) -> list[dict[str, object]]:
    return [task_json(uuid.uuid4(), url) for _ in range(count)]


def _drain(
    monkeypatch: pytest.MonkeyPatch,
    api: FakeApi,
    browser: FakeBrowser,
    *,
    budget_seconds: float = 480.0,
    robots: str | None = None,
    hook: list[tuple[ClaimedTask, ArtifactRead]] | None = None,
) -> DrainReport:
    after = (lambda task, artifact: hook.append((task, artifact))) if hook is not None else None
    policy = DrainPolicy(max_tasks=5, kinds=("render_page",), browser_budget_seconds=budget_seconds)
    return run_worker_drain(
        api.client(monkeypatch), robots_fetcher(robots), policy, browser=browser, after_snapshot=after
    )


def test_render_page_uploads_the_rendered_html_as_a_snapshot_and_completes(monkeypatch: pytest.MonkeyPatch) -> None:
    """render_page · uploads the rendered DOM as html_snapshot with source and final url, then completes."""
    api = FakeApi([_tasks(1)])

    report = _drain(monkeypatch, api, FakeBrowser(page("<p>Bürger</p>", ms=2500)))

    upload = api.uploads[0].content.decode()
    for part in ('name="kind"', "html_snapshot", URL, "https://portal.example/final", "<p>Bürger</p>", "fetched_at"):
        assert part in upload
    assert [body for _, body in api.named("complete")] == [None]
    assert (report.completed, report.failed, report.browser_seconds_used, report.stop_reason) == (
        1,
        0,
        2.5,
        "batch_limit",
    )


@pytest.mark.parametrize(
    ("task_url", "html"),
    [
        (URL, '<form><input type="password" name="p"></form>'),
        (URL, '<form><INPUT TYPE="Password"></form>'),
    ],
)
def test_render_page_completes_with_login_wall_when_the_page_asks_for_a_password(
    monkeypatch: pytest.MonkeyPatch, task_url: str, html: str
) -> None:
    """render_page · a password input completes with note login_wall and uploads nothing."""
    api = FakeApi([_tasks(1, task_url)])

    report = _drain(monkeypatch, api, FakeBrowser(page(html)))

    assert [body for _, body in api.named("complete")] == [{"note": "login_wall"}]
    assert api.uploads == [] and report.completed == 1


@pytest.mark.parametrize(
    "login_url", ["https://sso.example/realms/x/openid-connect/auth", "https://portal.example/Account/Login"]
)
def test_render_page_skips_a_login_url_without_calling_the_browser_and_keeps_a_normal_page(
    monkeypatch: pytest.MonkeyPatch, login_url: str
) -> None:
    """render_page · a login url costs no browser time; a similar-looking normal url is rendered."""
    api, browser = FakeApi([_tasks(1, login_url)]), FakeBrowser()

    _drain(monkeypatch, api, browser)

    assert browser.calls == [] and [body for _, body in api.named("complete")] == [{"note": "login_wall"}]

    normal = FakeApi([_tasks(1, "https://portal.example/author/profile")])
    rendered = FakeBrowser(page())
    _drain(monkeypatch, normal, rendered)
    assert rendered.calls == ["https://portal.example/author/profile"] and len(normal.uploads) == 1


def test_render_page_treats_a_rendered_final_url_that_looks_like_login_as_a_login_wall(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """render_page · the page redirected to a sign-in url: login_wall, nothing uploaded."""
    api = FakeApi([_tasks(1)])
    redirected = page().__class__(
        html="<p>sign in</p>", ms=1000, http_status=200, final_url="https://idp.example/signin?x=1"
    )

    _drain(monkeypatch, api, FakeBrowser(redirected))

    assert [body for _, body in api.named("complete")] == [{"note": "login_wall"}] and api.uploads == []


def test_render_page_completes_with_oversize_and_uploads_nothing_above_the_cap(monkeypatch: pytest.MonkeyPatch) -> None:
    """render_page · a DOM over 4 MB completes with note oversize; exactly 4 MB is uploaded."""
    api = FakeApi([_tasks(1)])
    _drain(monkeypatch, api, FakeBrowser(page("x" * (MAX_SNAPSHOT_BYTES + 1))))
    assert [body for _, body in api.named("complete")] == [{"note": "oversize"}] and api.uploads == []

    exact = FakeApi([_tasks(1)])
    _drain(monkeypatch, exact, FakeBrowser(page("x" * MAX_SNAPSHOT_BYTES)))
    assert len(exact.uploads) == 1 and exact.named("complete") == [(exact.named("complete")[0][0], None)]


def test_render_page_fails_permanently_when_robots_disallows_and_never_calls_the_browser(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """render_page · robots.txt disallow is a permanent failure before any browser time is spent."""
    api, browser = FakeApi([_tasks(1)]), FakeBrowser()

    report = _drain(monkeypatch, api, browser, robots="User-agent: *\nDisallow: /")

    ((_, body),) = api.named("fail")
    assert body["retryable"] is False and "robots" in str(body["error"])
    assert browser.calls == [] and (report.failed, report.completed) == (1, 0)


def test_render_page_fails_retryably_when_robots_txt_is_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    """render_page · an unreadable robots.txt is a retryable failure, not a permanent one."""
    api, browser = FakeApi([_tasks(1)]), FakeBrowser()
    policy = DrainPolicy(max_tasks=5, kinds=("render_page",), browser_budget_seconds=480)

    run_worker_drain(api.client(monkeypatch), robots_fetcher(robots_status=500), policy, browser=browser)

    ((_, body),) = api.named("fail")
    assert body["retryable"] is True and browser.calls == []


def test_render_page_releases_the_task_and_stops_the_run_on_quota_exceeded(monkeypatch: pytest.MonkeyPatch) -> None:
    """render_page · a 429 releases the in-flight and the unstarted tasks, fails none, stops browser_quota."""
    tasks = _tasks(3)
    api = FakeApi([tasks])

    report = _drain(monkeypatch, api, FakeBrowser(BrowserQuotaExceeded("limit", 3600.0)))

    released = [task for task, _ in api.named("release")]
    assert released == [str(task["id"]) for task in tasks]
    assert all("browser_quota" in str(body["reason"]) for _, body in api.named("release"))
    assert api.named("fail") == [] and api.named("complete") == []
    assert (report.released, report.completed, report.stop_reason, report.succeeded) == (3, 0, "browser_quota", True)


def test_render_page_stops_with_browser_budget_before_calling_the_browser_once_the_budget_is_spent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """render_page · after the run budget is spent the next task is released unrendered; stop browser_budget."""
    api, browser = FakeApi([_tasks(3)]), FakeBrowser(page(ms=6000))

    report = _drain(monkeypatch, api, browser, budget_seconds=5.0)

    assert len(browser.calls) == 1 and len(api.named("release")) == 2
    assert (report.completed, report.released, report.stop_reason) == (1, 2, "browser_budget")
    assert report.browser_seconds_used == 6.0


@pytest.mark.parametrize(
    ("status", "detail", "reason"),
    [
        (503, "object store is not configured", "storage_unavailable"),
        (507, "object store byte cap reached", "storage_unavailable"),
        (507, '{"detail": "database_soft_limit"}', "db_limit"),
    ],
)
def test_an_upload_that_storage_or_the_database_refuses_releases_and_stops(
    monkeypatch: pytest.MonkeyPatch, status: int, detail: str, reason: str
) -> None:
    """render_page · upload 503, 507 and 507 database_soft_limit release every task and stop with the right reason."""
    api = FakeApi([_tasks(2)])
    api.upload_status, api.upload_detail = status, detail

    report = _drain(monkeypatch, api, FakeBrowser(page()))

    assert len(api.named("release")) == 2 and api.named("fail") == [] and api.named("complete") == []
    assert (report.stop_reason, report.released, report.succeeded) == (reason, 2, True)


def test_an_upload_413_or_415_is_a_programming_error_and_fails_the_task_permanently(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """render_page · 413 fails permanently; nothing is released."""
    api = FakeApi([_tasks(1)])
    api.upload_status, api.upload_detail = 413, "too large"

    report = _drain(monkeypatch, api, FakeBrowser(page()))

    ((_, body),) = api.named("fail")
    assert body["retryable"] is False and api.named("release") == [] and report.failed == 1


@pytest.mark.parametrize(
    ("outcome", "retryable"),
    [
        (BrowserRequestError("HTTP 502", retryable=True), True),
        (BrowserRequestError("HTTP 422 code 5006", retryable=False), False),
        (page(status=503), True),
        (page(status=404), False),
    ],
)
def test_render_page_fails_retryably_on_a_5xx_and_permanently_on_a_4xx(
    monkeypatch: pytest.MonkeyPatch, outcome: BrowserError | object, retryable: bool
) -> None:
    """render_page · browser or target 5xx is retryable, 4xx permanent; nothing is uploaded for either."""
    api = FakeApi([_tasks(1)])

    report = _drain(monkeypatch, api, FakeBrowser(outcome))  # type: ignore[arg-type]

    ((_, body),) = api.named("fail")
    assert body["retryable"] is retryable and api.uploads == [] and report.failed == 1


def test_after_snapshot_receives_the_artifact_once_and_not_when_nothing_was_stored(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """render_page · the hook gets the stored artifact exactly once; login wall and oversize never call it."""
    hook: list[tuple[ClaimedTask, ArtifactRead]] = []
    stored = _drain(monkeypatch, FakeApi([_tasks(1)]), FakeBrowser(page()), hook=hook)
    assert (
        len(hook) == 1 and hook[0][0].target_url == URL and hook[0][1].kind == "html_snapshot" and stored.completed == 1
    )

    skipped: list[tuple[ClaimedTask, ArtifactRead]] = []
    browser = FakeBrowser(page('<input type="password">'), page("x" * (MAX_SNAPSHOT_BYTES + 1)))
    _drain(monkeypatch, FakeApi([_tasks(2)]), browser, hook=skipped)
    assert skipped == []


def test_render_page_reserves_an_estimate_before_each_call_and_adjusts_to_the_measured_time(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """render_page · reserve 30 s before the call, adjust by ms_used minus 30 s after it."""
    api = FakeApi([_tasks(1)], ledger_remaining=100.0)

    _drain(monkeypatch, api, FakeBrowser(page(ms=12_000)))

    assert [body for _, body in api.named("reserve")] == [{"amount": 30.0}]
    assert [body for _, body in api.named("adjust")] == [{"delta": -18.0}]


def test_render_page_stops_when_the_ledger_has_less_left_than_the_run_budget_allows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """render_page · the shared day has 40 s left: the second reservation is denied and the run stops browser_budget."""
    api = FakeApi([_tasks(2)], ledger_remaining=40.0)

    report = _drain(monkeypatch, api, FakeBrowser(page(ms=36_000)))

    assert (report.completed, report.released, report.stop_reason) == (1, 1, "browser_budget")


def test_render_page_stops_before_claiming_when_the_day_is_already_exhausted(monkeypatch: pytest.MonkeyPatch) -> None:
    """render_page · an exhausted ledger day stops browser_budget with nothing claimed."""
    api = FakeApi([_tasks(2)])
    api.ledger_exhausted = True
    browser = FakeBrowser()

    report = _drain(monkeypatch, api, browser)

    assert api.batches and browser.calls == []
    assert (report.claimed, report.batches, report.stop_reason, report.succeeded) == (0, 0, "browser_budget", True)


def test_a_429_marks_the_day_exhausted_in_the_ledger(monkeypatch: pytest.MonkeyPatch) -> None:
    """render_page · quota exceeded calls /exhaust on the ledger."""
    api = FakeApi([_tasks(1)])

    _drain(monkeypatch, api, FakeBrowser(BrowserQuotaExceeded("limit")))

    assert len(api.named("exhaust")) == 1 and api.ledger_exhausted is True


def test_an_unreachable_ledger_falls_back_to_the_run_budget_and_is_reported(monkeypatch: pytest.MonkeyPatch) -> None:
    """render_page · ledger 503: the run continues on its own budget and says ledger_unavailable."""
    api = FakeApi([_tasks(2)], ledger_remaining=None)

    report = _drain(monkeypatch, api, FakeBrowser(page(ms=6000), page(ms=6000)), budget_seconds=10.0)

    assert report.completed == 2 and report.ledger_unavailable is True
    assert report.browser_seconds_used == 12.0


def test_a_rejected_token_releases_the_batch_and_fails_the_run(monkeypatch: pytest.MonkeyPatch) -> None:
    """render_page · BrowserAuthError is infrastructure: tasks released, stop error, run not succeeded."""
    api = FakeApi([_tasks(2)])

    report = _drain(monkeypatch, api, FakeBrowser(BrowserAuthError("token rejected")))

    assert len(api.named("release")) == 2 and api.named("fail") == []
    assert (report.stop_reason, report.succeeded, report.released) == ("error", False, 2)
    assert report.error is not None and "token" in report.error
