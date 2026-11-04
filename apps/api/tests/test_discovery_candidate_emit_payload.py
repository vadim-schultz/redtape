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


def test_the_payload_adds_the_url_and_canonical_codes_that_exist() -> None:
    payload = new_document_payload(_candidate("https://example.gov/a"), SuggestedTags(["housing"], ["moving-house"]))

    assert payload == {
        "title_i18n": {"de": "Personalausweis"},
        "official_url": "https://example.gov/a",
        "category_codes": ["home-and-housing", "moving-house"],
    }


def test_the_default_tag_hook_suggests_no_codes_for_a_candidate_without_mentions(db_session: Session) -> None:
    assert suggested_tags(db_session, _candidate()) == SuggestedTags([], [], {})


def test_the_payload_adds_tag_confidence_when_it_has_any() -> None:
    tags = SuggestedTags(["housing"], ["moving-house"], {"housing": 0.85, "moving-house": 0.5})

    payload = new_document_payload(_candidate("https://example.gov/a"), tags)

    assert payload["tag_confidence"] == {"home-and-housing": 0.85, "moving-house": 0.5}


def test_suggested_tags_confidence_only_covers_usable_categories(db_session: Session) -> None:
    """Every usable category gets its combined score."""
    procs = world.procedures(db_session, 2)
    subject = world.candidate(db_session, procs[0], "subject")
    world.mentioned(
        db_session,
        subject,
        procs,
        [world.Row(0, ["housing"], ["moving-house"]), world.Row(1, ["housing"], ["other"])],
    )

    tags = suggested_tags(db_session, subject)

    assert tags.category_codes == ["home-and-housing", "moving-house"]
    assert set(tags.tag_confidence) == {"home-and-housing", "moving-house"}
    assert all(0 < score <= 1 for score in tags.tag_confidence.values())
    assert tags.situation_leaf_codes == {}


def test_suggested_tags_carries_the_pvog_leaf_code_of_a_usable_category(db_session: Session) -> None:
    procs = world.procedures(db_session, 1)
    subject = world.candidate(db_session, procs[0], "subject")
    world.mentioned(
        db_session,
        subject,
        procs,
        [world.Row(0, ["moving-house", "renting-home"], None, "pvog", 0.65, None, "1050200")],
    )

    tags = suggested_tags(db_session, subject)

    assert tags.category_codes == ["moving-house", "renting-home"]
    assert tags.situation_leaf_codes == {"moving-house": "1050200", "renting-home": "1050200"}


def test_suggested_tags_omits_the_leaf_code_of_a_code_that_does_not_clear_the_inclusion_floor(
    db_session: Session,
) -> None:
    """A leaf code only ever accompanies a usable situation code — never one the floor already dropped."""
    many_procs = world.procedures(db_session, 11)
    subject = world.candidate(db_session, many_procs[0], "subject")
    thin_mention = world.Row(0, None, ["thin"])
    pvog_mention = world.Row(1, ["moving-house"], None, "pvog", 0.95, None, "1050100")
    others = [world.Row(i, None, ["other"]) for i in range(2, 11)]
    world.mentioned(db_session, subject, many_procs, [thin_mention, pvog_mention, *others])

    tags = suggested_tags(db_session, subject)

    assert "thin" not in tags.category_codes
    assert tags.situation_leaf_codes == {"moving-house": "1050100"}


def test_the_payload_adds_pvog_leaf_codes_when_it_has_any() -> None:
    tags = SuggestedTags(
        [],
        [],
        {"moving-house": 0.95},
        {"moving-house": "1050100"},
        ["moving-house"],
    )

    payload = new_document_payload(_candidate("https://example.gov/a"), tags)

    assert payload["pvog_leaf_codes"] == {"moving-house": "1050100"}
