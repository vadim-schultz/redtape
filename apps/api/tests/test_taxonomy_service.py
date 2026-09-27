from __future__ import annotations

import pytest
from app.features.taxonomy.repository import TaxonomyRepository
from app.features.taxonomy.service import TaxonomyCodeError, TaxonomyService
from app.models.taxonomy import Domain, LifeSituation
from scripts.seed_taxonomy import seed_taxonomy
from sqlalchemy import select
from sqlalchemy.orm import Session


@pytest.fixture
def service(db_session: Session) -> TaxonomyService:
    # tags={}: this suite only resolves domain/situation codes, not documents;
    # the default tag map references a document graph this fixture never seeds.
    seed_taxonomy(db_session, tags={})
    db_session.flush()
    return TaxonomyService(TaxonomyRepository(db_session))


def _id_of(session: Session, model: type[Domain] | type[LifeSituation], code: str):
    return session.scalar(select(model.id).where(model.code == code))


def test_resolves_known_domain_codes_to_ids(service: TaxonomyService, db_session: Session) -> None:
    codes = [d.code for d in service.list_domains(locale="de", enabled_locales={"de", "en"})][:2]

    assert service.resolve_domain_ids(codes) == [_id_of(db_session, Domain, c) for c in codes]


def test_resolves_known_situation_codes_to_ids(service: TaxonomyService, db_session: Session) -> None:
    codes = [s.code for s in service.list_situations(locale="de", enabled_locales={"de", "en"})][:2]

    assert service.resolve_situation_ids(codes) == [_id_of(db_session, LifeSituation, c) for c in codes]


def test_unknown_domain_code_raises(service: TaxonomyService) -> None:
    with pytest.raises(TaxonomyCodeError, match="no-such-code"):
        service.resolve_domain_ids(["no-such-code"])


def test_unknown_situation_code_raises(service: TaxonomyService) -> None:
    with pytest.raises(TaxonomyCodeError, match="no-such-code"):
        service.resolve_situation_ids(["no-such-code"])
