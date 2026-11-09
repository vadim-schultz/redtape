"""Retired pre-C9 repository tests; canonical link coverage lives in ``test_document_category_repository.py``."""

# ruff: noqa

from __future__ import annotations

import uuid

import pytest
from app.features.documents.repository import DocumentRepository
from app.models.document import Document
from app.models.jurisdiction import Jurisdiction, JurisdictionKind
from app.models.taxonomy import Category, document_category
from sqlalchemy import select
from sqlalchemy.orm import Session

pytestmark = pytest.mark.skip(
    reason="Historical pre-C9 repository tests target removed axis tables; canonical category coverage is separate."
)


@pytest.fixture
def jurisdiction(db_session: Session) -> Jurisdiction:
    row = Jurisdiction(kind=JurisdictionKind.COUNTRY, name_i18n={"en": "Testland"}, code=f"T{uuid.uuid4().hex[:8]}")
    db_session.add(row)
    db_session.flush()
    return row


def _term(db_session: Session, model: type[Domain] | type[LifeSituation], code: str) -> Domain | LifeSituation:
    row = model(code=code, name_i18n={"en": code})
    db_session.add(row)
    db_session.flush()
    return row


def _repo(db_session: Session) -> DocumentRepository:
    return DocumentRepository(db_session)


def test_add_without_scores_links_nothing(db_session: Session, jurisdiction: Jurisdiction) -> None:
    repo = _repo(db_session)
    document = repo.add(Document(jurisdiction_id=jurisdiction.id, slug="no-tags"))

    confidence = repo.get_tag_confidence(document.id)

    assert (confidence.domains, confidence.life_situations) == ({}, {})


def test_add_writes_resolved_canonical_category_scores(db_session: Session, jurisdiction: Jurisdiction) -> None:
    """Repository · write canonical category links when category codes are resolved upstream."""
    db_session.add(Category(code="home-and-housing", name_i18n={"en": "Home & housing"}))
    db_session.flush()
    repo = _repo(db_session)

    document = repo.add(
        Document(jurisdiction_id=jurisdiction.id, slug="canonical-tagged"),
        category_scores={"home-and-housing": 0.84},
    )

    row = db_session.execute(
        select(document_category.c.confidence, document_category.c.source).where(
            document_category.c.document_id == document.id
        )
    ).one()
    assert row[0] == pytest.approx(0.84)
    assert row[1] == "promotion"


def test_add_rejects_an_unknown_canonical_category_code(db_session: Session, jurisdiction: Jurisdiction) -> None:
    """Repository · reject unknown canonical category codes instead of silently dropping them."""
    repo = _repo(db_session)

    with pytest.raises(ValueError, match="Unknown category code"):
        repo.add(
            Document(jurisdiction_id=jurisdiction.id, slug="invalid-canonical-tag"),
            category_scores={"does-not-exist": 0.84},
        )


def test_add_writes_the_given_confidence_per_term_id(db_session: Session, jurisdiction: Jurisdiction) -> None:
    repo = _repo(db_session)
    domain = _term(db_session, Domain, "housing")
    situation = _term(db_session, LifeSituation, "moving-house")

    document = repo.add(
        Document(jurisdiction_id=jurisdiction.id, slug="tagged"),
        domain_scores={domain.id: 0.73},
        situation_scores={situation.id: 0.42},
    )

    confidence = repo.get_tag_confidence(document.id)
    assert confidence.domains == {domain.id: pytest.approx(0.73)}
    assert confidence.life_situations == {situation.id: pytest.approx(0.42)}


def test_add_links_only_the_given_scores_leaving_any_other_id_unlinked(
    db_session: Session, jurisdiction: Jurisdiction
) -> None:
    """The repository is a pure write: a resolved id missing from ``scores`` is simply never linked — it
    is not the repository's job to default it (that default lives one layer up, in ``DocumentService``).
    """
    repo = _repo(db_session)
    scored = _term(db_session, Domain, "housing")
    unscored = _term(db_session, Domain, "work-employment")

    document = repo.add(Document(jurisdiction_id=jurisdiction.id, slug="partial"), domain_scores={scored.id: 0.9})

    confidence = repo.get_tag_confidence(document.id)
    assert confidence.domains == {scored.id: pytest.approx(0.9)}
    assert unscored.id not in confidence.domains


def test_add_writes_the_given_pvog_leaf_code_per_situation_term_id(
    db_session: Session, jurisdiction: Jurisdiction
) -> None:
    repo = _repo(db_session)
    situation = _term(db_session, LifeSituation, "moving-house")

    document = repo.add(
        Document(jurisdiction_id=jurisdiction.id, slug="tagged"),
        situation_scores={situation.id: 0.65},
        situation_leaf_codes={situation.id: "1050200"},
    )

    row = db_session.execute(
        select(document_life_situation.c.pvog_leaf_code).where(document_life_situation.c.document_id == document.id)
    ).scalar_one()
    assert row == "1050200"


