"""Build the ``new_document`` suggestion body of a candidate (chapter 11, loop B)."""

from __future__ import annotations

import uuid

from app.features.discovery.candidate_emit_payload import SuggestedTags, new_document_payload, suggested_tags
from app.models.discovery import DiscoveryDocumentCandidate
from sqlalchemy.orm import Session

import completeness_world as world


def _candidate(official_url: str | None = None) -> DiscoveryDocumentCandidate:
    return DiscoveryDocumentCandidate(
        id=uuid.uuid4(),
        jurisdiction_id=uuid.uuid4(),
        key="personalausweis",
        title_i18n={"de": "Personalausweis"},
        official_url=official_url,
    )


def test_the_payload_has_a_title_and_omits_everything_the_candidate_lacks() -> None:
    payload = new_document_payload(_candidate(), SuggestedTags([], []))

    assert payload == {"title_i18n": {"de": "Personalausweis"}}


def test_the_payload_adds_the_url_and_the_codes_that_exist() -> None:
    payload = new_document_payload(_candidate("https://example.gov/a"), SuggestedTags(["housing"], ["moving-house"]))

    assert payload == {
        "title_i18n": {"de": "Personalausweis"},
        "official_url": "https://example.gov/a",
        "domain_codes": ["housing"],
        "situation_codes": ["moving-house"],
    }


def test_the_default_tag_hook_suggests_no_codes_for_a_candidate_without_mentions(db_session: Session) -> None:
    assert suggested_tags(db_session, _candidate()) == SuggestedTags([], [], {})


def test_the_payload_adds_tag_confidence_when_it_has_any() -> None:
    tags = SuggestedTags(["housing"], ["moving-house"], {"housing": "high", "moving-house": "low"})

    payload = new_document_payload(_candidate("https://example.gov/a"), tags)

    assert payload["tag_confidence"] == {"housing": "high", "moving-house": "low"}


def test_suggested_tags_confidence_only_covers_accepted_codes_per_axis(db_session: Session) -> None:
    """A two-procedure domain code clears the strict floor (high); a situation code accepted only via
    the relaxed one-procedure rule, with a tagged procedure that disagrees, stays low — the regression
    this chapter exists to make visible.
    """
    procs = world.procedures(db_session, 2)
    subject = world.candidate(db_session, procs[0], "subject")
    world.mentioned(
        db_session,
        subject,
        procs,
        [world.Row(0, ["housing"], ["moving-house"]), world.Row(1, ["housing"], ["other"])],
    )

    tags = suggested_tags(db_session, subject)

    assert tags.domain_codes == ["housing"]
    assert tags.situation_codes == ["moving-house", "other"]
    assert tags.tag_confidence == {"housing": "high", "moving-house": "low", "other": "low"}
