"""extract_page handler: read a stored snapshot, run the extractor, record mentions (chapter 17, Loop B)."""

from __future__ import annotations

import uuid

import pytest
from discovery_ingest.extract.base import PageContext
from discovery_ingest.mentions import MentionItem
from discovery_ingest.schemas import DrainReport
from discovery_ingest.worker.drain import run_worker_drain
from discovery_ingest.worker.policy import DrainPolicy

from extract_fakes import ARTIFACT_ID, PAGE_URL, ExtractApi, FakeExtractor, extract_task, mention
from render_fakes import robots_fetcher


def _drain(monkeypatch: pytest.MonkeyPatch, api: ExtractApi, *extractors: FakeExtractor) -> DrainReport:
    policy = DrainPolicy(max_tasks=5, kinds=("extract_page",))
    return run_worker_drain(api.client(monkeypatch), robots_fetcher(), policy, extractors=extractors)


def _two_mentions(html: str, ctx: PageContext) -> list[MentionItem]:
    return [mention(ctx, "Meldebescheinigung"), mention(ctx, "Geburtsurkunde")]


def test_extract_page_posts_mentions_with_the_artifact_id_and_completes(monkeypatch: pytest.MonkeyPatch) -> None:
    """extract_page · decodes the snapshot, runs the extractor, posts its mentions with the artifact id, completes."""
    body = "<p>Bürger</p>".encode("iso-8859-1")
    api = ExtractApi([extract_task()], body, "text/html; charset=iso-8859-1")
    extractor = FakeExtractor(produce=_two_mentions)

    report = _drain(monkeypatch, api, extractor)

    html, ctx = extractor.pages[0]
    assert (html, ctx.artifact_id, ctx.source_url) == ("<p>Bürger</p>", ARTIFACT_ID, PAGE_URL)
    posted = [item for batch in api.mention_posts for item in batch]
    assert [item["title_i18n"] for item in posted] == [{"de": "Meldebescheinigung"}, {"de": "Geburtsurkunde"}]
    assert {item["artifact_id"] for item in posted} == {str(ARTIFACT_ID)}
    assert [body for _, body in api.named("complete")] == [None]
    assert (report.completed, report.failed) == (1, 0)


def test_extract_page_drops_mentions_that_fail_validation_and_posts_the_rest(monkeypatch: pytest.MonkeyPatch) -> None:
    """extract_page · an invalid mention is dropped; only the valid ones are posted."""

    def produce(html: str, ctx: PageContext) -> list[MentionItem]:
        broken = MentionItem.model_construct(**{**mention(ctx).model_dump(), "title_i18n": {}})
        return [broken, mention(ctx, "Geburtsurkunde")]

    api = ExtractApi([extract_task()])

    _drain(monkeypatch, api, FakeExtractor(produce=produce))

    assert [item["title_i18n"] for batch in api.mention_posts for item in batch] == [{"de": "Geburtsurkunde"}]
    assert [body for _, body in api.named("complete")] == [None]


def test_extract_page_completes_with_note_no_extractor_when_the_extractor_is_gone(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """extract_page · no extractor matches the page any more: complete with note no_extractor, post nothing."""
    api = ExtractApi([extract_task()])

    report = _drain(monkeypatch, api, FakeExtractor(host="elsewhere.example"))

    assert [body for _, body in api.named("complete")] == [{"note": "no_extractor"}]
    assert (api.mention_posts, report.completed, report.failed) == ([], 1, 0)


def test_extract_page_completes_with_note_no_mentions_when_the_page_yields_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """extract_page · an extractor that finds nothing is a normal outcome: note no_mentions, nothing posted."""
    api = ExtractApi([extract_task()])

    report = _drain(monkeypatch, api, FakeExtractor())

    assert [body for _, body in api.named("complete")] == [{"note": "no_mentions"}]
    assert (api.mention_posts, report.completed, report.failed) == ([], 1, 0)


def test_extract_page_fails_an_extractor_exception_without_retry_and_names_the_extractor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """extract_page · an extractor that raises fails the task permanently, naming extractor id and version."""

    def explode(html: str, ctx: PageContext) -> list[MentionItem]:
        raise ValueError("markup changed")

    api = ExtractApi([extract_task()])

    report = _drain(monkeypatch, api, FakeExtractor("verwaltung-bund", "3", produce=explode))

    ((_, failure),) = api.named("fail")
    assert failure["retryable"] is False
    assert "verwaltung-bund@3" in failure["error"] and "markup changed" in failure["error"]
    assert (api.mention_posts, api.named("complete"), report.failed) == ([], [], 1)


@pytest.mark.parametrize(("status", "retryable"), [(500, True), (503, True), (404, False)])
def test_extract_page_fails_retryably_only_when_the_content_route_has_a_server_error(
    monkeypatch: pytest.MonkeyPatch, status: int, retryable: bool
) -> None:
    """extract_page · a 5xx from the content route is retryable; a 404 (unknown artifact) is permanent."""
    api = ExtractApi([extract_task()])
    api.content_status = status
    extractor = FakeExtractor(produce=_two_mentions)

    report = _drain(monkeypatch, api, extractor)

    ((_, failure),) = api.named("fail")
    assert failure["retryable"] is retryable
    assert (extractor.pages, api.mention_posts, report.failed) == ([], [], 1)


def test_extract_page_fails_permanently_when_the_task_has_no_artifact(monkeypatch: pytest.MonkeyPatch) -> None:
    """extract_page · a task without an artifact id cannot be read: permanent failure, no content request."""
    api = ExtractApi([extract_task(artifact_id=None)])

    _drain(monkeypatch, api, FakeExtractor(produce=_two_mentions))

    ((_, failure),) = api.named("fail")
    assert failure["retryable"] is False and "artifact" in failure["error"]
    assert api.mention_posts == []
