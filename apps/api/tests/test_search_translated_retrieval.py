"""A query in a translated language finds a candidate through its translated row and vector (chapter 16)."""

from __future__ import annotations

from app.features.search.vector import vector_leg
from app.models.discovery import DiscoveryDocumentCandidate
from sqlalchemy.orm import Session

from search_locale_support import keyword_hits, payload
from search_query_world import add_embedding, at_similarity, params, query_vector
from search_support import make_candidate, search_service


def _vector_hits(session: Session, locale: str) -> list[object]:
    leg = vector_leg(query_vector(), locale, params(), None)
    return [row.candidate_id for row in session.execute(leg.order_by("rnk")).all()]


def _candidate(session: Session, locale: str, title: str, description: str) -> DiscoveryDocumentCandidate:
    candidate = make_candidate(session, "Wohnungsanmeldung")
    search_service(session).refresh(candidate.id)
    search_service(session).refresh_locale(candidate.id, locale, payload(locale, title, description))
    return candidate


def test_a_turkish_query_finds_a_candidate_through_its_turkish_row_and_its_tr_vector(db_session: Session) -> None:
    candidate = _candidate(db_session, "tr", "Çocuk parası başvurusu", "Kimlikler ve evrak getirin")
    other = make_candidate(db_session, "Wohngeld")
    search_service(db_session).refresh(other.id)
    add_embedding(db_session, candidate, at_similarity(0.9), locale="tr")

    assert keyword_hits(db_session, "kimlik", "tr") == [candidate.id]
    assert _vector_hits(db_session, "tr") == [candidate.id]


def test_a_german_term_query_still_finds_the_german_row_and_other_readers_do_not_see_the_turkish_row(
    db_session: Session,
) -> None:
    candidate = _candidate(db_session, "tr", "Çocuk parası başvurusu", "Kimlikler ve evrak getirin")
    add_embedding(db_session, candidate, at_similarity(0.9), locale="tr")

    assert keyword_hits(db_session, "wohnungsanmeldungen", "tr") == [candidate.id]
    assert keyword_hits(db_session, "kimlik", "ru") == []
    assert _vector_hits(db_session, "ru") == []


def test_polish_uses_the_simple_configuration_and_matches_exact_word_forms_only(db_session: Session) -> None:
    candidate = _candidate(db_session, "pl", "Zaświadczenie o zameldowaniu", "Dowód osobisty")

    assert keyword_hits(db_session, "zameldowaniu", "pl") == [candidate.id]
    assert keyword_hits(db_session, "zameldowanie", "pl") == []


def test_ukrainian_uses_the_simple_configuration_and_matches_exact_word_forms_only(db_session: Session) -> None:
    candidate = _candidate(db_session, "uk", "Довідка про реєстрацію", "Паспорт")

    assert keyword_hits(db_session, "реєстрацію", "uk") == [candidate.id]
    assert keyword_hits(db_session, "реєстрація", "uk") == []
