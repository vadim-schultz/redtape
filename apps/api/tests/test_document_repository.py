"""Persisting and reading tag confidence on document_domain/document_life_situation (situation-tag-hierarchy chapter 1 part B)."""

from __future__ import annotations

import uuid

import pytest
from app.features.documents.repository import DocumentRepository
from app.models.document import Document
from app.models.jurisdiction import Jurisdiction, JurisdictionKind
from app.models.taxonomy import Domain, LifeSituation, document_life_situation
from sqlalchemy import select
from sqlalchemy.orm import Session


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
