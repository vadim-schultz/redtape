"""Unit tests of the submitter kinds: each member of the submitter contract, per kind."""

from __future__ import annotations

import uuid
from typing import Any

import pytest
from app.features.suggestions.submitters import CrawlerSubmitter, HumanSubmitter, MissingSourceUrlError
from app.models.suggestion import SuggestionSource


class _FakeReplayRepo:
    """Records idempotency lookups and answers with a canned row."""

    def __init__(self, found: Any = None) -> None:
        self.found = found
        self.lookups: list[tuple[uuid.UUID, str]] = []

    def get_by_idempotency_key(self, *, api_key_id: uuid.UUID, idempotency_key: str) -> Any:
        self.lookups.append((api_key_id, idempotency_key))
        return self.found


def test_human_source_type_is_human() -> None:
    assert HumanSubmitter(uuid.uuid4()).source_type == SuggestionSource.HUMAN


def test_crawler_source_type_is_crawler() -> None:
    assert CrawlerSubmitter(uuid.uuid4()).source_type == SuggestionSource.CRAWLER


def test_human_row_fields_name_the_user_column() -> None:
    user_id = uuid.uuid4()

    assert HumanSubmitter(user_id).row_fields() == {"submitted_by_user_id": user_id}


def test_crawler_row_fields_name_the_api_key_column() -> None:
    api_key_id = uuid.uuid4()

    assert CrawlerSubmitter(api_key_id).row_fields() == {"submitted_by_api_key_id": api_key_id}


def test_human_find_replay_ignores_the_key_and_never_looks_up() -> None:
    repo = _FakeReplayRepo(found="existing")

    assert HumanSubmitter(uuid.uuid4()).find_replay(repo, "some-key") is None
    assert repo.lookups == []


def test_crawler_find_replay_looks_up_by_api_key_and_key() -> None:
    api_key_id = uuid.uuid4()
    repo = _FakeReplayRepo(found="existing")

    found = CrawlerSubmitter(api_key_id).find_replay(repo, "crawl-9")

    assert found == "existing"
    assert repo.lookups == [(api_key_id, "crawl-9")]


def test_crawler_find_replay_without_a_key_does_not_look_up() -> None:
    repo = _FakeReplayRepo(found="existing")

    assert CrawlerSubmitter(uuid.uuid4()).find_replay(repo, None) is None
    assert repo.lookups == []


def test_human_check_source_url_accepts_a_missing_url() -> None:
    HumanSubmitter(uuid.uuid4()).check_source_url(None)


def test_crawler_check_source_url_accepts_a_url() -> None:
    CrawlerSubmitter(uuid.uuid4()).check_source_url("https://example.gov/found-here")


def test_crawler_check_source_url_raises_when_the_url_is_missing() -> None:
    with pytest.raises(MissingSourceUrlError):
        CrawlerSubmitter(uuid.uuid4()).check_source_url(None)


def test_human_stored_idempotency_key_is_always_none() -> None:
    assert HumanSubmitter(uuid.uuid4()).stored_idempotency_key("ignored") is None


def test_crawler_stored_idempotency_key_is_the_key_it_was_given() -> None:
    assert CrawlerSubmitter(uuid.uuid4()).stored_idempotency_key("crawl-3") == "crawl-3"


def test_human_event_actor_is_the_user() -> None:
    user_id = uuid.uuid4()

    actor = HumanSubmitter(user_id).event_actor()

    assert (actor.user_id, actor.api_key_id) == (user_id, None)


def test_crawler_event_actor_is_the_api_key() -> None:
    api_key_id = uuid.uuid4()

    actor = CrawlerSubmitter(api_key_id).event_actor()

    assert (actor.user_id, actor.api_key_id) == (None, api_key_id)
