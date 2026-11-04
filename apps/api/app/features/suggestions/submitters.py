"""Who submits a suggestion: a human user or a crawler API key, each owning its own rules."""

from __future__ import annotations

from dataclasses import dataclass
from typing import NamedTuple, Protocol
from uuid import UUID

from app.features.suggestions.repository import SuggestionRepository
from app.models.suggestion import Suggestion, SuggestionSource


class MissingSourceUrlError(ValueError):
    """Raised when a crawler-submitted suggestion has no source_url (D9)."""


class EventActor(NamedTuple):
    """The actor columns of a suggestion event: at most one of the two is set."""

    user_id: UUID | None
    api_key_id: UUID | None


class Submitter(Protocol):
    """The submitter contract `SuggestionService` depends on instead of a kind switch."""

    @property
    def source_type(self) -> SuggestionSource:
        """How the stored suggestion is labelled."""
        ...

    def row_fields(self) -> dict[str, UUID]:
        """Return the submitter column of a new suggestion row, keyed by column name."""
        ...

    def find_replay(self, repo: SuggestionRepository, idempotency_key: str | None) -> Suggestion | None:
        """Return the suggestion an earlier submission with this key created, if this submitter may replay."""
        ...

    def check_source_url(self, source_url: str | None) -> None:
        """Raise when the submitter must supply a source URL and did not."""
        ...

    def stored_idempotency_key(self, idempotency_key: str | None) -> str | None:
        """Return the idempotency key to persist on the row, or None when keys are not kept."""
        ...

    def event_actor(self) -> EventActor:
        """Return the actor to record on the submitted event."""
        ...


@dataclass(frozen=True)
class HumanSubmitter:
    """A signed-in user; their idempotency header is ignored (D8) and a source URL is optional."""

    user_id: UUID

    @property
    def source_type(self) -> SuggestionSource:
        """Human submissions are labelled `human`."""
        return SuggestionSource.HUMAN

    def row_fields(self) -> dict[str, UUID]:
        """Store the user as the submitter."""
        return {"submitted_by_user_id": self.user_id}

    def find_replay(self, repo: SuggestionRepository, idempotency_key: str | None) -> Suggestion | None:
        """Never replay: a human's idempotency key is ignored."""
        return None

    def check_source_url(self, source_url: str | None) -> None:
        """Accept a missing source URL."""

    def stored_idempotency_key(self, idempotency_key: str | None) -> str | None:
        """Do not keep a human's idempotency key."""
        return None

    def event_actor(self) -> EventActor:
        """Record the user as the actor."""
        return EventActor(user_id=self.user_id, api_key_id=None)


@dataclass(frozen=True)
class CrawlerSubmitter:
    """A crawler authenticated by API key; its idempotency keys replay and it must cite a source URL."""

    api_key_id: UUID

    @property
    def source_type(self) -> SuggestionSource:
        """Crawler submissions are labelled `crawler`."""
        return SuggestionSource.CRAWLER

    def row_fields(self) -> dict[str, UUID]:
        """Store the API key as the submitter."""
        return {"submitted_by_api_key_id": self.api_key_id}

    def find_replay(self, repo: SuggestionRepository, idempotency_key: str | None) -> Suggestion | None:
        """Return this key's earlier suggestion, if the submission carried a key."""
        if idempotency_key is None:
            return None
        return repo.get_by_idempotency_key(api_key_id=self.api_key_id, idempotency_key=idempotency_key)

    def check_source_url(self, source_url: str | None) -> None:
        """Require a source URL (D9)."""
        if source_url is None:
            raise MissingSourceUrlError("source_url is required for crawler submissions")

    def stored_idempotency_key(self, idempotency_key: str | None) -> str | None:
        """Keep the key so a retry can find this row."""
        return idempotency_key

    def event_actor(self) -> EventActor:
        """Record the API key as the actor."""
        return EventActor(user_id=None, api_key_id=self.api_key_id)
