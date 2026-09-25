from __future__ import annotations

import re

import pytest
import sqlalchemy as sa
from app.models.taxonomy import CODE_PATTERN, Domain, LifeSituation, document_domain, document_life_situation
from scripts.seed_data.taxonomy import DOMAINS, SITUATIONS, Term, term_id
from scripts.seed_documents import ID_DOC_GEBURT, seed_mvp_graph
from scripts.seed_taxonomy import seed_taxonomy
from sqlalchemy.orm import Session

ALL_TERMS = DOMAINS + SITUATIONS
GERMAN_SLUGS = {"umzug", "wohnen", "geburt", "heirat", "fahrzeuge", "arbeit", "familie", "bildung"}


def _count(session: Session, table: sa.Table | type) -> int:
    return session.execute(sa.select(sa.func.count()).select_from(table)).scalar_one()


def _seeded(session: Session) -> Session:
    seed_mvp_graph(session)
    seed_taxonomy(session)
    session.flush()
    return session


def test_data_has_13_domains_and_18_situations() -> None:
    assert (len(DOMAINS), len(SITUATIONS)) == (13, 18)


@pytest.mark.parametrize("term", ALL_TERMS, ids=lambda t: t.code)
def test_every_term_has_non_empty_de_and_en(term: Term) -> None:
    for texts in (term.name_i18n, term.description_i18n):
        assert all(texts.get(locale, "").strip() for locale in ("de", "en"))


def test_codes_are_ascii_kebab_case_english() -> None:
    codes = [t.code for t in ALL_TERMS]

    assert all(re.fullmatch(CODE_PATTERN, c) for c in codes)
    assert not GERMAN_SLUGS & set(codes)
    assert len(set(codes)) == len(codes)


def test_term_ids_are_stable_across_imports() -> None:
    assert all(t.id == term_id(t.code) for t in ALL_TERMS)
    assert len({t.id for t in ALL_TERMS}) == len(ALL_TERMS)


def test_seed_creates_13_domains_and_18_situations(db_session: Session) -> None:
    _seeded(db_session)

    assert (_count(db_session, Domain), _count(db_session, LifeSituation)) == (13, 18)


def test_second_run_creates_no_duplicates(db_session: Session) -> None:
    _seeded(db_session)
    before = [_count(db_session, t) for t in (Domain, LifeSituation, document_domain, document_life_situation)]

    seed_taxonomy(db_session)
    db_session.flush()

    assert [_count(db_session, t) for t in (Domain, LifeSituation, document_domain, document_life_situation)] == before


def test_seed_tags_geburtsurkunde_with_birth_of_child(db_session: Session) -> None:
    _seeded(db_session)

    codes = db_session.execute(
        sa.select(LifeSituation.code)
        .join(document_life_situation, document_life_situation.c.life_situation_id == LifeSituation.id)
        .where(document_life_situation.c.document_id == ID_DOC_GEBURT)
    ).scalars()

    assert "birth-of-child" in set(codes)


def test_unknown_code_raises_before_writing(db_session: Session) -> None:
    seed_mvp_graph(db_session)

    with pytest.raises(ValueError, match="no-such-code"):
        seed_taxonomy(db_session, tags={ID_DOC_GEBURT: (("no-such-code",), ())})

    assert _count(db_session, Domain) == 0
