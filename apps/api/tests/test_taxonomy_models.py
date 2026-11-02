from __future__ import annotations

import uuid

import pytest
import sqlalchemy as sa
from app.models import Domain, LifeSituation, LifeSituationGroup
from app.models.document import Document
from app.models.jurisdiction import Jurisdiction, JurisdictionKind
from app.models.taxonomy import document_domain, document_life_situation
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session


def _term(model: type[Domain] | type[LifeSituation], code: str) -> Domain | LifeSituation:
    return model(code=code, name_i18n={"en": code})


def _document(session: Session) -> Document:
    country = Jurisdiction(kind=JurisdictionKind.COUNTRY, name_i18n={"en": "Testland"}, code=f"T{uuid.uuid4().hex[:8]}")
    session.add(country)
    session.flush()
    document = Document(jurisdiction_id=country.id, slug=f"doc-{uuid.uuid4().hex[:8]}")
    session.add(document)
    session.flush()
    return document


def _count(session: Session, table: sa.Table) -> int:
    return session.execute(sa.select(sa.func.count()).select_from(table)).scalar_one()


def test_domain_persists_with_de_and_en_names(db_session: Session) -> None:
    domain = Domain(code="housing", name_i18n={"de": "Wohnen", "en": "Housing"})
    db_session.add(domain)
    db_session.flush()
    db_session.expire(domain)

    assert domain.name_i18n == {"de": "Wohnen", "en": "Housing"}


def test_domain_duplicate_code_is_rejected(db_session: Session) -> None:
    db_session.add(_term(Domain, "housing"))
    db_session.flush()
    db_session.add(_term(Domain, "housing"))

    with pytest.raises(IntegrityError):
        db_session.flush()


@pytest.mark.parametrize("code", ["Umzüge", "moving house", "", "Housing", "-a", "a--b"])
def test_domain_non_kebab_or_accented_code_is_rejected(db_session: Session, code: str) -> None:
    db_session.add(_term(Domain, code))

    with pytest.raises(IntegrityError):
        db_session.flush()


def test_life_situation_duplicate_code_is_rejected(db_session: Session) -> None:
    db_session.add(_term(LifeSituation, "moving-house"))
    db_session.flush()
    db_session.add(_term(LifeSituation, "moving-house"))

    with pytest.raises(IntegrityError):
        db_session.flush()


def test_life_situation_group_persists_with_de_and_en_names(db_session: Session) -> None:
    group = LifeSituationGroup(code="home-housing", name_i18n={"de": "Wohnen", "en": "Home & housing"})
    db_session.add(group)
    db_session.flush()
    db_session.expire(group)

    assert group.name_i18n == {"de": "Wohnen", "en": "Home & housing"}


def test_life_situation_group_duplicate_code_is_rejected(db_session: Session) -> None:
    db_session.add(LifeSituationGroup(code="home-housing", name_i18n={"en": "home-housing"}))
    db_session.flush()
    db_session.add(LifeSituationGroup(code="home-housing", name_i18n={"en": "home-housing"}))

    with pytest.raises(IntegrityError):
        db_session.flush()


@pytest.mark.parametrize("code", ["Umzüge", "moving house", "", "Housing", "-a", "a--b"])
def test_life_situation_group_non_kebab_or_accented_code_is_rejected(db_session: Session, code: str) -> None:
    db_session.add(LifeSituationGroup(code=code, name_i18n={"en": code}))

    with pytest.raises(IntegrityError):
        db_session.flush()


def test_life_situation_can_be_assigned_a_group(db_session: Session) -> None:
    group = LifeSituationGroup(code="home-housing", name_i18n={"en": "home-housing"})
    db_session.add(group)
    db_session.flush()
    situation = LifeSituation(code="moving-house", name_i18n={"en": "moving-house"}, group_id=group.id)
    db_session.add(situation)
    db_session.flush()
    db_session.expire(situation)

    assert situation.group_id == group.id


def test_document_tagging_with_a_domain_and_a_situation_links_both(db_session: Session) -> None:
    document = _document(db_session)
    domain, situation = _term(Domain, "housing"), _term(LifeSituation, "moving-house")
    document.domains.append(domain)  # type: ignore[arg-type]
    document.life_situations.append(situation)  # type: ignore[arg-type]
    db_session.flush()
    db_session.expire(document)

    assert document.domains == [domain]
    assert document.life_situations == [situation]


def test_a_link_row_without_confidence_backfills_to_full_confidence(db_session: Session) -> None:
    """D7: a row written without an explicit confidence (the shape of every row from before chapter 1)
    reads back as ``1.0`` via the column's own ``server_default`` — honest, not a retroactive scoring claim.
    """
    document = _document(db_session)
    domain = _term(Domain, "housing")
    db_session.add(domain)
    db_session.flush()
    db_session.execute(document_domain.insert().values(document_id=document.id, domain_id=domain.id))

    confidence = db_session.execute(
        sa.select(document_domain.c.confidence).where(document_domain.c.document_id == document.id)
    ).scalar_one()

    assert confidence == 1.0


def test_document_tagging_the_same_domain_twice_is_rejected(db_session: Session) -> None:
    document = _document(db_session)
    domain = _term(Domain, "housing")
    db_session.add(domain)
    db_session.flush()
    link = document_domain.insert().values(document_id=document.id, domain_id=domain.id)
    db_session.execute(link)

    with pytest.raises(IntegrityError):
        db_session.execute(link)


def test_deleting_a_document_removes_its_links_but_keeps_the_domain(db_session: Session) -> None:
    document = _document(db_session)
    document.domains.append(_term(Domain, "housing"))  # type: ignore[arg-type]
    document.life_situations.append(_term(LifeSituation, "moving-house"))  # type: ignore[arg-type]
    db_session.flush()

    db_session.execute(sa.delete(Document).where(Document.id == document.id))

    assert _count(db_session, document_domain) == 0
    assert _count(db_session, document_life_situation) == 0
    assert db_session.execute(sa.select(Domain).where(Domain.code == "housing")).scalar_one()


def test_deleting_a_linked_domain_cascades_its_links(db_session: Session) -> None:
    document = _document(db_session)
    domain = _term(Domain, "housing")
    document.domains.append(domain)  # type: ignore[arg-type]
    db_session.flush()

    db_session.execute(sa.delete(Domain).where(Domain.id == domain.id))

    assert _count(db_session, document_domain) == 0
    assert db_session.get(Document, document.id) is not None
