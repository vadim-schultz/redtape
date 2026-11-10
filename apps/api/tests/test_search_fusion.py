"""Reciprocal Rank Fusion, the keyword leg and the vector leg against a seeded database (chapter 8)."""

from __future__ import annotations

import uuid
from collections.abc import Sequence

import pytest
from app.features.search.fusion import fuse
from app.features.search.keyword import keyword_leg
from app.features.search.query import NormalisedQuery
from app.features.search.vector import vector_leg
from app.schema.search import SearchMode
from sqlalchemy import Float, Integer, Select, Uuid, cast, column, false, select, values
from sqlalchemy.orm import Session

from search_query_world import add_embedding, add_text, at_similarity, indexed, params, query_vector

A, B, C = (uuid.UUID(int=n) for n in (1, 2, 3))
K = 60


def leg(rows: Sequence[tuple[uuid.UUID, int, float | None]]) -> Select:
    """A leg with fixed rows ``(candidate_id, rank, cosine)``."""
    data = values(column("candidate_id", Uuid), column("rnk", Integer), column("cos", Float), name="leg")
    relation = data.data(list(rows))
    return select(relation.c.candidate_id, relation.c.rnk, cast(relation.c.cos, Float).label("cos"))


def fused(session: Session, legs: Sequence[Select], mode: SearchMode, **overrides: object) -> dict[uuid.UUID, tuple]:
    relation = fuse(legs, params(**overrides), mode)
    rows = session.execute(select(relation).order_by(relation.c.rrf.desc(), relation.c.candidate_id)).all()
    return {row.candidate_id: (row.rrf, row.cos, row.relevance) for row in rows}


def test_a_candidate_in_both_legs_outranks_one_in_a_single_leg(db_session: Session) -> None:
    keyword = leg([(A, 1, None), (B, 2, None)])
    vector = leg([(C, 1, 0.9), (A, 2, 0.8)])

    rows = fused(db_session, [keyword, vector], SearchMode.HYBRID)

    assert list(rows) == [A, C, B]
    assert rows[A][0] == pytest.approx(1 / (K + 1) + 1 / (K + 2))
    assert rows[C][0] == pytest.approx(1 / (K + 1))
    assert rows[B][0] == pytest.approx(1 / (K + 2))


def test_results_are_deduplicated_by_candidate_and_keep_the_cosine_of_the_vector_leg(db_session: Session) -> None:
    rows = fused(db_session, [leg([(A, 1, None), (B, 2, None)]), leg([(A, 1, 0.8), (C, 2, 0.6)])], SearchMode.HYBRID)

    assert sorted(rows) == [A, B, C]
    assert rows[A][1] == pytest.approx(0.8)
    assert rows[B][1] is None
    assert rows[C][1] == pytest.approx(0.6)


def test_relevance_is_the_rrf_over_the_best_possible_score_for_the_mode(db_session: Session) -> None:
    both = fused(db_session, [leg([(A, 1, None)]), leg([(A, 1, 0.9)])], SearchMode.HYBRID)
    one_of_two = fused(db_session, [leg([(A, 1, None)]), leg([(B, 1, 0.9)])], SearchMode.HYBRID)
    alone = fused(db_session, [leg([(A, 1, None), (B, 2, None)])], SearchMode.KEYWORD)

    assert both[A][2] == pytest.approx(1.0)
    assert one_of_two[A][2] == pytest.approx(0.5)
    assert alone[A][2] == pytest.approx(1.0)
    assert alone[B][2] == pytest.approx((K + 1) / (K + 2))


def test_the_fused_pool_is_capped_at_the_relevance_gate(db_session: Session) -> None:
    rows = fused(db_session, [leg([(A, 1, None), (B, 2, None), (C, 3, None)])], SearchMode.KEYWORD, fused_top_k=2)

    assert list(rows) == [A, B]


def test_a_fusion_without_any_hit_is_empty(db_session: Session) -> None:
    nothing = leg([(A, 1, None)]).where(false())

    assert fused(db_session, [nothing, nothing], SearchMode.HYBRID) == {}


def hits(session: Session, statement: Select) -> list[uuid.UUID]:
    return [row.candidate_id for row in session.execute(statement.order_by("rnk")).all()]


def keyword(text: str, locale: str = "de") -> Select:
    return keyword_leg(NormalisedQuery(text, locale), params(), None)


def test_keyword_leg_matches_inflected_german_words_through_the_german_configuration(db_session: Session) -> None:
    hit = indexed(db_session, "Antrag auf Kindergeld")
    indexed(db_session, "Wohnungsgeberbestaetigung")

    assert hits(db_session, keyword("anträge")) == [hit.id]


def test_keyword_leg_matches_stopwords_and_exact_terms_through_the_simple_vector(db_session: Session) -> None:
    hit = indexed(db_session, "Die Partei")

    assert hits(db_session, keyword("die")) == [hit.id]


def test_keyword_leg_keeps_the_title_substring_match_so_exact_titles_do_not_regress(db_session: Session) -> None:
    hit = indexed(db_session, "Kindergeldantrag")

    assert hits(db_session, keyword("kinder")) == [hit.id]


