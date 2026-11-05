"""Build the ``new_document`` suggestion body of a candidate (chapter 11, loop B), category-only."""

from __future__ import annotations

import uuid

from app.features.discovery.candidate_emit_payload import SuggestedTags, new_document_payload, suggested_tags
from app.models.discovery import DiscoveryDocumentCandidate
from sqlalchemy.orm import Session

import completeness_world as world

EMPTY = SuggestedTags([], {}, {})


def _candidate(official_url: str | None = None) -> DiscoveryDocumentCandidate:
    return DiscoveryDocumentCandidate(
        id=uuid.uuid4(),
        jurisdiction_id=uuid.uuid4(),
        key="personalausweis",
        title_i18n={"de": "Personalausweis"},
        official_url=official_url,
    )


def test_the_payload_has_a_title_and_omits_everything_the_candidate_lacks() -> None:
    payload = new_document_payload(_candidate(), EMPTY)

    assert payload == {"title_i18n": {"de": "Personalausweis"}}


def test_the_payload_adds_the_url_and_canonical_categories_that_exist() -> None:
    tags = SuggestedTags(["home-and-housing", "moving-house"], {}, {})

    payload = new_document_payload(_candidate("https://example.gov/a"), tags)

    assert payload == {
        "title_i18n": {"de": "Personalausweis"},
        "official_url": "https://example.gov/a",
        "category_codes": ["home-and-housing", "moving-house"],
    }


def test_the_default_tag_hook_suggests_no_codes_for_a_candidate_without_mentions(db_session: Session) -> None:
    assert suggested_tags(db_session, _candidate()) == EMPTY


def test_the_payload_adds_tag_confidence_when_it_has_any() -> None:
    tags = SuggestedTags(["home-and-housing", "moving-house"], {"home-and-housing": 0.85, "moving-house": 0.5}, {})

    payload = new_document_payload(_candidate("https://example.gov/a"), tags)

    assert payload["tag_confidence"] == {"home-and-housing": 0.85, "moving-house": 0.5}


def test_suggested_tags_confidence_covers_exactly_the_usable_categories(db_session: Session) -> None:
    """Every usable category gets its combined score; the list and the scores name the same codes."""
    procs = world.procedures(db_session, 2)
    subject = world.candidate(db_session, procs[0], "subject")
    world.mentioned(
        db_session,
        subject,
        procs,
        [world.Row(0, ["home-and-housing", "moving-house"]), world.Row(1, ["home-and-housing"])],
    )

    tags = suggested_tags(db_session, subject)

    assert set(tags.category_codes) == {"home-and-housing", "moving-house"}
    assert set(tags.tag_confidence) == set(tags.category_codes)
    assert all(0 < score <= 1 for score in tags.tag_confidence.values())


def test_suggested_tags_carries_the_pvog_leaf_code_of_a_usable_category(db_session: Session) -> None:
    procs = world.procedures(db_session, 1)
    subject = world.candidate(db_session, procs[0], "subject")
    world.mentioned(
        db_session,
        subject,
        procs,
        [world.Row(0, ["moving-house", "renting-home"], "pvog", 0.65, "1050200")],
    )

    tags = suggested_tags(db_session, subject)

    assert set(tags.category_codes) == {"moving-house", "renting-home"}
    assert tags.pvog_leaf_codes == {"moving-house": "1050200", "renting-home": "1050200"}


def test_suggested_tags_omits_the_leaf_code_of_a_code_that_does_not_clear_the_inclusion_floor(
    db_session: Session,
) -> None:
    """A leaf code only ever accompanies a usable category, never one the inclusion floor already dropped."""
    many_procs = world.procedures(db_session, 11)
    subject = world.candidate(db_session, many_procs[0], "subject")
    thin_mention = world.Row(0, ["retirement"])
    pvog_mention = world.Row(1, ["moving-house"], "pvog", 0.95, "1050100")
    others = [world.Row(index, ["birth-and-parenthood"]) for index in range(2, 11)]
    world.mentioned(db_session, subject, many_procs, [thin_mention, pvog_mention, *others])

    tags = suggested_tags(db_session, subject)

    assert "retirement" not in tags.category_codes
    assert tags.pvog_leaf_codes == {"moving-house": "1050100"}


def test_the_payload_adds_pvog_leaf_codes_when_it_has_any() -> None:
    tags = SuggestedTags(["moving-house"], {"moving-house": 0.95}, {"moving-house": "1050100"})

    payload = new_document_payload(_candidate("https://example.gov/a"), tags)

    assert payload["pvog_leaf_codes"] == {"moving-house": "1050100"}