def test_add_without_leaf_codes_leaves_the_column_null(db_session: Session, jurisdiction: Jurisdiction) -> None:
    repo = _repo(db_session)
    situation = _term(db_session, LifeSituation, "moving-house")

    document = repo.add(
        Document(jurisdiction_id=jurisdiction.id, slug="untagged-leaf"),
        situation_scores={situation.id: 1.0},
    )

    row = db_session.execute(
        select(document_life_situation.c.pvog_leaf_code).where(document_life_situation.c.document_id == document.id)
    ).scalar_one()
    assert row is None


def test_leaf_codes_in_scope_returns_the_distinct_non_null_codes_for_the_given_situation(
    db_session: Session, jurisdiction: Jurisdiction
) -> None:
    repo = _repo(db_session)
    situation = _term(db_session, LifeSituation, "moving-house")
    repo.add(
        Document(jurisdiction_id=jurisdiction.id, slug="one"),
        situation_scores={situation.id: 1.0},
        situation_leaf_codes={situation.id: "1050200"},
    )
    repo.add(
        Document(jurisdiction_id=jurisdiction.id, slug="two"),
        situation_scores={situation.id: 1.0},
        situation_leaf_codes={situation.id: "1050300"},
    )
    repo.add(
        Document(jurisdiction_id=jurisdiction.id, slug="three"),
        situation_scores={situation.id: 1.0},
        situation_leaf_codes={situation.id: "1050200"},
    )
    repo.add(
        Document(jurisdiction_id=jurisdiction.id, slug="four-no-leaf"),
        situation_scores={situation.id: 1.0},
    )

    codes = repo.leaf_codes_in_scope(jurisdiction_id=jurisdiction.id, situation_ids=[situation.id])

    assert codes == ["1050200", "1050300"]


def test_leaf_codes_in_scope_ignores_rows_outside_the_jurisdiction(
    db_session: Session, jurisdiction: Jurisdiction
) -> None:
    repo = _repo(db_session)
    situation = _term(db_session, LifeSituation, "moving-house")
    other_jurisdiction = Jurisdiction(kind=JurisdictionKind.COUNTRY, name_i18n={"en": "Other"}, code="OTHER")
    db_session.add(other_jurisdiction)
    db_session.flush()
    repo.add(
        Document(jurisdiction_id=other_jurisdiction.id, slug="elsewhere"),
        situation_scores={situation.id: 1.0},
        situation_leaf_codes={situation.id: "1050200"},
    )

    codes = repo.leaf_codes_in_scope(jurisdiction_id=jurisdiction.id, situation_ids=[situation.id])

    assert codes == []


def test_list_page_orders_by_slug_when_no_situation_filter_is_active(
    db_session: Session, jurisdiction: Jurisdiction
) -> None:
    repo = _repo(db_session)
    situation = _term(db_session, LifeSituation, "moving-house")
    repo.add(
        Document(jurisdiction_id=jurisdiction.id, slug="b-low-confidence"),
        situation_scores={situation.id: 0.1},
    )
    repo.add(
        Document(jurisdiction_id=jurisdiction.id, slug="a-high-confidence"),
        situation_scores={situation.id: 0.9},
    )

    rows = repo.list_page(jurisdiction_id=jurisdiction.id, offset=0, limit=10)

    assert [row.slug for row in rows] == ["a-high-confidence", "b-low-confidence"]


def test_list_page_orders_by_confidence_desc_when_a_situation_filter_is_active(
    db_session: Session, jurisdiction: Jurisdiction
) -> None:
    """Slugs are deliberately the reverse of the confidence order, so a passing assertion can only
    be explained by the confidence ordering actually taking effect, not the slug tiebreak."""
    repo = _repo(db_session)
    situation = _term(db_session, LifeSituation, "moving-house")
    repo.add(
        Document(jurisdiction_id=jurisdiction.id, slug="a-low-confidence"),
        situation_scores={situation.id: 0.1},
    )
    repo.add(
        Document(jurisdiction_id=jurisdiction.id, slug="b-high-confidence"),
        situation_scores={situation.id: 0.9},
    )

    rows = repo.list_page(jurisdiction_id=jurisdiction.id, offset=0, limit=10, situation_ids=[situation.id])

    assert [row.slug for row in rows] == ["b-high-confidence", "a-low-confidence"]