def test_keyword_leg_ranks_a_text_match_with_the_title_match_first(db_session: Session) -> None:
    title = indexed(db_session, "Meldebescheinigung")
    excerpt = indexed(db_session, "Nachweis", "Bitte die Meldebescheinigung mitbringen")

    assert hits(db_session, keyword("meldebescheinigung")) == [title.id, excerpt.id]


def test_keyword_leg_searches_turkish_rows_with_the_turkish_configuration_and_german_rows_with_german(
    db_session: Session,
) -> None:
    german = indexed(db_session, "Wohnungsanmeldung")
    turkish = indexed(db_session, "Meldebescheinigung")
    add_text(db_session, turkish, "tr", "Kimlikler ve evrak")

    by_turkish = hits(db_session, keyword("kimlik", "tr"))
    by_german = hits(db_session, keyword("wohnungsanmeldungen", "tr"))

    assert by_turkish == [turkish.id]
    assert by_german == [german.id]


def test_keyword_leg_ignores_rows_of_locales_other_than_the_request_locale_and_german(db_session: Session) -> None:
    turkish = indexed(db_session, "Meldebescheinigung")
    add_text(db_session, turkish, "tr", "Kimlikler ve evrak")

    assert hits(db_session, keyword("kimlik", "de")) == []
    assert hits(db_session, keyword("kimlik", "en")) == []


def test_keyword_leg_lists_a_candidate_matching_in_two_rows_once(db_session: Session) -> None:
    both = indexed(db_session, "Meldebescheinigung")
    add_text(db_session, both, "tr", "Meldebescheinigung kimlikler")

    assert hits(db_session, keyword("meldebescheinigung", "tr")) == [both.id]


def test_keyword_leg_finds_nothing_for_a_nonsense_query(db_session: Session) -> None:
    indexed(db_session, "Antrag auf Kindergeld")

    assert hits(db_session, keyword("qzxwv")) == []


def test_keyword_leg_stays_within_the_scope(db_session: Session) -> None:
    kept = indexed(db_session, "Antrag auf Kindergeld")
    indexed(db_session, "Kindergeld Bescheid")

    scope = select(column("id", Uuid)).select_from(values(column("id", Uuid), name="s").data([(kept.id,)]))
    scoped = keyword_leg(NormalisedQuery("kindergeld", "de"), params(), scope)

    assert hits(db_session, scoped) == [kept.id]


def test_keyword_leg_returns_at_most_top_n(db_session: Session) -> None:
    for number in range(4):
        indexed(db_session, f"Kindergeld Antrag {number}")

    limited = keyword_leg(NormalisedQuery("kindergeld", "de"), params(top_n=3), None)

    assert len(hits(db_session, limited)) == 3


def vector(locale: str = "de", **overrides: object) -> Select:
    return vector_leg(query_vector(), locale, params(**overrides), None)


def test_vector_leg_orders_by_cosine_and_reports_it(db_session: Session) -> None:
    near = indexed(db_session, "Near", similarity=0.9)
    far = indexed(db_session, "Far", similarity=0.5)

    rows = db_session.execute(vector().order_by("rnk")).all()

    assert [row.candidate_id for row in rows] == [near.id, far.id]
    assert [row.cos for row in rows] == [pytest.approx(0.9, abs=2e-3), pytest.approx(0.5, abs=2e-3)]


def test_vector_leg_drops_results_below_the_cut_off(db_session: Session) -> None:
    kept = indexed(db_session, "Kept", similarity=0.6)
    indexed(db_session, "Nonsense", similarity=0.1)

    assert hits(db_session, vector(min_similarity=0.3)) == [kept.id]
    assert hits(db_session, vector(min_similarity=0.7)) == []


def test_vector_leg_reads_only_the_configured_model(db_session: Session) -> None:
    other = indexed(db_session, "Other model")
    add_embedding(db_session, other, at_similarity(0.9), model="some-other-model")

    assert hits(db_session, vector()) == []


def test_vector_leg_searches_the_request_locale_and_german_and_the_best_row_wins(db_session: Session) -> None:
    both = indexed(db_session, "Both", similarity=0.5)
    add_embedding(db_session, both, at_similarity(0.8), locale="tr")
    polish = indexed(db_session, "Polish", similarity=None)
    add_embedding(db_session, polish, at_similarity(0.9), locale="pl")

    turkish = db_session.execute(vector("tr")).all()
    german = db_session.execute(vector("de")).all()

    assert [row.candidate_id for row in turkish] == [both.id]
    assert turkish[0].cos == pytest.approx(0.8, abs=2e-3)
    assert [row.cos for row in german] == [pytest.approx(0.5, abs=2e-3)]


def test_vector_leg_stays_within_the_scope_and_top_n(db_session: Session) -> None:
    kept = indexed(db_session, "Kept", similarity=0.9)
    indexed(db_session, "Dropped", similarity=0.8)
    indexed(db_session, "Also dropped", similarity=0.7)
    scope = select(column("id", Uuid)).select_from(values(column("id", Uuid), name="s").data([(kept.id,)]))

    assert hits(db_session, vector_leg(query_vector(), "de", params(), scope)) == [kept.id]
    assert len(hits(db_session, vector(top_n=2))) == 2
